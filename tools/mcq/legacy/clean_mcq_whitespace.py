from pathlib import Path
from collections import Counter
import csv
import pymupdf

SOURCE = Path.home() / "Desktop/pastify_mcq_full_staging"
DEST = Path.home() / "Desktop/pastify_mcq_cleaned_staging"

BOTTOM_MARGIN = 24
MIN_SAVING = 65
MIN_HEIGHT = 100

if not SOURCE.is_dir():
    raise SystemExit(f"Source folder not found: {SOURCE}")

if DEST.exists():
    raise SystemExit(
        f"Cleaned folder already exists: {DEST}\n"
        "No files were overwritten."
    )

files = sorted(SOURCE.glob("*/*/*.pdf"))

if len(files) != 17630:
    raise SystemExit(
        f"Expected 17,630 question PDFs, found {len(files)}."
    )

# Validate the full source collection before writing anything.
for path in files:
    with pymupdf.open(path) as doc:
        if len(doc) != 1:
            raise SystemExit(f"Unexpected page count: {path}")

DEST.mkdir(parents=True)

stats = Counter()
report = []

for index, source in enumerate(files, 1):
    relative = source.relative_to(SOURCE)
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(source) as original:
        page = original[0]
        old_height = page.rect.height
        width = page.rect.width

        # Inspect text, drawings, and image positions.
        boxes = []

        for word in page.get_text("words"):
            boxes.append(pymupdf.Rect(word[:4]))

        for drawing in page.get_drawings():
            boxes.append(pymupdf.Rect(drawing["rect"]))

        for image in page.get_images(full=True):
            boxes.extend(page.get_image_rects(image[0]))

        # Do not modify a PDF if its content cannot be
        # confidently located.
        if not boxes:
            stats["unchanged_no_content_bounds"] += 1
            new_height = old_height
        else:
            content_bottom = max(box.y1 for box in boxes)

            proposed_height = max(
                MIN_HEIGHT,
                content_bottom + BOTTOM_MARGIN
            )

            saving = old_height - proposed_height

            if saving >= MIN_SAVING:
                new_height = proposed_height
                stats["trimmed"] += 1
            else:
                new_height = old_height
                stats["unchanged"] += 1

        # Build a new PDF rather than editing the original.
        output = pymupdf.open()

        new_page = output.new_page(
            width=width,
            height=new_height
        )

        new_page.show_pdf_page(
            new_page.rect,
            original,
            0,
            clip=pymupdf.Rect(
                0, 0, width, new_height
            )
        )

        output.save(
            target,
            garbage=4,
            deflate=True
        )
        output.close()

    report.append({
        "file": str(relative),
        "old_height": round(old_height, 2),
        "new_height": round(new_height, 2),
        "saved_height": round(old_height - new_height, 2),
    })

    if index % 2000 == 0:
        print(f"Processed {index:,}/{len(files):,}")

report_path = DEST / "whitespace_cleanup_report.csv"

with report_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "file",
            "old_height",
            "new_height",
            "saved_height"
        ]
    )
    writer.writeheader()
    writer.writerows(report)

print("\n=== CLEANUP COMPLETE ===")
print("Total PDFs:", len(files))
print("Trimmed:", stats["trimmed"])
print("Unchanged:", stats["unchanged"])
print(
    "No content bounds:",
    stats["unchanged_no_content_bounds"]
)
print("Output:", DEST)
print("Report:", report_path)
print("Original staging files untouched.")
