"""
Pastify MCQ Batch Processor
===========================

Runs the validated MCQ splitter across selected Cambridge subjects.

Safety:
- Never overwrites an existing output directory.
- Dry-run mode performs no file writes.
- Does not modify the Pastify database or production PDFs.
- Preserves historical Accounting/Economics Paper 3 detection.
"""

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

import mcq_splitter


DEFAULT_SUBJECTS = {
    "9702": "9702 Physics",
    "9706": "9706 Accounting",
    "9708": "9708 Economics",
}

FILENAME_RE = re.compile(
    r"^(?P<subject>\d{4})_"
    r"(?P<session>[swm])"
    r"(?P<year>\d{2})_qp_"
    r"(?P<paper>\d{1,2})\.pdf$",
    re.IGNORECASE,
)

REPORT_COLUMNS = [
    "subject",
    "session",
    "year",
    "paper",
    "source",
    "status",
    "detail",
]


def is_mcq(path, subject, paper):
    if paper.startswith("1"):
        return True

    if not paper.startswith("3") or subject == "9702":
        return False

    with pymupdf.open(path) as doc:
        header = " ".join(
            doc[index].get_text()
            for index in range(min(2, len(doc)))
        ).lower()

    return "multiple choice" in header


def discover_papers(input_root, subjects, subject_folders):
    candidates = {}
    excluded = []
    unmatched = []

    for subject in subjects:
        folder_name = subject_folders.get(subject, subject)
        base = input_root / folder_name

        if not base.is_dir():
            raise FileNotFoundError(
                f"Missing subject folder: {base}"
            )

        for path in sorted(base.rglob("*.pdf")):
            if "_qp_" not in path.name.lower():
                continue

            match = FILENAME_RE.fullmatch(path.name)

            if not match:
                unmatched.append(str(path))
                continue

            code = match.group("subject")
            session = match.group("session").lower()
            year = match.group("year")
            paper = match.group("paper")

            if code != subject:
                excluded.append(
                    ("subject_mismatch", str(path))
                )
                continue

            key = (code, session, year, paper)

            if key in candidates:
                excluded.append(
                    ("duplicate", str(path))
                )
                continue

            try:
                eligible = is_mcq(path, code, paper)
            except Exception as exc:
                excluded.append(
                    ("classification_error", f"{path}: {exc}")
                )
                continue

            if eligible:
                candidates[key] = path
            else:
                excluded.append(
                    ("not_mcq", str(path))
                )

    return candidates, excluded, unmatched


def write_report(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=REPORT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Batch-process Cambridge MCQ question papers."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Root containing subject folders.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New directory for extracted MCQ PDFs.",
    )

    parser.add_argument(
        "--subjects",
        nargs="+",
        default=list(DEFAULT_SUBJECTS),
        help="Subject codes to process (default: 9702 9706 9708).",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview eligible papers without writing files.",
    )

    args = parser.parse_args()

    input_root = args.input.expanduser().resolve()
    output_root = args.output.expanduser().resolve()

    subjects = list(dict.fromkeys(args.subjects))

    if not input_root.is_dir():
        parser.error(f"Input directory does not exist: {input_root}")

    unsupported = [
        code for code in subjects
        if code not in mcq_splitter.EXPECTED_QUESTIONS
    ]

    if unsupported:
        parser.error(
            "Subjects not supported by the current splitter: "
            + ", ".join(unsupported)
        )

    if output_root.exists():
        parser.error(
            f"Output directory already exists: {output_root}\n"
            "Choose a new destination to avoid overwriting files."
        )

    # Existing Cambridge download folder names are preserved.
    subject_folders = {
        code: DEFAULT_SUBJECTS.get(code, code)
        for code in subjects
    }

    try:
        candidates, excluded, unmatched = discover_papers(
            input_root,
            subjects,
            subject_folders,
        )
    except (FileNotFoundError, OSError) as exc:
        parser.error(str(exc))

    print("=== PASTIFY MCQ BATCH ===")
    print("Input:", input_root)
    print("Output:", output_root)
    print("Subjects:", ", ".join(subjects))
    print("Eligible papers:", len(candidates))
    print("Excluded:", len(excluded))
    print("Unmatched:", len(unmatched))

    subject_counts = Counter(
        key[0] for key in candidates
    )

    for subject in subjects:
        print(
            f"  {subject}: {subject_counts[subject]} eligible papers"
        )

    if args.dry_run:
        print("\n=== DRY RUN ===")
        for key, path in sorted(candidates.items()):
            print(f"{key[0]} | {path.name}")

        print("\nNo files created or modified.")
        return

    if not candidates:
        print("\nNo eligible papers found. No output created.")
        return

    output_root.mkdir(parents=True, exist_ok=False)

    results = []
    counts = Counter()

    for index, (key, path) in enumerate(
        sorted(candidates.items()),
        start=1,
    ):
        try:
            status, detail = mcq_splitter.process_pdf(
                path,
                output_root,
            )
        except Exception as exc:
            status, detail = "failed", repr(exc)

        counts[status] += 1

        results.append({
            "subject": key[0],
            "session": key[1],
            "year": key[2],
            "paper": key[3],
            "source": str(path),
            "status": status,
            "detail": str(detail),
        })

        print(
            f"[{index}/{len(candidates)}] "
            f"{status.upper()}: {path.name} — {detail}",
            flush=True,
        )

    report = output_root / "batch_report.csv"

    write_report(report, results)

    with (output_root / "excluded_sources.txt").open(
        "w", encoding="utf-8"
    ) as file:
        for reason, path in excluded:
            file.write(f"{reason}\t{path}\n")

    with (output_root / "unmatched_sources.txt").open(
        "w", encoding="utf-8"
    ) as file:
        for path in unmatched:
            file.write(path + "\n")

    print("\n=== FINAL SUMMARY ===")
    print("Eligible:", len(candidates))
    print("Successful:", counts["success"])
    print("Review:", counts["review"])
    print("Failed:", counts["failed"])
    print("Skipped:", counts["skipped"])
    print("Report:", report)
    print("Production database and PDFs untouched.")


if __name__ == "__main__":
    main()
