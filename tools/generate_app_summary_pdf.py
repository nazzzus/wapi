from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
OUTPUT_PATH = OUTPUT_DIR / "wapi-app-summary.pdf"


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCompact",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=colors.HexColor("#1E1E1E"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCompact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#5B6470"),
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "SectionCompact",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=12,
            textColor=colors.HexColor("#E8682A"),
            spaceBefore=2,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "BodyCompact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10.1,
            textColor=colors.HexColor("#1E1E1E"),
            alignment=TA_LEFT,
            spaceAfter=2.2,
        ),
        "bullet": ParagraphStyle(
            "BulletCompact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.1,
            leading=9.6,
            leftIndent=9,
            firstLineIndent=-7,
            bulletIndent=0,
            textColor=colors.HexColor("#1E1E1E"),
            spaceAfter=1.6,
        ),
        "small": ParagraphStyle(
            "SmallCompact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=8.8,
            textColor=colors.HexColor("#5B6470"),
        ),
    }


def p(text, style):
    return Paragraph(text, style)


def section(title, body_items):
    return KeepTogether([title, *body_items])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=11 * mm,
    )

    left_col = [
        p("What It Is", styles["section"]),
        p(
            "WAPI is a desktop image processing app built with PySide6. Repo evidence shows it applies "
            "watermarks and optional frames to batches of images, previews the result, and exports the "
            "processed files in common image formats.",
            styles["body"],
        ),
        p("Who It's For", styles["section"]),
        p(
            "<b>Primary persona:</b> Not stated directly in repo. Based on the UI, settings, and processing "
            "code, the target user appears to be a creator or small business user batch-exporting branded images.",
            styles["body"],
        ),
        p("What It Does", styles["section"]),
        p("&bull; Load images from file picker or drag-and-drop.", styles["bullet"]),
        p("&bull; Preview edits before export inside the desktop UI.", styles["bullet"]),
        p("&bull; Apply text watermarks with font, color, size, opacity, and position controls.", styles["bullet"]),
        p("&bull; Apply logo/image watermarks with adjustable size and placement.", styles["bullet"]),
        p("&bull; Add simple or passepartout-style frames around images.", styles["bullet"]),
        p("&bull; Batch-export to JPG, PNG, or WebP with output folder, quality, and filename suffix settings.", styles["bullet"]),
        p("&bull; Persist user settings locally and gate app launch behind license activation.", styles["bullet"]),
    ]

    right_col = [
        p("How It Works", styles["section"]),
        p(
            "&bull; <b>Desktop shell:</b> <font name='Courier'>main.py</font> launches the PySide6 app, applies the theme, "
            "loads settings, checks the license, and opens <font name='Courier'>MainWindow</font>.",
            styles["bullet"],
        ),
        p(
            "&bull; <b>UI layer:</b> <font name='Courier'>ui.py</font> provides the image list, live preview, watermark/frame/export tabs, "
            "progress UI, and license activation dialog.",
            styles["bullet"],
        ),
        p(
            "&bull; <b>Image engine:</b> <font name='Courier'>processor.py</font> uses Pillow to add text/logo watermarks, build "
            "frames, and save processed outputs.",
            styles["bullet"],
        ),
        p(
            "&bull; <b>Local state:</b> <font name='Courier'>settings.py</font> reads/writes <font name='Courier'>wapi_settings.json</font>; "
            "<font name='Courier'>license.py</font> caches activation data in <font name='Courier'>wapi_license.json</font>.",
            styles["bullet"],
        ),
        p(
            "&bull; <b>Licensing backend:</b> <font name='Courier'>backend/app.py</font> exposes Flask APIs for activate/validate, "
            "stores customers/activations/webhook logs with SQLAlchemy + SQLite, and includes admin pages.",
            styles["bullet"],
        ),
        p(
            "&bull; <b>External flow:</b> Desktop app calls backend APIs; backend calls Lemon Squeezy license endpoints and "
            "receives Lemon Squeezy webhooks. A complete local end-to-end dev setup tying desktop to a live backend is <b>Not found in repo</b>.",
            styles["bullet"],
        ),
        Spacer(1, 2),
        p("How To Run", styles["section"]),
        p("1. Install desktop deps: <font name='Courier'>pip install -r requirements.txt</font>", styles["body"]),
        p("2. Start the desktop app: <font name='Courier'>python main.py</font>", styles["body"]),
        p(
            "3. Optional licensing backend: <font name='Courier'>cd backend</font>, "
            "<font name='Courier'>pip install -r requirements.txt</font>, then <font name='Courier'>python app.py</font>.",
            styles["body"],
        ),
        p(
            "4. Before packaged use, update <font name='Courier'>BACKEND_URL</font> in <font name='Courier'>license.py</font>; "
            "a ready-made local dev URL or unified startup command is <b>Not found in repo</b>.",
            styles["body"],
        ),
    ]

    table = Table(
        [[left_col, right_col]],
        colWidths=[88 * mm, 88 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [
        p("WAPI", styles["title"]),
        p(
            "One-page repo-based app summary generated from source code and repository docs on 2026-04-08.",
            styles["subtitle"],
        ),
        table,
        Spacer(1, 5),
        p(
            "Evidence used: main.py, ui.py, processor.py, settings.py, license.py, build.bat, "
            "WAPI.spec, backend/app.py, backend/requirements.txt, DEPLOYMENT_RAILWAY.md.",
            styles["small"],
        ),
    ]

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
