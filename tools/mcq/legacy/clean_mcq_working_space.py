from pathlib import Path
from collections import Counter
import csv
import re
import shutil
import pymupdf

SOURCE = Path.home() / "Desktop/pastify_mcq_full_staging"
DEST = Path.home() / "Desktop/pastify_mcq_working_space_cleaned"

if not SOURCE.is_dir():
    raise SystemExit(f"Missing source: {SOURCE}")

if DEST.exists():
    raise SystemExit(
        f"Destination already exists: {DEST}. "
        "Nothing overwritten."
    )

files = sorted(SOURCE.glob("*/*/*.pdf"))

if len(files) != 17630:
    raise SystemExit(
        f"Expected 17,630 PDFs, found {len(files)}"
    )

DEST.mkdir(parents=True)

stats = Counter()
report = []

def label_positions(words):
    positions = []

    for i in range(len(words) - 2):
        phrase = " ".join(
            str(words[j][4]).lower().strip(" :")
            for j in range(i, i + 3)
        )

        if phrase == "space for working":
            positions.append(
                min(words[j][1] for j in range(i, i + 3))
            )

    return positions


for index, source in enumerate(files, 1):
    relative = source.relative_to(SOURCE)
    subject = relative.parts[0]

    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)

    decision = "copied"
    detail = ""

    with pymupdf.open(source) as doc:
        page = doc[0]
        full_text = " ".join(
            page.get_text().lower().split()
        )

        if (
            subject != "9702"
            or "space for working" not in full_text
        ):
            shutil.copy2(source, target)
            stats["copied"] += 1

        else:
            words = page.get_text("words", sort=True)
            positions = label_positions(words)

            if len(positions) != 1:
                decision = "review"
                detail = (
                    f"Expected one label, "
                    f"found {len(positions)}"
                )

            else:
                new_height = positions[0] - 8

                upper_text = page.get_text(
                    clip=pymupdf.Rect(
                        0, 0,
                        page.rect.width,
                        new_height
                    )
                )

                choices = {
                    letter for letter in "ABCD"
                    if re.search(
                        rf"(?<![A-Za-z]){letter}(?![A-Za-z])",
                        upper_text
                    )
                }

                if choices != set("ABCD"):
                    decision = "review"
                    detail = "Answer labels not confidently detected"

                elif new_height < 100:
                    decision = "review"
                    detail = "Crop would be unusually short"

                else:
                    output = pymupdf.open()

                    new_page = output.new_page(
                        width=page.rect.width,
                        height=new_height
                    )

                    new_page.show_pdf_page(
                        new_page.rect,
                        doc,
                        0,
                        clip=pymupdf.Rect(
                            0, 0,
                            page.rect.width,
                            new_height
                        )
                    )

                    output.save(
                        target,
                        garbage=4,
                        deflate=True
                    )

                    output.close()

                    decision = "cropped"
                    detail = (
                        f"{page.rect.height:.1f} "
                        f"→ {new_height:.1f} pt"
                    )

            if decision == "review":
                shutil.copy2(source, target)

            stats[decision] += 1

    report.append({
        "file": str(relative),
        "decision": decision,
        "detail": detail,
    })

    if index % 2000 == 0:
        print(f"Processed {index:,}/{len(files):,}")

report_path = DEST / "working_space_cleanup_report.csv"

with report_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["file", "decision", "detail"]
    )
    writer.writeheader()
    writer.writerows(report)

print("\n=== WORKING SPACE CLEANUP ===")
print("Total PDFs:", len(files))
print("Cropped:", stats["cropped"])
print("Copied unchanged:", stats["copied"])
print("Flagged for review:", stats["review"])
print("Output:", DEST)
print("Report:", report_path)
print("Original staging untouched.")
