#!/usr/bin/env python3
"""
Pastify MCQ Splitter - Version 12

Extract Cambridge MCQ question papers into individual PDFs.

Supported for testing:
    9702 - Physics: 40 questions
    9706 - Accounting: 30 questions
    9708 - Economics: 30 questions

Original PDFs and Pastify databases are never modified.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

import pymupdf


FILENAME_RE = re.compile(
    r"(?P<subject>\d{4})_[swm]\d{2}_qp_(?P<paper>\d{2})\.pdf$",
    re.IGNORECASE,
)

EXPECTED_QUESTIONS = {
    "9702": 40,
    "9706": 30,
    "9708": 30,
}

TOP_PADDING = 5
BOTTOM_PADDING = 9

VERY_TALL_HEIGHT = 650

IGNORE_TEXT = (
    "© UCLES",
    "© CAMBRIDGE",
    "BLANK PAGE",
    "PERMISSION TO REPRODUCE",
    "COPYRIGHT ACKNOWLEDGEMENTS",
    "COPYRIGHT ACKNOWLEDGMENTS",
    "TO AVOID THE ISSUE OF DISCLOSURE",
    "CAMBRIDGE ASSESSMENT INTERNATIONAL EDUCATION IS PART OF",
    "UNIVERSITY OF CAMBRIDGE LOCAL EXAMINATIONS SYNDICATE",
)

ADMINISTRATIVE_PHRASES = (
    "PERMISSION TO REPRODUCE",
    "EVERY REASONABLE EFFORT HAS BEEN MADE",
    "TO AVOID THE ISSUE OF DISCLOSURE",
    "COPYRIGHT ACKNOWLEDGEMENTS BOOKLET",
    "COPYRIGHT ACKNOWLEDGMENTS BOOKLET",
    "CAMBRIDGE ASSESSMENT INTERNATIONAL EDUCATION IS PART OF",
    "UNIVERSITY OF CAMBRIDGE LOCAL EXAMINATIONS SYNDICATE",
)


def is_ignored_text(text):
    cleaned = " ".join(text.upper().split())

    if not cleaned:
        return True

    return any(
        cleaned.startswith(prefix.upper())
        for prefix in IGNORE_TEXT
    )


def is_administrative_page(page):
    """
    Identify an explicitly labelled Cambridge BLANK PAGE.

    Handles both short blank pages and pages containing
    standard copyright notices.

    Does not remove pages simply because they contain
    copyright-related wording.
    """
    normalized = " ".join(
        page.get_text().upper().split()
    )

    if "BLANK PAGE" not in normalized:
        return False

    # A normal question page should not be classified as
    # administrative just because it mentions a blank page.
    if not re.search(r"\bBLANK PAGE\b", normalized):
        return False

    # Remove the BLANK PAGE label and common page furniture.
    remaining = normalized.replace("BLANK PAGE", "")

    remaining = re.sub(
        r"\b\d{4}/\d{2}/[A-Z]/[A-Z]/\d{2}\b",
        "",
        remaining,
    )

    remaining = remaining.replace("[TURN OVER]", "")

    remaining = re.sub(
        r"©[^.]*",
        "",
        remaining,
    )

    remaining = re.sub(
        r"^\s*\d{1,3}\s*",
        "",
        remaining,
    )

    # Short administrative pages were already handled in V5.
    if len(remaining.strip()) < 80:
        return True

    # Long copyright pages must contain several known
    # administrative phrases to qualify.
    phrase_matches = sum(
        phrase in normalized
        for phrase in ADMINISTRATIVE_PHRASES
    )

    return phrase_matches >= 2


def collect_number_candidates(doc):
    candidates = []

    for page_index, page in enumerate(doc):
        for word in page.get_text("words"):
            x0, y0, x1, y1, value, *_ = word
            value = value.strip()

            if not value.isdigit():
                continue

            number = int(value)

            if not 1 <= number <= 100:
                continue

            if not (30 <= x0 <= page.rect.width * 0.35):
                continue

            if not (55 <= y0 <= page.rect.height * 0.93):
                continue

            candidates.append(
                {
                    "number": number,
                    "page": page_index,
                    "x": x0,
                    "y": y0,
                }
            )

    return candidates


def find_question_anchors(doc, expected):
    candidates = collect_number_candidates(doc)

    if not candidates:
        raise ValueError(
            "No question-number candidates detected"
        )

    x_counts = Counter(
        round(candidate["x"] / 5) * 5
        for candidate in candidates
    )

    possible_x = [
        value
        for value, _ in x_counts.most_common()
    ]

    best_sequence = []

    for dominant_x in possible_x:
        filtered = [
            candidate
            for candidate in candidates
            if abs(candidate["x"] - dominant_x) <= 8
        ]

        filtered.sort(
            key=lambda item: (
                item["page"],
                item["y"],
            )
        )

        sequence = []
        next_number = 1

        for candidate in filtered:
            if candidate["number"] == next_number:
                sequence.append(candidate)
                next_number += 1

                if len(sequence) == expected:
                    break

        if len(sequence) > len(best_sequence):
            best_sequence = sequence

        if len(sequence) == expected:
            return sequence

    raise ValueError(
        f"Detected {len(best_sequence)} of "
        f"{expected} expected questions"
    )



def copyright_boundary(page, question_top):
    """
    Find a clearly identified administrative section near
    the bottom of a page, after the question begins.

    Returns None if no suitable boundary is found.
    """
    starts = []

    for block in page.get_text("blocks"):
        if len(block) <= 4:
            continue

        text = " ".join(str(block[4]).upper().split())

        if not any(
            phrase in text
            for phrase in ADMINISTRATIVE_PHRASES
        ):
            continue

        y = block[1]

        if (
            y > question_top
            and y > page.rect.height * 0.70
        ):
            starts.append(y)

    if not starts:
        return None

    return min(starts) - 10


def content_bottom(page, top, limit):
    bottom = None

    # Text content
    for block in page.get_text("blocks"):
        x0, y0, x1, y1 = block[:4]

        if y1 <= top or y0 >= limit:
            continue

        if y0 < 55:
            continue

        if y0 > page.rect.height - 65:
            continue

        text = block[4] if len(block) > 4 else ""

        if is_ignored_text(text):
            continue

        candidate_bottom = min(y1, limit)

        if bottom is None or candidate_bottom > bottom:
            bottom = candidate_bottom

    # Drawings, diagrams and table borders
    for drawing in page.get_drawings():
        rect = drawing["rect"]

        # V5 footer separator fix
        if (
            rect.width > page.rect.width * 0.75
            and rect.height < 3
            and rect.y0 > page.rect.height * 0.75
        ):
            continue

        if rect.y1 <= top or rect.y0 >= limit:
            continue

        if rect.y0 < 55:
            continue

        if rect.y0 > page.rect.height - 65:
            continue

        candidate_bottom = min(rect.y1, limit)

        if bottom is None or candidate_bottom > bottom:
            bottom = candidate_bottom

    # Images
    for image_info in page.get_image_info():
        rect = pymupdf.Rect(image_info["bbox"])

        if rect.y1 <= top or rect.y0 >= limit:
            continue

        candidate_bottom = min(rect.y1, limit)

        if bottom is None or candidate_bottom > bottom:
            bottom = candidate_bottom

    return bottom


def extract_question(source_doc, anchors, index):
    start = anchors[index]

    end = (
        anchors[index + 1]
        if index + 1 < len(anchors)
        else None
    )

    output_doc = pymupdf.open()

    last_page = (
        end["page"]
        if end is not None
        else len(source_doc) - 1
    )

    for page_index in range(
        start["page"],
        last_page + 1,
    ):
        source_page = source_doc[page_index]

        top = (
            max(0, start["y"] - TOP_PADDING)
            if page_index == start["page"]
            else 55
        )

        if (
            end is not None
            and page_index == end["page"]
        ):
            limit = max(
                top,
                end["y"] - TOP_PADDING,
            )
        else:
            limit = source_page.rect.height

        # V12: Exclude a recognised copyright section
        # below the question without removing its page.
        if end is None:
            boundary = copyright_boundary(source_page, top)

            if boundary is not None:
                limit = min(limit, boundary)

        if limit <= top:
            continue

        # When the next question starts in the page-header
        # region, do not create a tiny continuation page
        # from the area immediately above its anchor.
        if (
            end is not None
            and page_index == end["page"]
            and page_index != start["page"]
            and end["y"] < 80
        ):
            continue

        # Ignore a next-question page when the only content
        # before its anchor is an image overlapping that anchor.
        # Such images can be page decorations rather than
        # actual continuations of the previous question.
        if (
            end is not None
            and page_index == end["page"]
            and page_index != start["page"]
        ):
            meaningful_text = any(
                block[1] >= top
                and block[1] < limit
                and not is_ignored_text(block[4])
                for block in source_page.get_text("blocks")
                if len(block) > 4
            )

            meaningful_drawings = any(
                drawing["rect"].y0 >= top
                and drawing["rect"].y0 < limit
                for drawing in source_page.get_drawings()
            )

            if not meaningful_text and not meaningful_drawings:
                continue

        # V6: Skip recognised administrative pages,
        # including long Cambridge copyright pages.
        if is_administrative_page(source_page):
            continue

        bottom = content_bottom(
            source_page,
            top,
            limit,
        )

        if bottom is None:
            continue

        bottom = min(
            source_page.rect.height,
            limit,
            bottom + BOTTOM_PADDING,
        )

        if bottom <= top:
            continue

        crop = pymupdf.Rect(
            0,
            top,
            source_page.rect.width,
            bottom,
        )

        output_page = output_doc.new_page(
            width=crop.width,
            height=crop.height,
        )

        output_page.show_pdf_page(
            output_page.rect,
            source_doc,
            page_index,
            clip=crop,
        )

    # Check again after extraction.
    for page_index in range(
        len(output_doc) - 1,
        -1,
        -1,
    ):
        if is_administrative_page(
            output_doc[page_index]
        ):
            output_doc.delete_page(page_index)

    return output_doc


def validate_extracted_questions(extracted):
    """
    Return warnings for structurally suspicious PDFs.

    Multi-page questions are flagged, not deleted.
    """
    warnings = []

    for index, question_doc in enumerate(
        extracted,
        start=1,
    ):
        if len(question_doc) > 1:
            warnings.append(
                f"Q{index}: {len(question_doc)} pages"
            )

        for page_number, page in enumerate(
            question_doc,
            start=1,
        ):
            if page.rect.height > VERY_TALL_HEIGHT:
                warnings.append(
                    f"Q{index} page {page_number}: "
                    f"height {page.rect.height:.1f} pt"
                )

    return warnings


def process_pdf(pdf_path, output_root):
    match = FILENAME_RE.match(pdf_path.name)

    if not match:
        return "skipped", "Unrecognized filename"

    subject = match.group("subject")
    paper = match.group("paper")

    if subject not in EXPECTED_QUESTIONS:
        return "skipped", "Subject not enabled"

    if not paper.startswith("1"):
        return "skipped", "Not an MCQ paper"

    expected = EXPECTED_QUESTIONS[subject]

    with pymupdf.open(pdf_path) as source_doc:
        anchors = find_question_anchors(
            source_doc,
            expected,
        )

        if len(anchors) != expected:
            raise ValueError(
                "Question count validation failed"
            )

        extracted = []

        try:
            for index in range(expected):
                question_doc = extract_question(
                    source_doc,
                    anchors,
                    index,
                )

                if len(question_doc) == 0:
                    question_doc.close()

                    raise ValueError(
                        f"Question {index + 1} is empty"
                    )

                extracted.append(question_doc)

            warnings = validate_extracted_questions(
                extracted
            )

            output_dir = (
                output_root
                / subject
                / pdf_path.stem
            )

            output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            for index, question_doc in enumerate(
                extracted,
                start=1,
            ):
                question_doc.save(
                    str(output_dir / f"{index}.pdf"),
                    garbage=4,
                    deflate=True,
                )

            if warnings:
                return (
                    "review",
                    f"{expected} questions saved; "
                    + "; ".join(warnings),
                )

            return (
                "success",
                f"{expected} questions saved",
            )

        finally:
            for question_doc in extracted:
                question_doc.close()


def find_pdfs(input_path):
    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        return sorted(
            input_path.rglob("*.pdf")
        )

    raise FileNotFoundError(
        f"Input does not exist: {input_path}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Split Cambridge MCQ papers into "
            "individual question PDFs"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="PDF file or directory containing PDFs",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Directory for extracted question PDFs",
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    ).expanduser()

    output_root = Path(
        args.output
    ).expanduser()

    try:
        pdf_files = find_pdfs(input_path)
    except OSError as exc:
        parser.error(str(exc))

    if not pdf_files:
        parser.error(f"No PDF files found in: {input_path}")

    successes = 0
    reviews = 0
    failures = 0
    skipped = 0

    for pdf_path in pdf_files:
        try:
            status, message = process_pdf(
                pdf_path,
                output_root,
            )

            if status == "success":
                successes += 1
                print(
                    f"SUCCESS: {pdf_path.name}: {message}"
                )

            elif status == "review":
                reviews += 1
                print(
                    f"REVIEW: {pdf_path.name}: {message}"
                )

            else:
                skipped += 1

        except Exception as exc:
            failures += 1
            print(
                f"FAILED: {pdf_path.name}: {exc}"
            )

    print("\nMCQ SPLITTING SUMMARY")
    print(f"Successful papers: {successes}")
    print(f"Review papers: {reviews}")
    print(f"Failed papers: {failures}")
    print(f"Skipped papers: {skipped}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
