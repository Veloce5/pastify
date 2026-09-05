#!/usr/bin/env python3
"""
split_papers.py  (v2 — multi-tier anchor detection + MCQ awareness + zero-drop fallback)
==========================================================================================
Slices full-length CAIE A-Level past papers (Question Papers + Mark Schemes)
into per-question PDF snippets, matched against `past_papers.db`.

--------------------------------------------------------------------------
What changed from v1, and why
--------------------------------------------------------------------------
v1 located question-number anchors using a single pass over PyMuPDF's
coarse `page.get_text("blocks")` output, with a fixed left-margin cutoff.
That failed in two well-defined ways, both now fixed:

1. MCQ Mark Schemes (ms_11/12/13...) are usually a 1-2 page grid:
   "1 A | 11 C | 21 B | 31 D" laid out in 2-4 *vertical strips*. Columns
   2-4 sit in the middle/right of the page, so the old left-margin check
   rejected them outright — and even if found, a single grid cell ("C")
   can't be sliced into a meaningful standalone snippet anyway. These are
   now detected as MCQ mark schemes and the ENTIRE document is assigned to
   every question in that paper (see `is_mcq_paper` / `_process_mcq_mark_scheme`).

2. Theory/MCQ Question Papers sometimes have the question number bolded,
   indented past the margin, or merged by PyMuPDF into the same coarse
   text block as the stem (especially with 2-4 short MCQ items per page).
   Anchor detection is now a 3-tier cascade — block, then line, then span
   — each tier only searching for whatever the previous tier couldn't find
   (see `find_anchors_multitier`). The span tier additionally treats an
   isolated BOLD numeric span as a valid anchor even with no trailing text
   in that same span, which block/line-level text matching can't do.

3. Zero-Drop Fallback: if all three tiers still can't pin down a precise
   y-coordinate for some question, it is no longer dropped. It gets the
   page range bounded by its nearest resolved neighbours (or the whole
   document, in the worst case) — a snippet with extra context beats a
   missing snippet. See `compute_ranges_with_fallback`.

--------------------------------------------------------------------------
Granularity, restated (still true in v2)
--------------------------------------------------------------------------
Question Papers are sliced at TOP-LEVEL question granularity (all of
Question 1's pages, sub-parts included, as one PDF) — CAIE QPs don't mark
(a)/(b) sub-parts as separate visual anchors, so that's the finest
reliable grain without OCR. Every DB row under that top-level number gets
the same extracted PDF. Non-MCQ Mark Schemes ARE sliced at full sub-part
granularity, since official CAIE mark scheme tables print "1(a)", "2(d)(iii)"
etc. as literal row labels.

--------------------------------------------------------------------------
A note on the MCQ mark-scheme detection rule
--------------------------------------------------------------------------
The brief for this version said "if Paper_number == 1 ... use the MCQ
strategy." For mark schemes specifically, that's deliberately tightened to
Paper_number == 1 AND a high count of bare (no sub-part) question numbers
in the DB, because Paper_number alone isn't reliable across all five
subjects (some Paper 1 variants are structured, not MCQ), and the MCQ-MS
path trades away precise slicing entirely. Question papers still use the
plain Paper_number == 1 OR high-bare-count check, and always fall back to
whole-page extraction if anchoring fails anyway — so nothing is silently
lost either way. See `is_mcq_paper`.

--------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------
    python split_papers.py --input "/path/to/raw/papers" \\
                            --db "past_papers.db" \\
                            --output "output_questions" \\
                            [--dry-run] [--margin-fraction 0.18]

Requires: PyMuPDF (`pip install pymupdf`). tqdm is optional.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# ===========================================================================
# Configuration constants
# ===========================================================================
SESSION_DB = {"s": "May/June", "w": "Oct/Nov", "m": "Feb/March"}
SESSION_FOLDER = {"s": "May_June", "w": "Oct_Nov", "m": "Feb_March"}

DEFAULT_MARGIN_FRACTION = 0.18
CROP_GAP = 3.0

# MCQ-paper detection thresholds — see is_mcq_paper for the rationale.
MCQ_BARE_THRESHOLD_PAPER1 = 15
MCQ_BARE_THRESHOLD_GENERIC = 30

FILENAME_RE = re.compile(
    r"(?P<subject>\d{4})_(?P<sess>[swm])(?P<yy>\d{2})_(?P<type>qp|ms)_(?P<variant>\d{2})",
    re.IGNORECASE,
)


# ===========================================================================
# Data classes
# ===========================================================================
@dataclass
class ParsedFilename:
    subject_code: str
    year: int
    session_letter: str
    paper_type: str  # "qp" or "ms"
    variant_code: str  # e.g. "12", "41"

    @property
    def db_session(self) -> str:
        return SESSION_DB[self.session_letter]

    @property
    def folder_session(self) -> str:
        return SESSION_FOLDER[self.session_letter]

    @property
    def paper_number(self) -> int:
        return int(self.variant_code[0])

    def label(self) -> str:
        return f"{self.subject_code}/{self.year}/{self.paper_type.upper()}/{self.variant_code}"


@dataclass
class RunStats:
    files_seen: int = 0
    files_parsed: int = 0
    files_skipped_unparsed: int = 0
    files_skipped_no_db_rows: int = 0
    files_corrupted: int = 0

    mcq_qp_files: int = 0
    theory_qp_files: int = 0
    mcq_ms_files: int = 0
    theory_ms_files: int = 0

    questions_saved: int = 0
    questions_unresolved: int = 0  # should stay 0 thanks to the fallback; nonzero here is a red flag
    fallback_used: int = 0         # precise anchor NOT found; page-range fallback used instead
    mcq_ms_whole_doc_assigned: int = 0

    tier_hits: Counter = field(default_factory=Counter)  # {"block": n, "line": n, "span": n}
    unresolved_details: list = field(default_factory=list)


# ===========================================================================
# Step 1 — Filename parsing (regex only, folder names are never inspected)
# ===========================================================================
def parse_filename(filename: str) -> Optional[ParsedFilename]:
    match = FILENAME_RE.search(filename)
    if not match:
        return None
    g = match.groupdict()
    session_letter = g["sess"].lower()
    if session_letter not in SESSION_DB:
        return None
    return ParsedFilename(
        subject_code=g["subject"],
        year=2000 + int(g["yy"]),
        session_letter=session_letter,
        paper_type=g["type"].lower(),
        variant_code=g["variant"],
    )


# ===========================================================================
# Step 2 — Question-number parsing / sorting helpers
# ===========================================================================
_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def roman_to_int(s: str) -> int:
    s = s.lower()
    total, prev = 0, 0
    for ch in reversed(s):
        val = _ROMAN_VALUES.get(ch, 0)
        total += -val if val < prev else val
        prev = max(prev, val)
    return total


LABEL_RE = re.compile(r"^(\d+)((?:\s*\([a-zA-Z]+\))*)\s*$")


def parse_question_number(label: str) -> Optional[tuple]:
    """'2(d)(iii)' -> (2, 'd', 3). '6' -> (6, '', 0). None if unparseable."""
    m = LABEL_RE.match(label.strip())
    if not m:
        return None
    main = int(m.group(1))
    sub_groups = re.findall(r"\(([a-zA-Z]+)\)", m.group(2))
    letter = sub_groups[0].lower() if sub_groups else ""
    roman = roman_to_int(sub_groups[1]) if len(sub_groups) > 1 else 0
    return (main, letter, roman)


def label_to_anchor_regex(label: str) -> re.Pattern:
    """Builds a regex that matches `label` even with slightly different
    internal spacing, e.g. '2 (d) (iii)' vs '2(d)(iii)'."""
    m = LABEL_RE.match(label.strip())
    if not m:
        return re.compile(re.escape(label))
    num = m.group(1)
    groups = re.findall(r"\(([a-zA-Z]+)\)", m.group(2))
    pattern = re.escape(num)
    for grp in groups:
        pattern += r"\s*\(\s*" + re.escape(grp) + r"\s*\)"
    return re.compile(r"^\s*" + pattern)


# ===========================================================================
# Step 3 — Database lookup
# ===========================================================================
def get_paper_rows(conn: sqlite3.Connection, parsed: ParsedFilename) -> list[dict]:
    rows = conn.execute(
        """
        SELECT Question_Number, Marks FROM past_papers
        WHERE Subject_code = ? AND Year = ? AND Variant = ?
          AND Paper_number = ? AND Paper_variant = ?
        """,
        (parsed.subject_code, parsed.year, parsed.db_session,
         parsed.paper_number, parsed.variant_code),
    ).fetchall()

    parsed_rows = []
    for question_number, marks in rows:
        key = parse_question_number(question_number)
        if key is None:
            logging.warning("Unparseable Question_Number in DB: %r — skipping this row.", question_number)
            continue
        parsed_rows.append({"question_number": question_number, "marks": marks, "sort_key": key})

    parsed_rows.sort(key=lambda r: r["sort_key"])
    return parsed_rows


def is_mcq_paper(parsed: ParsedFilename, db_rows: list[dict]) -> bool:
    """True if this paper should use the MCQ strategy. See the module
    docstring section "A note on the MCQ mark-scheme detection rule" for
    the reasoning behind combining Paper_number with a bare-question-count
    check rather than trusting Paper_number alone."""
    if not db_rows:
        return False
    bare_rows = [r for r in db_rows if r["sort_key"][1] == ""]
    all_bare = len(bare_rows) == len(db_rows)
    bare_count = len(bare_rows)

    if parsed.paper_number == 1 and all_bare and bare_count >= MCQ_BARE_THRESHOLD_PAPER1:
        return True
    if all_bare and bare_count >= MCQ_BARE_THRESHOLD_GENERIC:
        return True
    return False


# ===========================================================================
# Step 4 — Multi-tier anchor detection (Block -> Line -> Span)
# ===========================================================================
def _iter_units(page: fitz.Page, level: str):
    """Yields (x0, y0, x1, y1, text, is_bold) in reading order, at the
    requested granularity. `is_bold` is only ever meaningful at the 'span'
    level — it's False elsewhere since style info isn't tracked there."""
    if level == "block":
        try:
            blocks = page.get_text("blocks", sort=True)
        except TypeError:  # older PyMuPDF without the `sort` kwarg
            blocks = sorted(page.get_text("blocks"), key=lambda b: (round(b[1], 1), b[0]))
        for b in blocks:
            yield b[0], b[1], b[2], b[3], b[4], False
        return

    raw = page.get_text("dict")
    units = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # skip images etc.
            continue
        for line in block.get("lines", []):
            if level == "line":
                x0, y0, x1, y1 = line["bbox"]
                text = "".join(span.get("text", "") for span in line.get("spans", []))
                units.append((x0, y0, x1, y1, text, False))
            else:  # "span"
                for span in line.get("spans", []):
                    x0, y0, x1, y1 = span["bbox"]
                    flags = span.get("flags", 0)
                    font = span.get("font", "")
                    is_bold = bool(flags & (1 << 4)) or "bold" in font.lower()
                    units.append((x0, y0, x1, y1, span.get("text", ""), is_bold))

    units.sort(key=lambda u: (round(u[1], 1), u[0]))
    yield from units


def _scan_for_anchors(doc: fitz.Document, expected: list, margin_fraction: float,
                       mode: str, level: str) -> tuple[dict, list]:
    """Single-tier pass. mode: 'top_level' (int keys, QP) or 'full_label'
    (str keys, MS). Returns ({key: (page_idx, y0)}, [still-unresolved keys])."""
    anchors: dict = {}
    remaining = list(expected)

    for page_idx in range(doc.page_count):
        if not remaining:
            break
        page = doc[page_idx]
        margin_x = page.rect.width * margin_fraction
        target = remaining[0]
        target_re = label_to_anchor_regex(target) if mode == "full_label" else None

        for x0, y0, x1, y1, text, is_bold in _iter_units(page, level):
            if x0 > margin_x:
                continue

            if mode == "top_level":
                stripped = text.lstrip()
                m = re.match(r"^(\d{1,2})\b", stripped)
                if not m or int(m.group(1)) != target:
                    continue
                remainder = stripped[m.end():].strip()
                has_sentence_remainder = bool(remainder) and re.search(r"[A-Za-z]", remainder)
                # At span-granularity, an isolated bold number with (almost)
                # nothing else in the SAME span is itself a strong signal —
                # the sentence typically continues in a sibling span/line.
                isolated_bold_number = level == "span" and is_bold and len(remainder) <= 2
                if not (has_sentence_remainder or isolated_bold_number):
                    continue
                anchors[target] = (page_idx, y0)
                remaining.pop(0)
                if not remaining:
                    break
                target = remaining[0]

            else:  # full_label
                stripped = text.strip()
                match = target_re.match(stripped)
                if not match:
                    continue
                if len(stripped) - match.end() > 3:
                    continue  # more than a trace of extra text — likely a false match
                anchors[target] = (page_idx, y0)
                remaining.pop(0)
                if not remaining:
                    break
                target = remaining[0]
                target_re = label_to_anchor_regex(target)

    return anchors, remaining


def find_anchors_multitier(doc: fitz.Document, expected: list, margin_fraction: float,
                            mode: str) -> tuple[dict, dict, list]:
    """Runs the block -> line -> span cascade. Each tier only searches for
    whatever the previous tier left unresolved. Returns (anchors,
    {key: tier_name}, [still-unresolved after all 3 tiers])."""
    remaining = list(expected)
    anchors: dict = {}
    tier_used: dict = {}

    for level in ("block", "line", "span"):
        if not remaining:
            break
        found, still_missing = _scan_for_anchors(doc, remaining, margin_fraction, mode, level)
        for key, pos in found.items():
            anchors[key] = pos
            tier_used[key] = level
        remaining = still_missing

    return anchors, tier_used, remaining


# ===========================================================================
# Step 5 — Range computation WITH zero-drop fallback
# ===========================================================================
def compute_ranges_with_fallback(anchors: dict, ordered_keys: list) -> dict:
    """Every key in `ordered_keys` gets a range, even if it has no resolved
    anchor of its own. Unresolved keys fall back to the span bounded by
    their nearest resolved neighbours (or the whole document, in the worst
    case where nothing at all was resolved).

    Returns {key: (start_page, start_y, end_page_or_None, end_y_or_None, is_fallback)}.
    """
    resolved_indices = [i for i, k in enumerate(ordered_keys) if k in anchors]
    ranges = {}

    for i, key in enumerate(ordered_keys):
        if key in anchors:
            start_page, start_y = anchors[key]
            next_idx = next((j for j in resolved_indices if j > i), None)
            if next_idx is not None:
                end_page, end_y = anchors[ordered_keys[next_idx]]
            else:
                end_page, end_y = None, None
            ranges[key] = (start_page, start_y, end_page, end_y, False)
            continue

        prev_idx = max((j for j in resolved_indices if j < i), default=None)
        next_idx = next((j for j in resolved_indices if j > i), None)

        if prev_idx is not None and next_idx is not None:
            start_page, start_y = anchors[ordered_keys[prev_idx]]
            end_page, end_y = anchors[ordered_keys[next_idx]]
        elif prev_idx is not None:
            start_page, start_y = anchors[ordered_keys[prev_idx]]
            end_page, end_y = None, None
        elif next_idx is not None:
            start_page, start_y = 0, 0.0
            end_page, end_y = anchors[ordered_keys[next_idx]]
        else:
            # Nothing at all resolved in this document — worst case, hand
            # back the entire thing rather than drop the question.
            start_page, start_y = 0, 0.0
            end_page, end_y = None, None

        ranges[key] = (start_page, start_y, end_page, end_y, True)

    return ranges


# ===========================================================================
# Step 6 — Crop & extract
# ===========================================================================
def extract_range(doc: fitz.Document, start_page: int, start_y: float,
                   end_page: Optional[int], end_y: Optional[float]) -> bytes:
    last_page = end_page if end_page is not None else doc.page_count - 1
    last_page = max(start_page, min(last_page, doc.page_count - 1))

    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=start_page, to_page=last_page)

    first = new_doc[0]
    r = first.rect
    top = max(r.y0, start_y - CROP_GAP)

    if new_doc.page_count == 1:
        bottom = (end_y - CROP_GAP) if (end_page == start_page and end_y is not None) else r.y1
        try:
            first.set_cropbox(fitz.Rect(r.x0, top, r.x1, max(top + 1, bottom)))
        except Exception:
            logging.debug("Cropbox trim failed on single-page snippet; keeping full page(s).")
    else:
        try:
            first.set_cropbox(fitz.Rect(r.x0, top, r.x1, r.y1))
        except Exception:
            logging.debug("Top cropbox trim failed; keeping full first page.")
        if end_y is not None:
            last = new_doc[-1]
            r2 = last.rect
            bottom = max(r2.y0 + 1, end_y - CROP_GAP)
            try:
                last.set_cropbox(fitz.Rect(r2.x0, r2.y0, r2.x1, bottom))
            except Exception:
                logging.debug("Bottom cropbox trim failed; keeping full last page.")

    data = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    return data


# ===========================================================================
# Step 7 — Per-strategy processing
# ===========================================================================
def _process_mcq_mark_scheme(doc: fitz.Document, parsed: ParsedFilename, db_rows: list[dict],
                              output_root: Path, dry_run: bool, stats: RunStats) -> None:
    """MCQ mark schemes are compact answer grids — a single cell ("C")
    can't be sliced into a meaningful snippet, so every question in this
    paper gets the whole document."""
    data = doc.tobytes(garbage=4, deflate=True)
    for row in db_rows:
        _save_snippet(data, parsed, row["question_number"], output_root, dry_run)
        stats.questions_saved += 1
        stats.mcq_ms_whole_doc_assigned += 1

    logging.info(
        "%s: MCQ mark scheme (grid layout) — assigned the full %d-page document to all %d questions.",
        parsed.label(), doc.page_count, len(db_rows),
    )


def _process_question_paper(doc: fitz.Document, parsed: ParsedFilename, db_rows: list[dict],
                             output_root: Path, margin_fraction: float, dry_run: bool,
                             stats: RunStats, mcq: bool) -> None:
    top_level_numbers = sorted({row["sort_key"][0] for row in db_rows})
    anchors, tier_used, _unresolved_after_all_tiers = find_anchors_multitier(
        doc, top_level_numbers, margin_fraction, mode="top_level"
    )
    ranges = compute_ranges_with_fallback(anchors, top_level_numbers)

    cache: dict[int, bytes] = {}
    fallback_count = 0
    for row in db_rows:
        main_num = row["sort_key"][0]
        start_page, start_y, end_page, end_y, is_fallback = ranges[main_num]
        if is_fallback:
            fallback_count += 1
            stats.unresolved_details.append((parsed.label(), row["question_number"], "fallback"))
        if main_num not in cache:
            cache[main_num] = extract_range(doc, start_page, start_y, end_page, end_y)
        _save_snippet(cache[main_num], parsed, row["question_number"], output_root, dry_run)
        stats.questions_saved += 1

    stats.fallback_used += fallback_count
    for tier in tier_used.values():
        stats.tier_hits[tier] += 1

    tc = Counter(tier_used.values())
    logging.info(
        "%s (%s QP): %d/%d top-level questions anchored precisely "
        "[block:%d line:%d span:%d] — %d used page-range fallback.",
        parsed.label(), "MCQ" if mcq else "Theory",
        len(anchors), len(top_level_numbers),
        tc.get("block", 0), tc.get("line", 0), tc.get("span", 0),
        fallback_count,
    )


def _process_theory_mark_scheme(doc: fitz.Document, parsed: ParsedFilename, db_rows: list[dict],
                                 output_root: Path, margin_fraction: float, dry_run: bool,
                                 stats: RunStats) -> None:
    labels = [row["question_number"] for row in db_rows]
    anchors, tier_used, _unresolved_after_all_tiers = find_anchors_multitier(
        doc, labels, margin_fraction, mode="full_label"
    )
    ranges = compute_ranges_with_fallback(anchors, labels)

    fallback_count = 0
    for row in db_rows:
        label = row["question_number"]
        start_page, start_y, end_page, end_y, is_fallback = ranges[label]
        if is_fallback:
            fallback_count += 1
            stats.unresolved_details.append((parsed.label(), label, "fallback"))
        data = extract_range(doc, start_page, start_y, end_page, end_y)
        _save_snippet(data, parsed, label, output_root, dry_run)
        stats.questions_saved += 1

    stats.fallback_used += fallback_count
    for tier in tier_used.values():
        stats.tier_hits[tier] += 1

    tc = Counter(tier_used.values())
    logging.info(
        "%s (Theory MS): %d/%d sub-part labels anchored precisely "
        "[block:%d line:%d span:%d] — %d used page-range fallback.",
        parsed.label(), len(anchors), len(labels),
        tc.get("block", 0), tc.get("line", 0), tc.get("span", 0),
        fallback_count,
    )


def _save_snippet(pdf_bytes: bytes, parsed: ParsedFilename, question_number: str,
                   output_root: Path, dry_run: bool) -> None:
    dest_dir = (
        output_root / parsed.paper_type / parsed.subject_code / str(parsed.year)
        / parsed.folder_session / parsed.variant_code
    )
    dest_path = dest_dir / f"{question_number}.pdf"

    if dry_run:
        logging.info("[dry-run] Would write: %s", dest_path)
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(pdf_bytes)


# ===========================================================================
# Step 8 — Orchestration for a single file
# ===========================================================================
def process_file(filepath: Path, conn: sqlite3.Connection, output_root: Path,
                  margin_fraction: float, dry_run: bool, stats: RunStats) -> None:
    parsed = parse_filename(filepath.name)
    if parsed is None:
        stats.files_skipped_unparsed += 1
        logging.warning("Filename doesn't match CAIE pattern, skipping: %s", filepath.name)
        return
    stats.files_parsed += 1

    db_rows = get_paper_rows(conn, parsed)
    if not db_rows:
        stats.files_skipped_no_db_rows += 1
        logging.info("No DB rows found for %s (%s) — nothing to extract, skipping.",
                      filepath.name, parsed.label())
        return

    try:
        doc = fitz.open(filepath)
    except Exception as e:
        stats.files_corrupted += 1
        logging.error("Could not open PDF (corrupted or unreadable): %s — %s", filepath.name, e)
        return

    try:
        mcq = is_mcq_paper(parsed, db_rows)

        if parsed.paper_type == "ms" and mcq:
            stats.mcq_ms_files += 1
            _process_mcq_mark_scheme(doc, parsed, db_rows, output_root, dry_run, stats)
        elif parsed.paper_type == "qp":
            stats.mcq_qp_files += 1 if mcq else 0
            stats.theory_qp_files += 0 if mcq else 1
            _process_question_paper(doc, parsed, db_rows, output_root, margin_fraction, dry_run, stats, mcq)
        else:  # theory (non-grid) mark scheme
            stats.theory_ms_files += 1
            _process_theory_mark_scheme(doc, parsed, db_rows, output_root, margin_fraction, dry_run, stats)
    finally:
        doc.close()


# ===========================================================================
# Main
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Root directory of raw, full-length past papers.")
    parser.add_argument("--db", default="past_papers.db", help="Path to past_papers.db")
    parser.add_argument("--output", default="output_questions", help="Root output directory.")
    parser.add_argument("--margin-fraction", type=float, default=DEFAULT_MARGIN_FRACTION,
                         help="Fraction of page width treated as the left margin for block/line-tier anchors.")
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen without writing any files.")
    parser.add_argument("--log-file", default="split_papers.log", help="Where to write the detailed log.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(args.log_file, mode="w"), logging.StreamHandler(sys.stdout)],
    )

    input_root = Path(args.input)
    output_root = Path(args.output)
    if not input_root.exists():
        logging.error("Input directory does not exist: %s", input_root)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    stats = RunStats()

    pdf_files = []
    for dirpath, _dirnames, filenames in os.walk(input_root):
        for fname in filenames:
            if fname.lower().endswith(".pdf"):
                pdf_files.append(Path(dirpath) / fname)
    stats.files_seen = len(pdf_files)
    logging.info("Found %d PDF files under %s", len(pdf_files), input_root)

    for filepath in tqdm(pdf_files, desc="Splitting papers", unit="file"):
        try:
            process_file(filepath, conn, output_root, args.margin_fraction, args.dry_run, stats)
        except Exception as e:  # never let one bad file kill the whole run
            logging.error("Unexpected error on %s — skipping. (%s)", filepath, e)

    conn.close()

    logging.info("=" * 70)
    logging.info("RUN SUMMARY")
    logging.info("  Files seen:                    %d", stats.files_seen)
    logging.info("  Files parsed (filename):       %d", stats.files_parsed)
    logging.info("  Skipped — bad filename:        %d", stats.files_skipped_unparsed)
    logging.info("  Skipped — no DB match:         %d", stats.files_skipped_no_db_rows)
    logging.info("  Skipped — corrupted PDF:       %d", stats.files_corrupted)
    logging.info("  ---")
    logging.info("  MCQ question papers:           %d", stats.mcq_qp_files)
    logging.info("  Theory question papers:        %d", stats.theory_qp_files)
    logging.info("  MCQ mark schemes (grid):       %d", stats.mcq_ms_files)
    logging.info("  Theory mark schemes:           %d", stats.theory_ms_files)
    logging.info("  ---")
    logging.info("  Question snippets saved:       %d", stats.questions_saved)
    logging.info("  Anchored via block tier:       %d", stats.tier_hits.get("block", 0))
    logging.info("  Anchored via line tier:        %d", stats.tier_hits.get("line", 0))
    logging.info("  Anchored via span tier:        %d", stats.tier_hits.get("span", 0))
    logging.info("  Used page-range fallback:      %d", stats.fallback_used)
    logging.info("  MCQ MS whole-doc assignments:  %d", stats.mcq_ms_whole_doc_assigned)
    logging.info("  Hard failures (should be 0):   %d", stats.questions_unresolved)

    if stats.unresolved_details:
        logging.info("  ---")
        logging.info("  Questions that needed the page-range fallback (first 30):")
        for label, qn, reason in stats.unresolved_details[:30]:
            logging.info("    - %s -> %s (%s)", label, qn, reason)
        if len(stats.unresolved_details) > 30:
            logging.info("    ... and %d more — full list in %s", len(stats.unresolved_details) - 30, args.log_file)
    logging.info("=" * 70)


if __name__ == "__main__":
    main()
