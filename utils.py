"""PDF rendering, worksheet exports, and shared Pastify helpers."""

from __future__ import annotations

import zipfile
from io import BytesIO

import pymupdf as fitz
import streamlit as st
from PyPDF2 import PdfMerger

from config import PDF_RENDER_ZOOM
from database import get_sorted_topics as _get_sorted_topics_db, get_distinct_values
from pdf_storage import get_pdf_bytes


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=256)
def _render_pdf_pages(relative_path: str, zoom: float = PDF_RENDER_ZOOM) -> list[bytes]:
    """Render a local or remote PDF to PNG bytes, cached by relative path."""
    pdf_bytes = get_pdf_bytes(relative_path)
    if not pdf_bytes:
        return []

    images: list[bytes] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    return images


def get_pdf_page_images(relative_path: str | None) -> list[bytes]:
    """Return PNG images for a database-relative PDF path."""
    if not relative_path:
        return []
    try:
        return _render_pdf_pages(relative_path)
    except Exception as exc:
        st.warning(f"Could not display PDF {relative_path}: {exc}")
        return []


def render_pdf(relative_path: str | None, empty_message: str = "This file couldn't be found.") -> None:
    """Render PDF pages in Streamlit."""
    images = get_pdf_page_images(relative_path)
    if not images:
        st.info(f"📄 {empty_message}")
        return

    if len(images) <= 4:
        cols = st.columns(len(images))
        for i, image_bytes in enumerate(images):
            with cols[i]:
                st.image(image_bytes, caption=f"Page {i + 1}", width="stretch")
    else:
        for i, image_bytes in enumerate(images):
            st.image(image_bytes, caption=f"Page {i + 1}", width="stretch")


# ---------------------------------------------------------------------------
# Worksheet Builder
# ---------------------------------------------------------------------------
def merge_pdfs(question_paths, answer_paths, progress_bar=None) -> tuple[bytes | None, bytes | None]:
    """Merge PDFs from local or remote storage into question and answer booklets."""
    q_merger, a_merger = PdfMerger(), PdfMerger()
    missing: list[str] = []
    total = max(len(question_paths), 1)

    try:
        for i, (question_path, answer_path) in enumerate(zip(question_paths, answer_paths)):
            for path, merger in ((question_path, q_merger), (answer_path, a_merger)):
                if not path:
                    continue
                try:
                    pdf_bytes = get_pdf_bytes(path)
                    if pdf_bytes:
                        merger.append(BytesIO(pdf_bytes))
                    else:
                        missing.append(str(path))
                except Exception as exc:
                    st.error(f"Could not load {path!r}: {type(exc).__name__}: {exc}")
                    missing.append(str(path))

            if progress_bar:
                progress_bar.progress(int((i + 1) / total * 100))

        if missing:
            st.warning(f"⚠️ {len(missing)} PDF(s) could not be loaded.")
            # Show examples so we can diagnose missing paths without guessing.
            st.caption("Missing paths (first 5): " + ", ".join(repr(p) for p in missing[:5]))

        def finish_merge(merger: PdfMerger) -> bytes | None:
            if not merger.pages:
                return None
            buffer = BytesIO()
            merger.write(buffer)
            return buffer.getvalue()

        return finish_merge(q_merger), finish_merge(a_merger)
    finally:
        q_merger.close()
        a_merger.close()


def create_zip(files: dict[str, bytes]) -> BytesIO:
    """Build a ZIP archive from a mapping of filename to bytes."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            if data:
                archive.writestr(name, data)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Topic sorting and snippet helpers
# ---------------------------------------------------------------------------
def get_sorted_topics(subject: str) -> tuple[list, list]:
    return _get_sorted_topics_db(subject)


def get_sorted_subtopics(subject: str, topics: list[str]) -> tuple[list, list]:
    subtopics = get_distinct_values("Sub_topic", {"Subject_name": subject, "Topic": topics})
    return sorted(subtopics), []


def get_mapping(variant: str) -> str:
    mapping = {"May/June": "M/J", "Feb/March": "F/M", "Oct/Nov": "O/N"}
    for key, value in mapping.items():
        if key in (variant or ""):
            return value
    return "Unknown"


def generate_snippet(subject_code, paper_variant, mapping, year) -> str:
    return f"{subject_code}/{paper_variant}/{mapping}/{year}"


def add_divider(n: int = 1) -> None:
    st.markdown("<hr>" * n, unsafe_allow_html=True)
