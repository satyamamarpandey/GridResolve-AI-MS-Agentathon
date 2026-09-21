"""Redact the Foundry project name from authentic portal captures.

The portal breadcrumb shows the project name. This script keeps the untouched
original in evidence/_originals_unredacted/ (ignored by git), and writes a copy to
evidence/screenshots/ with one solid box over the breadcrumb. Nothing else in the
image is changed, and nothing is generated or redrawn.

  python scripts/redact_foundry_captures.py
"""
import os
import shutil
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "evidence", "app-screenshots")
ORIGINALS = os.path.join(ROOT, "evidence", "_originals_unredacted")
OUT = os.path.join(ROOT, "evidence", "screenshots")
BOX_COLOUR = (60, 60, 60)

# file name: (image size the box was measured on, box as left, top, right, bottom)
CAPTURES = {
    "F10-WORKFLOW.png": ((1672, 941), (160, 8, 372, 36)),
    "F10-COMPLIANCE.png": ((2860, 1700), (280, 12, 660, 60)),
}


def main() -> int:
    os.makedirs(ORIGINALS, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for name, (size, box) in CAPTURES.items():
        original = os.path.join(ORIGINALS, name)
        inbox = os.path.join(INBOX, name)
        if os.path.exists(inbox) and not os.path.exists(original):
            shutil.move(inbox, original)
        if not os.path.exists(original):
            print("missing  %s" % name)
            continue
        image = Image.open(original).convert("RGB")
        if image.size != size:
            print("skipped  %s, size %s is not the %s the box was measured on" % (name, image.size, size))
            continue
        ImageDraw.Draw(image).rectangle(box, fill=BOX_COLOUR)
        image.save(os.path.join(OUT, name), optimize=True)
        print("redacted %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
