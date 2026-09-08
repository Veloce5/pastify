"""
utils.py  (replaces Utils.py)

Key change: PyMuPDF page rendering is now wrapped in st.cache_data, keyed on
(file path, mtime). Previously every rerun (which in Streamlit happens on
almost every widget click) re-opened and re-rasterized the PDF from scratch
— by far the most expensive operation in the app. Now it only happens once
per unique file.
"""

from __future__ import annotations

import zipfile
from io import BytesIO

import fitz  # PyMuPDF
import streamlit as st
from PyPDF2 import PdfMerger

from config import PDF_RENDER_ZOOM, resolve_media_path
from database import get_sorted_topics as _get_sorted_topics_db, get_distinct_values


# ---------------------------------------------------------------------------
# PDF rendering (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=256)
def _render_pdf_pages(resolved_path: str, _mtime: float, zoom: float = PDF_RENDER_ZOOM) -> list[bytes]:
    """Rasterize every page of a PDF to PNG bytes. `resolved_path` is always
    an already-resolved absolute path by the time it gets here; `_mtime` is
    part of the cache key so an edited file on disk correctly busts the
    cache. `alpha=False` skips the alpha channel PyMuPDF would otherwise
    allocate per pixmap — exam PDFs have no transparency to preserve, and
    this alone cuts peak memory per page by roughly a quarter."""
    images: list[bytes] = []
    doc = fitz.open(resolved_path)
    try:
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
            pix = None  # drop the reference eagerly; pages can be large
    finally:
        doc.close()
    return images


def get_pdf_page_images(relative_path: str | None) -> list[bytes]:
    """Public entry point. `relative_path` is the raw value pulled straight
    out of the Question/Answer DB columns (e.g.
    'qp/9618/2024/May_June/12/1(a).pdf') — resolution against OUTPUT_DIR and
    the existence check both happen here, in one place, using pathlib only."""
    resolved = resolve_media_path(relative_path)
    if resolved is None or not resolved.exists():
        return []
    return _render_pdf_pages(str(resolved), resolved.stat().st_mtime)


def render_pdf(relative_path: str | None, empty_message: str = "This file couldn't be found.") -> None:
    """Render a PDF's pages as images with a clean empty state on failure."""
    images = get_pdf_page_images(relative_path)
    if not images:
        st.info(f"📄 {empty_message}")
        return

    cols = st.columns(len(images)) if len(images) <= 4 else [st.container()]
    if len(images) <= 4:
        for i, img_bytes in enumerate(images):
            with cols[i]:
                st.image(img_bytes, caption=f"Page {i + 1}", use_container_width=True)
    else:
        for i, img_bytes in enumerate(images):
            st.image(img_bytes, caption=f"Page {i + 1}", use_container_width=True)


# ---------------------------------------------------------------------------
# Merge / zip (Worksheet Builder)
# ---------------------------------------------------------------------------
def merge_pdfs(question_paths, answer_paths, progress_bar=None) -> tuple[bytes | None, bytes | None]:
    """Merge lists of question/answer PDFs into two in-memory PDFs (bytes).
    `question_paths`/`answer_paths` are the raw relative DB values; each one
    is resolved against OUTPUT_DIR right before use, and skipped (not
    crashed on) if it doesn't actually exist on this machine."""
    q_merger, a_merger = PdfMerger(), PdfMerger()
    total = max(len(question_paths), 1)
    missing: list[str] = []

    for i, (q, a) in enumerate(zip(question_paths, answer_paths)):
        q_resolved = resolve_media_path(q)
        if q_resolved is not None and q_resolved.exists():
            q_merger.append(str(q_resolved))
        elif q:
            missing.append(q)

        a_resolved = resolve_media_path(a)
        if a_resolved is not None and a_resolved.exists():
            a_merger.append(str(a_resolved))
        elif a:
            missing.append(a)

        if progress_bar:
            progress_bar.progress(int((i + 1) / total * 100))

    if missing:
        st.warning(f"⚠️ {len(missing)} file(s) were missing on disk and were skipped from the merge.")

    q_bytes = a_bytes = None
    try:
        buf = BytesIO()
        q_merger.write(buf)
        q_merger.close()
        q_bytes = buf.getvalue()
    except Exception as e:
        st.error(f"Error merging question papers: {e}")

    try:
        buf = BytesIO()
        a_merger.write(buf)
        a_merger.close()
        a_bytes = buf.getvalue()
    except Exception as e:
        st.error(f"Error merging answer sheets: {e}")

    return q_bytes, a_bytes


def create_zip(files: dict[str, bytes]) -> BytesIO:
    """files: {"filename.pdf": bytes, ...}"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            if data:
                zf.writestr(name, data)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Topic sorting / snippet helpers
# ---------------------------------------------------------------------------
def get_sorted_topics(subject: str) -> tuple[list, list]:
    return _get_sorted_topics_db(subject)


def get_sorted_subtopics(subject: str, topics: list[str]) -> tuple[list, list]:
    subtopics = get_distinct_values("Sub_topic", {"Subject_name": subject, "Topic": topics})
    return sorted(subtopics), []


def get_mapping(variant: str) -> str:
    mapping = {"May/June": "M/J", "Feb/March": "F/M", "Oct/Nov": "O/N"}
    for key, val in mapping.items():
        if key in (variant or ""):
            return val
    return "Unknown"


def generate_snippet(subject_code, paper_variant, mapping, year) -> str:
    return f"{subject_code}/{paper_variant}/{mapping}/{year}"


def add_divider(n: int = 1) -> None:
    st.markdown("<hr>" * n, unsafe_allow_html=True)
