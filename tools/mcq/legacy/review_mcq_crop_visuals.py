from pathlib import Path
import csv
import html
import base64
import pymupdf

desktop = Path.home() / "Desktop"
source_root = desktop / "pastify_mcq_full_staging"
clean_root = desktop / "pastify_mcq_working_space_cleaned"
report_path = clean_root / "working_space_cleanup_report.csv"

with report_path.open(newline="") as f:
    cropped = [
        row["file"]
        for row in csv.DictReader(f)
        if row["decision"] == "cropped"
    ]

def render(path):
    with pymupdf.open(path) as doc:
        pix = doc[0].get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False
        )
        return base64.b64encode(
            pix.tobytes("png")
        ).decode("ascii")

entries = []

for relative in cropped:
    original = source_root / relative
    cleaned = clean_root / relative

    with (
        pymupdf.open(original) as src,
        pymupdf.open(cleaned) as dst
    ):
        page = src[0]
        crop_y = dst[0].rect.height

        drawings = sum(
            1 for d in page.get_drawings()
            if d["rect"].y1 > crop_y + 1
        )

        images = sum(
            1
            for img in page.get_images(full=True)
            for rect in page.get_image_rects(img[0])
            if rect.y1 > crop_y + 1
        )

    if drawings or images:
        entries.append((relative, drawings, images))

out = desktop / "pastify_mcq_crop_review.html"

with out.open("w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>MCQ Crop Review</title>
<style>
body { font-family: Arial, sans-serif; margin: 24px; }
.item { border-top: 2px solid #ddd; padding: 24px 0; }
.pair { display: flex; gap: 20px; align-items: flex-start; }
.panel { width: 50%; }
.panel img { width: 100%; border: 1px solid #aaa; }
h3 { overflow-wrap: anywhere; }
</style>
</head>
<body>
<h1>MCQ Crop Review</h1>
<p>Original (left) vs cleaned (right)</p>
""")

    for relative, drawings, images in entries:
        before = render(source_root / relative)
        after = render(clean_root / relative)

        f.write(f"""
<section class="item">
<h3>{html.escape(relative)}</h3>
<p>Drawings below: {drawings} |
Images below: {images}</p>
<div class="pair">
<div class="panel">
<h4>Original</h4>
<img src="data:image/png;base64,{before}">
</div>
<div class="panel">
<h4>Cropped</h4>
<img src="data:image/png;base64,{after}">
</div>
</div>
</section>
""")

    f.write("</body></html>")

print("Flagged comparisons:", len(entries))
print("Gallery:", out)
print("No question PDFs modified.")
