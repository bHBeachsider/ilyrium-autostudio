"""
Caption generator for Nast style-LoRA training images.

Derives captions from image filenames (containing cartoon titles), cleaning out
catalog IDs and attribution boilerplate, with a fixed style trigger.

Run: python -m packs.nast.hand.caption --imgdir packs/nast/data/hand/train
"""

import argparse
import re
from pathlib import Path

TRIGGER = "thomas_nast_style"


def clean_title(filename: str) -> str:
    """
    Clean a cartoon title from a filename.

    1. Drop the extension.
    2. Remove catalog/accession ID tokens (case-insensitive):
       LCCN, MET_DP*, MET_*, NGA_*, NPG[-_]*, DPLA[-_]*, (cropped), (No. N)
    3. Remove attribution boilerplate: -_Th._Nast., Th._Nast., by_Thomas_Nast, etc.
    4. Replace underscores with spaces, collapse multiple spaces, strip.
    5. Strip trailing/leading " - ", ",", ".".

    Args:
        filename: Image filename with extension.

    Returns:
        Cleaned title string.
    """
    # Drop the extension
    title = Path(filename).stem

    # Remove catalog/accession ID tokens (case-insensitive)
    # LCCN followed by optional word characters (or standalone)
    title = re.sub(r'LCCN\w*', '', title, flags=re.IGNORECASE)
    # MET_DP followed by any word characters
    title = re.sub(r'MET_DP\w+', '', title, flags=re.IGNORECASE)
    # MET_ followed by any word characters
    title = re.sub(r'MET_\w+', '', title, flags=re.IGNORECASE)
    # NGA_ followed by any word characters
    title = re.sub(r'NGA_\w+', '', title, flags=re.IGNORECASE)
    # NPG- or NPG_ followed by any word characters
    title = re.sub(r'NPG[-_]\w+', '', title, flags=re.IGNORECASE)
    # DPLA- or DPLA_ followed by any word characters
    title = re.sub(r'DPLA[-_]\w+', '', title, flags=re.IGNORECASE)
    # Remove (cropped) or similar
    title = re.sub(r'\(cropped\)', '', title, flags=re.IGNORECASE)
    # Remove (No. N) or (No N)
    title = re.sub(r'\(No\.?\s*\d+\)', '', title, flags=re.IGNORECASE)

    # Remove attribution boilerplate
    # -_Th._Nast. or -_Th._Nast
    title = re.sub(r'-_Th\._Nast\.?', '', title, flags=re.IGNORECASE)
    # Th._Nast. or Th._Nast
    title = re.sub(r'Th\._Nast\.?', '', title, flags=re.IGNORECASE)
    # by_Thomas_Nast or by_Thomas_Nast,
    title = re.sub(r'by_Thomas_Nast,?', '', title, flags=re.IGNORECASE)
    # _by_Thomas_Nast
    title = re.sub(r'_by_Thomas_Nast', '', title, flags=re.IGNORECASE)
    # Thomas_Nast, or Thomas_Nast
    title = re.sub(r'Thomas_Nast,?', '', title, flags=re.IGNORECASE)

    # Replace underscores with spaces
    title = title.replace('_', ' ')

    # Collapse multiple spaces
    title = re.sub(r' +', ' ', title)

    # Strip whitespace
    title = title.strip()

    # Strip trailing/leading " - ", ",", "."
    title = title.strip(' -,.')

    return title


def build_caption(title: str, trigger: str = TRIGGER) -> str:
    """
    Build a caption for a training image.

    Args:
        title: Cleaned cartoon title.
        trigger: Style trigger token (default: TRIGGER).

    Returns:
        Full caption string.
    """
    return f"{trigger}, {title}, 19th-century wood engraving, dense cross-hatching, black and white"


def main():
    """
    Main entry point: process all images in a directory.

    Writes sibling .txt caption files and a manifest TSV.
    """
    parser = argparse.ArgumentParser(
        description="Generate captions for Nast cartoon images."
    )
    parser.add_argument(
        "--imgdir",
        default="packs/nast/data/hand/train",
        help="Directory containing training images (default: packs/nast/data/hand/train)",
    )
    args = parser.parse_args()

    img_dir = Path(args.imgdir)
    if not img_dir.exists():
        print(f"Error: image directory does not exist: {img_dir}")
        return

    # Image extensions to process
    extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}

    caption_rows = []
    count = 0

    for img_file in img_dir.iterdir():
        if img_file.suffix.lower() not in extensions:
            continue

        # Clean title and build caption
        title = clean_title(img_file.name)
        caption = build_caption(title)

        # Write sibling .txt file
        txt_file = img_file.with_suffix('.txt')
        txt_file.write_text(caption, encoding='utf-8')

        caption_rows.append((img_file.name, caption))
        count += 1

    # Write manifest TSV
    manifest_file = img_dir / 'captions.tsv'
    with manifest_file.open('w', encoding='utf-8') as f:
        for filename, caption in caption_rows:
            f.write(f"{filename}\t{caption}\n")

    print(f"Wrote {count} caption files and manifest to {manifest_file}")


if __name__ == "__main__":
    main()
