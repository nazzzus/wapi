# WAPI Backend – Deployment auf Railway

Dieses Dokument beschreibt Schritt für Schritt, wie du das WAPI-Backend auf **Railway** deployst, Umgebungsvariablen setzt und Lemon Squeezy konfigurierst.

---

## Voraussetzungen

- Railway-Account (kostenlos unter https://railway.app)
- Lemon Squeezy-Account mit einem Produkt/Lizenz eingerichtet
- Git installiert (optional, aber empfohlen)

---

## Schritt 1: Railway-Projekt erstellen

1. Melde dich auf https://railway.app an
2. Klicke auf **„New Project"**
3. Wähle **„Deploy from GitHub repo"** (empfohlen) oder **„Empty project"**

### Option A – GitHub (empfohlen)
- Pushe den Ordner `backend/` in ein eigenes GitHub-Repository (z. B. `wapi-backend`)
- Verbinde Railway mit deinem GitHub-Account
- Wähle das Repository aus → Railway erkennt das `Procfile` automatisch

### Option B – Railway CLI
```bash
npm install -g @railway/cli
cd backend/
railway login
railway init
railway up
```

---

## Schritt 2: Umgebungsvariablen setzen

Gehe in Railway zu deinem Projekt → **„Variables"** und lege folgende Variablen an:

| Variable | Wert | Beschreibung |
|---|---|---|
| `SECRET_KEY` | langer zufälliger String | Flask Session-Secret (z. B. `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ADMIN_PASSWORD` | dein sicheres Passwort | Passwort für das Admin-Dashboard |
| `LS_API_KEY` | dein Lemon Squeezy API-Key | Unter LS → Settings → API |
| `LS_WEBHOOK_SECRET` | zufälliger String | Selbst gewählt; wird auch in LS eingetragen |
| `LS_STORE_ID` | deine Store-ID | Unter LS → Settings → Stores |
| `DATABASE_URL` | *(leer lassen, Railway setzt das automatisch bei Volume)* | Für SQLite reicht der Default |

**SECRET_KEY generieren:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**LS_WEBHOOK_SECRET generieren:**
```bash
python -c "import secrets; print(secrets.token_hex(24))"
```

---

## Schritt 3: Persistentes Volume für SQLite einrichten

Railway löscht das Dateisystem bei jedem Deploy. Damit die SQLite-Datenbank erhalten bleibt:

1. In deinem Railway-Projekt → **„+ New"** → **„Volume"**
2. Mountpath: `/data`
3. In `backend/app.py` sicherstellen, dass die DB im Volume liegt:

```python
# In app.py – DATABASE_URL anpassen
import os
DB_PATH = os.environ.get("DATABASE_URL", "sqlite:////data/wapi.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
```

4. Setze die Railway-Variable:
   - `DATABASE_URL` = `sqlite:////data/wapi.db`

> **Tipp:** Alternativ kannst du Railway's PostgreSQL-Add-on verwenden (kostenlos im Hobby-Plan). Dann `DATABASE_URL` auf die PostgreSQL-URL setzen und `psycopg2-binary` zu `requirements.txt` hinzufügen.

---

## Schritt 4: Erste Deployment-URL ermitteln

1. Nach dem Deploy siehst du in Railway unter **„Settings" → „Networking"** deine öffentliche URL
2. Format: `https://wapi-backend-production-xxxx.up.railway.app`
3. Diese URL brauchst du für:
   - `BACKEND_URL` in `license.py` (Desktop-App)
   - Lemon Squeezy Webhook-Konfiguration

---

## Schritt 5: `license.py` der Desktop-App aktualisieren

Öffne `wapi/license.py` und ersetze:

```python
BACKEND_URL = "https://your-app.railway.app"
```

durch deine echte Railway-URL:

```python
BACKEND_URL = "https://wapi-backend-production-xxxx.up.railway.app"
```

Danach die App neu bauen:
```bash
build.bat
```

---

## Schritt 6: Lemon Squeezy konfigurieren

### 6.1 Produkt anlegen

1. Gehe zu **Lemon Squeezy → Products → New Product**
2. Wähle **Software License** als Produkttyp
3. Preis festlegen (z. B. 29 € einmalig)
4. **License key settings:**
   - Expiry: **Never**
   - Activations limit: **1** (für Einzelplatzlizenz; erhöhe für Multi-Device)

### 6.2 Webhook einrichten

1. LS → Settings → **Webhooks → Add webhook**
2. URL: `https://deine-railway-url.up.railway.app/webhook/lemonsqueezy`
3. Secret: Den gleichen Wert, den du als `LS_WEBHOOK_SECRET` in Railway gesetzt hast
4. Events aktivieren:
   - ✅ `order_created`
   - ✅ `license_key_created`
   - ✅ `license_key_updated`

### 6.3 Checkout-URL

Die Checkout-URL für deinen Shop findest du unter:
LS → Products → dein Produkt → **„Share"** oder **„Buy"**

Diese URL verlinkst du in der Desktop-App (ActivationDialog „Lizenz kaufen →"-Button).

Um den Link in `ui.py` zu aktualisieren, suche nach:
```python
QDesktopServices.openUrl(QUrl("https://wapi.sultani.de"))
```
und ersetze die URL durch deine direkte LS-Checkout-URL.

---

## Schritt 7: Admin-Dashboard aufrufen

1. Rufe `https://deine-railway-url.up.railway.app/admin` auf
2. Melde dich mit dem `ADMIN_PASSWORD` an, das du in Railway gesetzt hast
3. Du siehst jetzt das Dashboard mit Kunden, Aktivierungen und Webhook-Logs

---

## Schritt 8: Datenbank initialisieren (beim ersten Deploy)

Die Datenbanktabellen werden automatisch beim ersten Start angelegt (`db.create_all()` in `app.py`). Falls nicht:

```bash
railway run python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

---

## Deployment-Checkliste

Vor dem Go-Live:

- [ ] `SECRET_KEY` gesetzt (mindestens 32 Zeichen)
- [ ] `ADMIN_PASSWORD` gesetzt (sicheres Passwort)
- [ ] `LS_API_KEY` gesetzt (aus Lemon Squeezy)
- [ ] `LS_WEBHOOK_SECRET` gesetzt (und in LS eingetragen)
- [ ] `LS_STORE_ID` gesetzt
- [ ] Volume für SQLite eingerichtet (`/data`)
- [ ] `BACKEND_URL` in `license.py` aktualisiert
- [ ] Desktop-App neu gebaut (`build.bat`)
- [ ] Webhook-Test in Lemon Squeezy ausgelöst (LS → Webhook → „Send test")
- [ ] Test-Kauf durchgeführt und Lizenzschlüssel im Admin-Dashboard geprüft
- [ ] Admin-Passwort ist nicht das Standard-Beispielpasswort

---

## Fehlerbehebung

**„Application failed to start"**
- Prüfe Railway-Logs: Projekt → **„Deployments" → letztes Deployment → Logs**
- Häufige Ursache: fehlende Umgebungsvariable

**Webhook kommt nicht an**
- Prüfe unter LS → Webhooks die letzten Events und deren HTTP-Status
- Prüfe `/admin/logs` im Admin-Dashboard
- Häufige Ursache: falscher `LS_WEBHOOK_SECRET`

**SQLite-Daten nach Deploy weg**
- Volume nicht eingerichtet oder falscher Mountpath
- Lösung: Volume auf `/data` und `DATABASE_URL=sqlite:////data/wapi.db`

**Lizenzaktivierung schlägt fehl**
- `BACKEND_URL` in `license.py` noch auf `your-app.railway.app`?
- Firewall/Proxy blockiert ausgehende HTTPS-Anfragen vom Desktop?

---

## Kosten

Railway bietet einen **Hobby-Plan** ab 5 $/Monat (Stand April 2026). Für ein kleines Indieprojekt reicht das Hobby-Kontingent problemlos. Volumes kosten zusätzlich ~0,25 $/GB/Monat.

Alternativ: Vollständig kostenlos mit **Render.com** (free tier, aber Sleep-Modus nach Inaktivität) oder **Fly.io** (free tier mit Persistent Storage).
