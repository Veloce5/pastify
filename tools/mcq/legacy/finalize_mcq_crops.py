from pathlib import Path
import csv
import shutil
import pymupdf

desktop = Path.home() / "Desktop"
original = desktop / "pastify_mcq_full_staging"
cleaned = desktop / "pastify_mcq_working_space_cleaned"
final = desktop / "pastify_mcq_final_staging"

report_path = cleaned / "working_space_cleanup_report.csv"

if final.exists():
    raise SystemExit(
        f"Destination already exists: {final}\n"
        "No files overwritten."
    )

with report_path.open(newline="") as f:
    rows = list(csv.DictReader(f))

remaining = [
    row["file"]
    for row in rows
    if row["decision"] == "review"
]

if len(remaining) != 49:
    raise SystemExit(
        f"Expected 49 review files, found {len(remaining)}"
    )

print("Copying cleaned collection...")
shutil.copytree(cleaned, final)

completed = 0

for relative in remaining:
    source = original / relative
    target = final / relative

    with pymupdf.open(source) as doc:
        page = doc[0]
        words = page.get_text("words", sort=True)

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

        if len(positions) != 1:
            raise RuntimeError(
                f"Unexpected label count: {relative}"
            )

        new_height = positions[0] - 8

        if not (30 < new_height < page.rect.height):
            raise RuntimeError(
                f"Invalid crop height: {relative}"
            )

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

        temp = target.with_suffix(".tmp.pdf")

        output.save(
            temp,
            garbage=4,
            deflate=True
        )
        output.close()

    temp.replace(target)
    completed += 1

    print(f"[{completed}/49] {relative}")

print("\n=== FINALIZATION COMPLETE ===")
print("Previously cropped:", 677)
print("Newly cropped:", completed)
print("Total cropped:", 677 + completed)
print("Final staging:", final)
print("Original staging untouched.")
print("Previous cleaned staging untouched.")
