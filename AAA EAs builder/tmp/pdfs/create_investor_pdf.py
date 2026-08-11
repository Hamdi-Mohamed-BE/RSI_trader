from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(r"C:\Users\hama101\Desktop\geek\ai trader\AAA EAs builder")
SLIDES_DIR = ROOT / "docs" / "investor" / "AAA_EAs_Builder_Investor_Briefing"
OUTPUT = ROOT / "docs" / "investor" / "AAA_EAs_Builder_Investor_Briefing.pdf"

# Standard widescreen presentation dimensions: 13.333 x 7.5 inches.
PAGE_WIDTH = 13.333 * 72
PAGE_HEIGHT = 7.5 * 72


def slide_number(path: Path) -> int:
    return int(path.stem.split("-")[-1])


def main() -> None:
    slide_paths = sorted(SLIDES_DIR.glob("slide-*.png"), key=slide_number)
    if len(slide_paths) != 14:
        raise RuntimeError(f"Expected 14 rendered slides, found {len(slide_paths)}")

    document = canvas.Canvas(str(OUTPUT), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    document.setTitle("AAA EAs Builder - Investor Product Briefing")
    document.setAuthor("AAA EAs Builder")
    document.setSubject("Investor briefing for the AI-assisted MT5 and Pine strategy platform")
    document.setCreator("AAA EAs Builder")

    for slide_path in slide_paths:
        document.drawImage(
            ImageReader(str(slide_path)),
            0,
            0,
            width=PAGE_WIDTH,
            height=PAGE_HEIGHT,
            preserveAspectRatio=True,
            anchor="c",
        )
        document.showPage()

    document.save()
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
