#!/usr/bin/env python3
"""
clean_db.py
===========
One-off migration: strips everything up to and including `output_questions/`
from the `Question` and `Answer` columns of `past_papers.db`, so both columns
contain only portable relative paths like:
    qp/9618/2024/May_June/12/1(a).pdf

Why this can't be a single blind UPDATE statement
--------------------------------------------------
The `Answer` column is dual-purpose in this schema: for most rows it's a
mark-scheme PDF path, but for the single-question "quiz mode" rows it holds
a literal letter grade ('A'/'B'/'C'/'D'), not a path at all.

A naive string-slice UPDATE would either corrupt those letters or silently
no-op on them. This script explicitly detects which case each value is and
only touches genuine paths, leaving everything else untouched.

Safety features
---------------
* Takes a timestamped backup of the .db file before writing anything
  (unless --no-backup is passed).
* --dry-run: prints exactly what would change, writes nothing.
* Idempotent: safe to run twice — already-relative paths are left alone.
* Anomalous values are never modified — they're logged for manual review.

Usage
-----
    python clean_db.py --db past_papers.db --dry-run
    python clean_db.py --db past_papers.db
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

MARKER = "output_questions/"
VALID_PREFIXES = ("qp/", "ms/")

# Sentinel meaning:
# "This value looks like a path but doesn't match anything we recognise."
_FLAG = object()


def clean_path(value: str | None):
    """
    Clean an absolute question/answer path into a portable relative path.

    Returns:
        - The cleaned relative path if `output_questions/` is found.
        - The original value if it is already clean or is not path-like.
        - `_FLAG` if the value looks like a path but has an unexpected format.
    """
    if not value:
        return value

    normalized = value.replace("\\", "/")
    lower = normalized.lower()

    marker_index = lower.find(MARKER)

    if marker_index != -1:
        return normalized[marker_index + len(MARKER):]

    if normalized.startswith(VALID_PREFIXES):
        return normalized

    looks_like_path = (
        "/" in normalized
        or "\\" in value
        or normalized.lower().endswith(".pdf")
    )

    if not looks_like_path:
        # Examples:
        # "A", "B", "C", "D"
        # These are valid quiz-mode answer values.
        return value

    return _FLAG


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db",
        default="past_papers.db",
        help="Path to past_papers.db",
    )

    parser.add_argument(
        "--table",
        default="past_papers",
        help="Table name (default: past_papers)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing anything",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a .bak copy first (not recommended)",
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="How many example diffs to print",
    )

    return parser.parse_args()


def create_backup(db_path: Path) -> Path:
    """Create a timestamped backup of the database."""
    backup_path = db_path.with_name(
        f"{db_path.stem}.bak_{datetime.now():%Y%m%d_%H%M%S}{db_path.suffix}"
    )

    shutil.copy2(db_path, backup_path)

    print(f"Backup written to: {backup_path}")

    return backup_path


def load_rows(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[sqlite3.Row]:
    """Load the rows that need to be inspected."""
    query = f"""
        SELECT rowid, Question, Answer
        FROM {table_name}
    """

    return conn.execute(query).fetchall()


def process_rows(
    rows: list[sqlite3.Row],
    sample_limit: int,
) -> tuple[
    list[tuple[str, str, int]],
    int,
    list[tuple[int, str, str]],
]:
    """
    Process database rows and determine which records need updating.

    Returns:
        updates:
            Values that should be written back to the database.

        unchanged:
            Number of rows that require no changes.

        flagged:
            Values that look path-like but do not match the expected format.
    """
    updates: list[tuple[str, str, int]] = []
    flagged: list[tuple[int, str, str]] = []
    unchanged = 0
    samples_shown = 0

    for row in rows:
        rowid = row["rowid"]
        original_question = row["Question"]
        original_answer = row["Answer"]

        cleaned_question = clean_path(original_question)
        cleaned_answer = clean_path(original_answer)

        row_flagged = False

        if cleaned_question is _FLAG:
            flagged.append(
                (rowid, "Question", original_question)
            )
            cleaned_question = original_question
            row_flagged = True

        if cleaned_answer is _FLAG:
            flagged.append(
                (rowid, "Answer", original_answer)
            )
            cleaned_answer = original_answer
            row_flagged = True

        # Never update a row containing an ambiguous value.
        if row_flagged:
            continue

        if (
            cleaned_question != original_question
            or cleaned_answer != original_answer
        ):
            updates.append(
                (
                    cleaned_question,
                    cleaned_answer,
                    rowid,
                )
            )

            if samples_shown < sample_limit:
                print(f"  rowid {rowid}:")

                if cleaned_question != original_question:
                    print(
                        f"    Question: "
                        f"{original_question!r} -> {cleaned_question!r}"
                    )

                if cleaned_answer != original_answer:
                    print(
                        f"    Answer:   "
                        f"{original_answer!r} -> {cleaned_answer!r}"
                    )

                samples_shown += 1
        else:
            unchanged += 1

    return updates, unchanged, flagged


def print_flagged_rows(
    flagged: list[tuple[int, str, str]],
    limit: int = 25,
) -> None:
    """Print values that require manual review."""
    if not flagged:
        return

    print(
        "\nFlagged rows "
        "(value looked path-like but didn't match the expected structure):"
    )

    for rowid, column, value in flagged[:limit]:
        print(f"  rowid {rowid} [{column}]: {value!r}")

    if len(flagged) > limit:
        print(f"  ... and {len(flagged) - limit} more.")


def print_summary(
    updates: list[tuple[str, str, int]],
    unchanged: int,
    flagged: list[tuple[int, str, str]],
) -> None:
    """Print a summary of the migration."""
    print("-" * 60)
    print(f"Rows to update:  {len(updates)}")
    print(
        "Rows unchanged:  "
        f"{unchanged} "
        "(already clean, or not a path e.g. a quiz letter answer)"
    )
    print(
        f"Rows flagged:    {len(flagged)} "
        "(left untouched — need manual review)"
    )


def apply_updates(
    conn: sqlite3.Connection,
    table_name: str,
    updates: list[tuple[str, str, int]],
) -> None:
    """Apply all database updates inside a single transaction."""
    if not updates:
        print("\nNothing to commit.")
        return

    query = f"""
        UPDATE {table_name}
        SET Question = ?, Answer = ?
        WHERE rowid = ?
    """

    try:
        conn.executemany(query, updates)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    print(f"\nCommitted {len(updates)} row updates.")


def run_sanity_check(
    conn: sqlite3.Connection,
    table_name: str,
) -> int:
    """
    Check for values that still appear to contain absolute paths.

    Returns:
        Number of rows containing suspicious path values.
    """
    query = f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE Question LIKE '%output_questions%'
           OR Answer LIKE '%output_questions%'
           OR Question LIKE '%:/%'
           OR Answer LIKE '%:/%'
           OR Question LIKE '%\\%'
           OR Answer LIKE '%\\%'
    """

    leftover = conn.execute(query).fetchone()[0]

    print(
        "Post-migration check: "
        f"{leftover} row(s) still contain an absolute-looking path."
    )

    if leftover:
        print(
            "These are likely the flagged rows above, "
            "or genuinely unusual data — check manually."
        )

    return leftover


def main() -> None:
    """Run the database cleanup migration."""
    args = parse_args()

    if args.sample < 0:
        print(
            "ERROR: --sample must be zero or greater.",
            file=sys.stderr,
        )
        sys.exit(1)

    db_path = Path(args.db)

    if not db_path.exists():
        print(
            f"ERROR: database not found at {db_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.dry_run and not args.no_backup:
        create_backup(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        rows = load_rows(conn, args.table)

        print(
            f"Loaded {len(rows)} rows from '{args.table}'."
        )

        updates, unchanged, flagged = process_rows(
            rows,
            args.sample,
        )

        print_summary(
            updates,
            unchanged,
            flagged,
        )

        print_flagged_rows(flagged)

        if args.dry_run:
            print(
                "\nDry run — no changes written. "
                "Re-run without --dry-run to apply."
            )
            return

        apply_updates(
            conn,
            args.table,
            updates,
        )

        run_sanity_check(
            conn,
            args.table,
        )

    except sqlite3.Error as exc:
        print(
            f"ERROR: SQLite operation failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()