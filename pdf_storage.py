
"""
PDF storage abstraction for Pastify.

Modes:
    local      - Read PDFs from output_questions/
    remote     - Download individual PDFs from a CDN
    github_zip - Download subject-year ZIPs from GitHub Releases

Database PDF paths remain unchanged.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

import streamlit as st

from config import resolve_media_path


def _get_setting(name: str, default: str = "") -> str:
    """Read Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _validate_relative_path(relative_path: str | None) -> str | None:
    """Validate a database-stored relative PDF path."""
    if not relative_path or not isinstance(relative_path, str):
        return None

    path = PurePosixPath(relative_path)

    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in relative_path
    ):
        return None

    return path.as_posix()


def _download_bytes(url: str, timeout: int = 60) -> bytes:
    """Download data securely over HTTPS."""
    request = Request(
        url,
        headers={"User-Agent": "Pastify/1.0"},
    )

    with urlopen(request, timeout=timeout) as response:
        return response.read()


@st.cache_data(show_spinner=False, max_entries=256)
def _download_remote_pdf(relative_path: str, base_url: str) -> bytes:
    """Download and cache an individual PDF."""
    url = f"{base_url.rstrip('/')}/{quote(relative_path, safe='/')}"
    return _download_bytes(url, timeout=30)


@st.cache_data(show_spinner=False, max_entries=256)
def _read_local_pdf(relative_path: str) -> bytes:
    """Read a PDF from output_questions/."""
    resolved = resolve_media_path(relative_path)

    if resolved is None or not resolved.is_file():
        raise FileNotFoundError(relative_path)

    return resolved.read_bytes()


def _get_archive_name(relative_path: str) -> str:
    """
    Convert:
        qp/9618/2024/May_June/12/1(a).pdf
    into:
        9618_2024.zip
    """
    parts = PurePosixPath(relative_path).parts

    if len(parts) < 4 or parts[0] not in ("qp", "ms"):
        raise ValueError(f"Invalid PDF archive path: {relative_path}")

    subject = parts[1]
    year = parts[2]

    if not subject.isdigit() or not year.isdigit():
        raise ValueError(f"Invalid subject/year: {relative_path}")

    return f"{subject}_{year}.zip"


@st.cache_data(
    show_spinner=False,
    max_entries=2,
    ttl=3600,
)
def _download_github_archive(
    archive_name: str,
    release_base_url: str,
) -> bytes:
    """Download and cache a subject-year ZIP archive."""
    url = (
        f"{release_base_url.rstrip('/')}/"
        f"{quote(archive_name)}"
    )

    return _download_bytes(url, timeout=120)


def _read_github_zip_pdf(
    relative_path: str,
    release_base_url: str,
) -> bytes | None:
    """Extract a PDF from its subject-year GitHub Release ZIP."""
    archive_name = _get_archive_name(relative_path)

    archive_bytes = _download_github_archive(
        archive_name,
        release_base_url,
    )

    try:
        with ZipFile(BytesIO(archive_bytes)) as archive:
            try:
                return archive.read(relative_path)
            except KeyError:
                return None
    except BadZipFile as exc:
        raise RuntimeError(
            f"Invalid ZIP archive: {archive_name}"
        ) from exc


def get_pdf_bytes(relative_path: str | None) -> bytes | None:
    """
    Return PDF bytes using the configured storage mode.

    Supported modes:
        local
        remote
        github_zip
    """
    relative_path = _validate_relative_path(relative_path)

    if relative_path is None:
        return None

    mode = _get_setting("PDF_STORAGE_MODE", "local").lower()

    if mode == "local":
        try:
            return _read_local_pdf(relative_path)
        except FileNotFoundError:
            return None

    if mode == "remote":
        base_url = _get_setting("PDF_BASE_URL")

        if not base_url:
            raise RuntimeError(
                "PDF_BASE_URL is not configured."
            )

        try:
            return _download_remote_pdf(relative_path, base_url)
        except Exception as exc:
            raise RuntimeError(
                f"Could not download PDF: {relative_path}"
            ) from exc

    if mode == "github_zip":
        release_base_url = _get_setting(
            "GITHUB_RELEASE_BASE_URL",
            "https://github.com/Veloce5/pastify/releases/"
            "download/pdf-storage-test-v1",
        )

        try:
            return _read_github_zip_pdf(
                relative_path,
                release_base_url,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not load PDF from GitHub ZIP: {relative_path}"
            ) from exc

    raise ValueError(
        f"Invalid PDF_STORAGE_MODE: {mode!r}. "
        "Use 'local', 'remote', or 'github_zip'."
    )
