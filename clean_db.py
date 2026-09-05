#!/usr/bin/env python3
"""
clean_db.py
===========
One-off migration: strips everything up to and including `output_questions/`
from the `Question` and `Answer` columns of `past_papers.db`, so both columns
contain only portable relative paths like `qp/9618/2024/May_June/12/1(a).pdf`.

Why this can't be a single blind UPDATE statement
--------------------------------------------------
The `Answer` column is dual-purpose in this schema: for most rows it's a
mark-scheme PDF path, but for the single-question "quiz mode" rows it holds a
literal letter grade ('A'/'B'/'C'/'D'), not a path at all. A naive
string-slice UPDATE would either corrupt those letters or silently no-op on
them — this script explicitly detects which case each value is and only
touches genuine paths, leaving everything else untouched and logging
anything ambiguous for manual review rather than guessing.

Safety features
----------------
* Takes a timestamped backup of the .db file before writing anything
  (unless --no-backup is passed).
* --dry-run: prints exactly what would change, writes nothing.
* Idempotent: safe to run twice — already-relative paths are left alone.
* Anomalous values (look like a path but don't match the expected
  structure) are never modified — they're logged for you to check by hand.

Usage
-----
    python clean_db.py --db past_papers.db --dry-run   # preview first
    python clean_db.py --db past_papers.db             # apply for real
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


_FLAG = object()  # sentinel meaning "path-shaped but unrecognised — do not touch, flag for review"
# (deliberately distinct from `None`, since `None` is also a legitimate,
#  unchanged value for rows where Question/Answer is genuinely NULL in the DB)


def clean_path(value: str | None):
    """Returns the cleaned relative path, the original value unchanged if it
    was never a path to begin with (NULL, or a quiz-mode letter answer like
    'A'/'B'/'C'/'D'), or the `_FLAG` sentinel if the value looks path-like
    but doesn't match anything we recognise (a signal to flag it, not
    silently touch it)."""
    if not value:
        return value  # NULL / empty — nothing to clean, leave as-is

    normalized = value.replace("\\", "/")
    lower = normalized.lower()

    idx = lower.find(MARKER)
    if idx != -1:
        return normalized[idx + len(MARKER):]

    if lower.startswith(VALID_PREFIXES):
        return normalized  # already clean — no-op, keeps the script idempotent

    looks_like_a_path = "/" in normalized or "\\" in value or normalized.lower().endswith(".pdf")
    if not looks_like_a_path:
        return value  # e.g. a bare letter answer 'A'/'B'/'C'/'D' — nothing to do

    return _FLAG  # path-shaped but unrecognised — flag for manual review


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="past_papers.db", help="Path to past_papers.db")
    parser.add_argument("--table", default="past_papers", help="Table name (default: past_papers)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing anything")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a .bak copy first (not recommended)")
    parser.add_argument("--sample", type=int, default=10, help="How many example diffs to print")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and not args.no_backup:
        backup_path = db_path.with_name(f"{db_path.stem}.bak_{datetime.now():%Y%m%d_%H%M%S}{db_path.suffix}")
        shutil.copy2(db_path, backup_path)
        print(f"Backup written to: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute(f"SELECT rowid, Question, Answer FROM {args.table}").fetchall()
    print(f"Loaded {len(rows)} rows from '{args.table}'.")

    updates: list[tuple[str, str, int]] = []
    unchanged = 0
    flagged: list[tuple[int, str, str]] = []
    samples_shown = 0

    for row in rows:
        rowid = row["rowid"]
        original_q, original_a = row["Question"], row["Answer"]

        cleaned_q = clean_path(original_q)
        cleaned_a = clean_path(original_a)

        row_flagged = False
        if cleaned_q is _FLAG:
            flagged.append((rowid, "Question", original_q))
            cleaned_q = original_q  # never write back an unrecognised value
            row_flagged = True
        if cleaned_a is _FLAG:
            flagged.append((rowid, "Answer", original_a))
            cleaned_a = original_a
            row_flagged = True

        if row_flagged:
            continue

        if cleaned_q != original_q or cleaned_a != original_a:
            updates.append((cleaned_q, cleaned_a, rowid))
            if samples_shown < args.sample:
                print(f"  rowid {rowid}:")
                if cleaned_q != original_q:
                    print(f"    Question: {original_q!r} -> {cleaned_q!r}")
                if cleaned_a != original_a:
                    print(f"    Answer:   {original_a!r} -> {cleaned_a!r}")
                samples_shown += 1
        else:
            unchanged += 1

    print("-" * 60)
    print(f"Rows to update:   {len(updates)}")
    print(f"Rows unchanged:   {unchanged} (already clean, or not a path e.g. a quiz letter answer)")
    print(f"Rows flagged:     {len(flagged)} (left untouched — need manual review)")

    if flagged:
        print("\nFlagged rows (value looked path-like but didn't match the expected structure):")
        for rowid, col, val in flagged[:25]:
            print(f"  rowid {rowid} [{col}]: {val!r}")
        if len(flagged) > 25:
            print(f"  ... and {len(flagged) - 25} more.")

    if args.dry_run:
        print("\nDry run — no changes written. Re-run without --dry-run to apply.")
        conn.close()
        return

    if updates:
        conn.executemany(
            f"UPDATE {args.table} SET Question = ?, Answer = ? WHERE rowid = ?",
            updates,
        )
        conn.commit()
        print(f"\nCommitted {len(updates)} row updates.")
    else:
        print("\nNothing to commit.")

    # Post-migration sanity check
    leftover = conn.execute(
        f"""
        SELECT COUNT(*) FROM {args.table}
        WHERE Question LIKE '%output_questions%' OR Answer LIKE '%output_questions%'
           OR Question LIKE '%:/%' OR Answer LIKE '%:/%'
           OR Question LIKE '%\\%' OR Answer LIKE '%\\%'
        """
    ).fetchone()[0]
    print(f"Post-migration check: {leftover} row(s) still contain an absolute-looking path.")
    if leftover:
        print("These are likely the flagged rows above, or genuinely unusual data — check manually.")

    conn.close()


if __name__ == "__main__":
    main()
