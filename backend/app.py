# app.py — WAPI License Backend v2.0
# Security hardening + Auth0 + Manual license management
from __future__ import annotations

import hmac
import hashlib
import json
import os
import secrets
import urllib.parse
import warnings
from datetime import datetime, timezone
from functools import wraps

import requests
from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv

try:
    from authlib.integrations.flask_client import OAuth as _AuthlibOAuth
    _AUTHLIB_AVAILABLE = True
except ImportError:
    _AUTHLIB_AVAILABLE = False

load_dotenv()

# ── App & core config ──────────────────────────────────────────────────────

app = Flask(__name__)

_secret = os.environ.get("SECRET_KEY", "")
_INSECURE = {"", "change-me-in-production", "change-this-to-a-random-string"}
if _secret in _INSECURE:
    warnings.warn(
        "⚠️  SECRET_KEY is missing or uses an insecure default. "
        "Set SECRET_KEY in your environment before deploying.",
        stacklevel=1,
    )
    _secret = secrets.token_hex(32)   # ephemeral — changes every restart!

_is_dev = os.environ.get("FLASK_ENV", "production") == "development"

app.secret_key = _secret
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///wapi.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    # Secure session cookies
    SESSION_COOKIE_NAME="wapi_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not _is_dev,   # HTTPS-only in production
    PERMANENT_SESSION_LIFETIME=28800,    # 8 hours
    # CSRF
    WTF_CSRF_TIME_LIMIT=3600,
)

# ── Extensions ─────────────────────────────────────────────────────────────

db     = SQLAlchemy(app)
csrf   = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://",
)

# ── Environment variables ──────────────────────────────────────────────────

LS_API_KEY        = os.environ.get("LS_API_KEY", "")
LS_WEBHOOK_SECRET = os.environ.get("LS_WEBHOOK_SECRET", "")
LS_STORE_ID       = os.environ.get("LS_STORE_ID", "")
ADMIN_PASSWORD    = os.environ.get("ADMIN_PASSWORD", "")

