from __future__ import annotations

from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "storyboard.mhtml"
SHEETS = ROOT / "storyboard-sheets"
FRAMES = ROOT / "storyboard-frames"
CONTACT = ROOT / "storyboard-contact.jpg"


def main() -> None:
    SHEETS.mkdir(exist_ok=True)
    FRAMES.mkdir(exist_ok=True)
    message = BytesParser(policy=policy.default).parsebytes(SOURCE.read_bytes())
    parts = [part for part in message.walk() if part.get_content_type() == "image/jpeg"]

    frame_index = 0
    for sheet_index, part in enumerate(parts):
        payload = part.get_payload(decode=True)
        image = Image.open(BytesIO(payload)).convert("RGB")
        sheet_path = SHEETS / f"sheet-{sheet_index:02d}.jpg"
        image.save(sheet_path, quality=95)

        # YouTube's L3 storyboard is a 5x5 grid. The last sheet may contain
        # unused black cells, which are retained so timestamps stay aligned.
        tile_width = image.width // 5
        tile_height = image.height // 5
        for row in range(5):
            for col in range(5):
                tile = image.crop(
                    (
                        col * tile_width,
                        row * tile_height,
                        (col + 1) * tile_width,
                        (row + 1) * tile_height,
                    )
                )
                tile.save(FRAMES / f"frame-{frame_index:03d}.jpg", quality=95)
                frame_index += 1

    valid_frames = sorted(FRAMES.glob("frame-*.jpg"))[:324]
    columns = 8
    label_height = 18
    tile_width, tile_height = 192, 108
    rows = (len(valid_frames) + columns - 1) // columns
    contact = Image.new("RGB", (columns * tile_width, rows * (tile_height + label_height)), "white")
    draw = ImageDraw.Draw(contact)
    interval_seconds = 1076.261 / len(valid_frames)
    for index, path in enumerate(valid_frames):
        frame = Image.open(path).convert("RGB").resize((tile_width, tile_height))
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + label_height)
        contact.paste(frame, (x, y))
        seconds = round(index * interval_seconds)
        draw.text((x + 3, y + tile_height + 2), f"{seconds // 60:02d}:{seconds % 60:02d}", fill="black")
    contact.save(CONTACT, quality=92)

    print(f"Extracted {len(parts)} sheets and {frame_index} frames; wrote {CONTACT.name}")


if __name__ == "__main__":
    main()
