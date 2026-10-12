from pathlib import Path
import csv
import html
import base64
import pymupdf

desktop = Path.home() / "Desktop"
source = desktop / "pastify_mcq_full_staging"
clean = desktop / "pastify_mcq_working_space_cleaned"
report = clean / "working_space_cleanup_report.csv"

with report.open(newline="") as f:
    flagged = [
        row["file"]
        for row in csv.DictReader(f)
        if row["decision"] == "review"
    ]

def render(page):
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )
    return base64.b64encode(
        pix.tobytes("png")
    ).decode("ascii")

out = desktop / "pastify_mcq_remaining_review.html"

with out.open("w", encoding="utf-8") as f:
    f.write("""
<html>
<head>
<meta charset="utf-8">
<title>Remaining MCQ Review</title>
<style>
body { font-family: Arial; margin: 24px; }
.item { border-top: 2px solid #ccc; padding: 20px 0; }
.pair { display: flex; gap: 20px; align-items: flex-start; }
.panel { width: 50%; }
img { width: 100%; border: 1px solid #aaa; }
</style>
</head>
<body>
<h1>Remaining 49 Physics MCQs</h1>
<p>Original (left) versus proposed crop (right)</p>
""")

    for relative in flagged:
        with pymupdf.open(source / relative) as doc:
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
                continue

            crop_y = positions[0] - 8
            before = render(page)

            # Render the proposed crop without modifying PDFs.
            crop_rect = pymupdf.Rect(
                0, 0, page.rect.width, crop_y
            )

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                clip=crop_rect,
                alpha=False
            )
            after = base64.b64encode(
                pix.tobytes("png")
            ).decode("ascii")

            f.write(f"""
<section class="item">
<h3>{html.escape(relative)}</h3>
<p>Proposed height: {crop_y:.1f} pt</p>
<div class="pair">
<div class="panel">
<h4>Original</h4>
<img src="data:image/png;base64,{before}">
</div>
<div class="panel">
<h4>Proposed crop</h4>
<img src="data:image/png;base64,{after}">
</div>
</div>
</section>
""")

    f.write("</body></html>")

print("Review gallery:", out)
print("Original and cleaned PDFs untouched.")