AUTH0_DOMAIN          = os.environ.get("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID       = os.environ.get("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET   = os.environ.get("AUTH0_CLIENT_SECRET", "")
ADMIN_EMAIL_WHITELIST = [
    e.strip() for e in os.environ.get("ADMIN_EMAIL_WHITELIST", "").split(",") if e.strip()
]

_USE_AUTH0 = bool(AUTH0_DOMAIN and AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET and _AUTHLIB_AVAILABLE)

if _USE_AUTH0:
    _oauth = _AuthlibOAuth(app)
    _auth0_client = _oauth.register(
        "auth0",
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        client_kwargs={"scope": "openid profile email"},
        server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
    )
    if not ADMIN_EMAIL_WHITELIST:
        warnings.warn(
            "⚠️  Auth0 is enabled but ADMIN_EMAIL_WHITELIST is not set. "
            "Any authenticated Auth0 user can access the admin panel!",
            stacklevel=1,
        )
elif not ADMIN_PASSWORD:
    warnings.warn("⚠️  Neither Auth0 nor ADMIN_PASSWORD is configured!", stacklevel=1)


# ── Models ─────────────────────────────────────────────────────────────────

class Customer(db.Model):
    __tablename__ = "customers"
    id             = db.Column(db.Integer, primary_key=True)
    email          = db.Column(db.String(255), nullable=False, index=True)
    name           = db.Column(db.String(255), nullable=True)
    ls_customer_id = db.Column(db.String(100), nullable=True)
    ls_order_id    = db.Column(db.String(100), nullable=True)
    license_key    = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ls_license_id  = db.Column(db.String(100), nullable=True)
    plan           = db.Column(db.String(50), default="standard")
    status         = db.Column(db.String(20), default="active")   # active|revoked|expired
    source         = db.Column(db.String(20), default="lemon_squeezy")  # lemon_squeezy|manual
    purchased_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notes          = db.Column(db.Text, nullable=True)
    activations    = db.relationship("Activation", backref="customer", lazy=True,
                                     cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "email": self.email, "name": self.name,
            "license_key": self.license_key, "plan": self.plan, "status": self.status,
            "source": self.source,
            "purchased_at": self.purchased_at.isoformat() if self.purchased_at else None,
            "activation_count": len(self.activations),
        }


class Activation(db.Model):
    __tablename__ = "activations"
    id           = db.Column(db.Integer, primary_key=True)
    customer_id  = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    instance_id  = db.Column(db.String(255), nullable=True, index=True)
    machine_name = db.Column(db.String(255), nullable=True)
    activated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address   = db.Column(db.String(50), nullable=True)
    app_version  = db.Column(db.String(20), nullable=True)
    is_active    = db.Column(db.Boolean, default=True)


class WebhookLog(db.Model):
    __tablename__ = "webhook_logs"
    id          = db.Column(db.Integer, primary_key=True)
    event_name  = db.Column(db.String(100), nullable=False)
    payload     = db.Column(db.Text, nullable=True)
    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status      = db.Column(db.String(20), default="ok")   # ok|error|ignored


# ── Helpers ────────────────────────────────────────────────────────────────

def _generate_license_key() -> str:
    """Generate a random license key in WAPI-XXXX-XXXX-XXXX-XXXX format."""
    parts = [secrets.token_hex(2).upper() for _ in range(4)]
    return "WAPI-" + "-".join(parts)


def _real_ip() -> str:
    """Return the real client IP, respecting Railway/proxy X-Forwarded-For header."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else request.remote_addr or ""


def _validate_key_input(license_key: str) -> str | None:
    """Return error string if license_key is invalid, else None."""
    if not license_key:
        return "Lizenzschlüssel fehlt"
    if len(license_key) > 255:
        return "Lizenzschlüssel zu lang"
    return None


# ── Admin auth ─────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── Lemon Squeezy helpers ──────────────────────────────────────────────────

LS_API_BASE = "https://api.lemonsqueezy.com/v1"

def _ls_headers() -> dict:
    return {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": f"Bearer {LS_API_KEY}",
    }


def ls_activate_license(license_key: str, instance_name: str) -> dict:
    resp = requests.post(
        f"{LS_API_BASE}/licenses/activate",
        json={"license_key": license_key, "instance_name": instance_name},
        headers=_ls_headers(), timeout=10,
    )
    return resp.json()


def ls_validate_license(license_key: str, instance_id: str) -> dict:
    resp = requests.post(
        f"{LS_API_BASE}/licenses/validate",
        json={"license_key": license_key, "instance_id": instance_id},
        headers=_ls_headers(), timeout=10,
    )
    return resp.json()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Lemon Squeezy HMAC-SHA256 webhook signature.
    Returns False (blocks request) if LS_WEBHOOK_SECRET is not configured.
    """
    if not LS_WEBHOOK_SECRET:
        # Never silently skip in production — require the secret to be set
        if not _is_dev:
            return False
        return True  # allow in dev if secret not set
    expected = hmac.new(
        LS_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── CSRF error handler ─────────────────────────────────────────────────────

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template("admin/csrf_error.html", reason=e.description), 400


# ── Public API (CSRF-exempt — called from desktop app) ─────────────────────

@app.route("/api/activate", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per minute; 50 per hour")
def api_activate():
    """Desktop app calls this on first launch to activate a license key."""
    data         = request.get_json(silent=True) or {}
    license_key  = str(data.get("license_key", "")).strip()[:255]
    instance_id  = str(data.get("instance_id", "")).strip()[:255]
    machine_name = str(data.get("machine_name", "Unknown"))[:100]
    app_version  = str(data.get("app_version", ""))[:20]

    err = _validate_key_input(license_key)
    if err or not instance_id:
        return jsonify({"valid": False, "error": err or "Instanz-ID fehlt"}), 400

    # Look up in our DB first
    customer = Customer.query.filter_by(license_key=license_key).first()
    if not customer:
        # Try Lemon Squeezy activation
        ls_result = ls_activate_license(license_key, machine_name)
        if ls_result.get("activated"):
            meta = ls_result.get("meta", {})
            customer = Customer(
                email=str(meta.get("customer_email", ""))[:255],
                name=str(meta.get("customer_name", ""))[:255],
                license_key=license_key,
                ls_license_id=str(ls_result.get("license_key", {}).get("id", ""))[:100],
                status="active",
                source="lemon_squeezy",
            )
            db.session.add(customer)
            db.session.commit()
        else:
            error_msg = ls_result.get("error", "Ungültiger Lizenzschlüssel")
            return jsonify({"valid": False, "error": error_msg}), 403

    if customer.status != "active":
        return jsonify({"valid": False, "error": "Lizenz gesperrt oder abgelaufen"}), 403

    # Record activation / update last_seen
    activation = Activation.query.filter_by(
        customer_id=customer.id, instance_id=instance_id
    ).first()

    if not activation:
        activation = Activation(
            customer_id=customer.id,
            instance_id=instance_id,
            machine_name=machine_name,
            ip_address=_real_ip(),
            app_version=app_version,
            is_active=True,
        )
        db.session.add(activation)
    else:
        if not activation.is_active:
            return jsonify({"valid": False, "error": "Dieses Gerät wurde gesperrt"}), 403
        activation.last_seen_at = datetime.now(timezone.utc)
        activation.app_version  = app_version

    db.session.commit()

    return jsonify({
        "valid": True,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "plan": customer.plan,
    })


@app.route("/api/validate", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per minute; 200 per hour")
def api_validate():
    """Desktop app calls this periodically (every 7 days) to confirm license validity."""
    data        = request.get_json(silent=True) or {}
    license_key = str(data.get("license_key", "")).strip()[:255]
    instance_id = str(data.get("instance_id", "")).strip()[:255]

    err = _validate_key_input(license_key)
    if err:
        return jsonify({"valid": False}), 400

    customer = Customer.query.filter_by(license_key=license_key).first()
    if not customer or customer.status != "active":
        return jsonify({"valid": False, "error": "Lizenz ungültig oder gesperrt"})

    # Check per-device status
    if instance_id:
        activation = Activation.query.filter_by(
            customer_id=customer.id, instance_id=instance_id
        ).first()
        if activation:
            if not activation.is_active:
                return jsonify({"valid": False, "error": "Dieses Gerät wurde gesperrt"})
            activation.last_seen_at = datetime.now(timezone.utc)
            db.session.commit()

    return jsonify({"valid": True, "plan": customer.plan})


# ── Lemon Squeezy Webhook ──────────────────────────────────────────────────

@app.route("/webhook/lemonsqueezy", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def webhook_lemonsqueezy():
    payload_bytes = request.get_data()
    signature     = request.headers.get("X-Signature", "")

    if not verify_webhook_signature(payload_bytes, signature):
        return jsonify({"error": "Invalid signature"}), 401

    try:
        payload    = json.loads(payload_bytes)
        event_name = request.headers.get("X-Event-Name", "unknown")

        log = WebhookLog(event_name=event_name, payload=payload_bytes.decode("utf-8")[:5000])
        db.session.add(log)

        if event_name == "order_created":
            _handle_order_created(payload)
        elif event_name == "license_key_created":
            _handle_license_key_created(payload)
        elif event_name == "license_key_updated":
            _handle_license_key_updated(payload)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        log = WebhookLog(event_name="error", payload=str(e)[:1000], status="error")
        db.session.add(log)
        db.session.commit()
        return jsonify({"error": "Internal error"}), 500   # don't leak exception details

    return jsonify({"ok": True})


def _handle_order_created(payload: dict):
    pass  # license_key_created covers what we need


def _handle_license_key_created(payload: dict):
    attrs  = payload.get("data", {}).get("attributes", {})
    meta   = payload.get("meta", {})
    key    = str(attrs.get("key", "")).strip()
    email  = str(attrs.get("user_email") or meta.get("user_email", ""))[:255]
    name   = str(attrs.get("user_name")  or meta.get("user_name", ""))[:255]
    ls_id  = str(payload.get("data", {}).get("id", ""))[:100]

    if not key:
        return
    if not Customer.query.filter_by(license_key=key).first():
        db.session.add(Customer(
            email=email, name=name, license_key=key,
            ls_license_id=ls_id, status="active", source="lemon_squeezy",
        ))


def _handle_license_key_updated(payload: dict):
    attrs  = payload.get("data", {}).get("attributes", {})
    key    = str(attrs.get("key", "")).strip()
    status = attrs.get("status", "")   # "active" | "inactive" | "expired" | "disabled"
    if not key:
        return
    customer = Customer.query.filter_by(license_key=key).first()
    if customer:
        if status in ("inactive", "disabled"):
            customer.status = "revoked"
        elif status == "expired":
            customer.status = "expired"
        elif status == "active":
            customer.status = "active"


# ── Admin: Auth0 login flow ────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def admin_login():
    if _USE_AUTH0:
        # Redirect to Auth0
        callback = AUTH0_DOMAIN and url_for("auth0_callback", _external=True)
        return _auth0_client.authorize_redirect(redirect_uri=callback)

    # Password fallback
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        # Timing-safe comparison
        if ADMIN_PASSWORD and hmac.compare_digest(pw, ADMIN_PASSWORD):
            session["admin_logged_in"] = True
            session["admin_user"] = {"email": "admin", "name": "Admin"}
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        error = "Falsches Passwort"
    return render_template("admin/login.html", error=error, use_auth0=False)


@app.route("/admin/callback")
def auth0_callback():
    """Auth0 OAuth2 callback."""
    if not _USE_AUTH0:
        return redirect(url_for("admin_login"))

    token    = _auth0_client.authorize_access_token()
    userinfo = token.get("userinfo") or {}
    email    = str(userinfo.get("email", "")).lower()

    if ADMIN_EMAIL_WHITELIST and email not in ADMIN_EMAIL_WHITELIST:
        return render_template("admin/login.html",
                               error=f"Zugriff verweigert: {email} ist nicht berechtigt.",
                               use_auth0=True), 403

    session["admin_logged_in"] = True
    session["admin_user"] = {
        "email": email,
        "name": userinfo.get("name", email),
        "picture": userinfo.get("picture", ""),
    }
    session.permanent = True
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    if _USE_AUTH0:
        return_to = url_for("admin_login", _external=True)
        logout_url = (
            f"https://{AUTH0_DOMAIN}/v2/logout?"
            + urllib.parse.urlencode({"returnTo": return_to, "client_id": AUTH0_CLIENT_ID})
        )
        return redirect(logout_url)
    return redirect(url_for("admin_login"))


# ── Admin: Dashboard ───────────────────────────────────────────────────────

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_customers   = Customer.query.count()
    active_customers  = Customer.query.filter_by(status="active").count()
    revoked_customers = Customer.query.filter_by(status="revoked").count()
    total_activations = Activation.query.filter_by(is_active=True).count()
    recent_customers  = Customer.query.order_by(Customer.purchased_at.desc()).limit(10).all()
    recent_logs       = WebhookLog.query.order_by(WebhookLog.received_at.desc()).limit(20).all()
    return render_template("admin/dashboard.html",
        total_customers=total_customers, active_customers=active_customers,
        revoked_customers=revoked_customers, total_activations=total_activations,
        recent_customers=recent_customers, recent_logs=recent_logs,
        admin_user=session.get("admin_user", {}),
    )


# ── Admin: Customers ───────────────────────────────────────────────────────

@app.route("/admin/customers")
@admin_required
def admin_customers():
    search        = request.args.get("q", "")[:100]
    status_filter = request.args.get("status", "")
    query = Customer.query
    if search:
        query = query.filter(
            Customer.email.ilike(f"%{search}%") |
            Customer.name.ilike(f"%{search}%")  |
            Customer.license_key.ilike(f"%{search}%")
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    customers = query.order_by(Customer.purchased_at.desc()).all()
    return render_template("admin/customers.html",
        customers=customers, search=search, status_filter=status_filter,
        admin_user=session.get("admin_user", {}),
    )


@app.route("/admin/customers/new", methods=["GET", "POST"])
@admin_required
def admin_new_customer():
    """Manually grant a license — for testers, friends, promo codes, etc."""
    error = None
    if request.method == "POST":
        email       = str(request.form.get("email", "")).strip()[:255]
        name        = str(request.form.get("name", "")).strip()[:255]
        plan        = str(request.form.get("plan", "standard"))[:50]
        custom_key  = str(request.form.get("license_key", "")).strip()[:255]
        notes       = str(request.form.get("notes", ""))[:1000]

        if not email:
            error = "E-Mail ist erforderlich."
        else:
            key = custom_key or _generate_license_key()
            if Customer.query.filter_by(license_key=key).first():
                error = "Dieser Lizenzschlüssel existiert bereits."
            else:
                customer = Customer(
                    email=email, name=name, license_key=key,
                    plan=plan, status="active", source="manual", notes=notes,
                )
                db.session.add(customer)
                db.session.commit()
                return redirect(url_for("admin_customer_detail", customer_id=customer.id))

    return render_template("admin/new_customer.html",
        error=error, admin_user=session.get("admin_user", {}),
    )


@app.route("/admin/customers/<int:customer_id>")
@admin_required
def admin_customer_detail(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    return render_template("admin/customer_detail.html",
        customer=customer, admin_user=session.get("admin_user", {}),
    )


@app.route("/admin/customers/<int:customer_id>/revoke", methods=["POST"])
@admin_required
def admin_revoke_license(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    customer.status = "revoked"
    db.session.commit()
    return redirect(url_for("admin_customer_detail", customer_id=customer_id))


@app.route("/admin/customers/<int:customer_id>/activate", methods=["POST"])
@admin_required
def admin_activate_license(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    customer.status = "active"
    db.session.commit()
    return redirect(url_for("admin_customer_detail", customer_id=customer_id))


@app.route("/admin/customers/<int:customer_id>/note", methods=["POST"])
@admin_required
def admin_update_note(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    customer.notes = str(request.form.get("notes", ""))[:2000]
    db.session.commit()
    return redirect(url_for("admin_customer_detail", customer_id=customer_id))


# ── Admin: Per-device activation management ────────────────────────────────

@app.route("/admin/activations/<int:activation_id>/revoke", methods=["POST"])
@admin_required
def admin_revoke_activation(activation_id):
    """Block a specific device without revoking the entire license."""
    a = db.get_or_404(Activation, activation_id)
    a.is_active = False
    db.session.commit()
    return redirect(url_for("admin_customer_detail", customer_id=a.customer_id))


@app.route("/admin/activations/<int:activation_id>/reactivate", methods=["POST"])
@admin_required
def admin_reactivate_activation(activation_id):
    """Re-allow a previously blocked device."""
    a = db.get_or_404(Activation, activation_id)
    a.is_active = True
    db.session.commit()
    return redirect(url_for("admin_customer_detail", customer_id=a.customer_id))


# ── Admin: Activations & Logs ──────────────────────────────────────────────

@app.route("/admin/activations")
@admin_required
def admin_activations():
    activations = Activation.query.order_by(Activation.last_seen_at.desc()).limit(200).all()
    return render_template("admin/activations.html",
        activations=activations, admin_user=session.get("admin_user", {}),
    )


@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs = WebhookLog.query.order_by(WebhookLog.received_at.desc()).limit(100).all()
    return render_template("admin/logs.html",
        logs=logs, admin_user=session.get("admin_user", {}),
    )


# ── Security headers (applied to all responses) ────────────────────────────

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-XSS-Protection"]       = "1; mode=block"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    # Only set HSTS in production
    if not _is_dev:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── DB init & run ──────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=_is_dev, port=5001)
