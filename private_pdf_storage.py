"""Private GitHub Releases backend for Pastify. Token never reaches the browser."""
from __future__ import annotations

import io
import json
from pathlib import PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import zipfile

import streamlit as st


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass
    import os
    return os.environ.get(name, default)


def _github_json(url: str, token: str) -> dict:
    req = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Pastify/1.0",
    })
    with urlopen(req, timeout=30) as response:
        return json.load(response)


@st.cache_data(ttl=3600, max_entries=2, show_spinner=False)
def _archive_bytes(repo: str, tag: str, archive_name: str) -> bytes:
    token = _setting("GITHUB_PDF_READ_TOKEN")
    if not token:
        raise RuntimeError("Private PDF storage token is not configured.")
    release = _github_json(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}", token
    )
    matches = [a for a in release.get("assets", []) if a.get("name") == archive_name]
    if len(matches) != 1:
        raise FileNotFoundError("PDF archive is missing from private storage.")
    asset_id = matches[0]["id"]
    req = Request(
        f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Pastify/1.0",
        },
    )
    # Never forward the GitHub token to the signed asset-download host.
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=60) as response:
            data = response.read()
            if response.headers.get("Content-Type", "").startswith("application/json"):
                raise RuntimeError("GitHub returned asset metadata rather than ZIP bytes.")
    except HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise RuntimeError(f"Private PDF asset request failed (HTTP {exc.code}).") from None
        location = exc.headers.get("Location", "")
        parsed = urlparse(location)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            host == "githubusercontent.com" or host.endswith(".githubusercontent.com")
        ):
            raise RuntimeError("Unexpected private asset redirect host.")
        with urlopen(Request(location, headers={"User-Agent": "Pastify/1.0"}), timeout=90) as response:
            data = response.read()
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise RuntimeError("Private storage did not return a valid ZIP archive.")
    return data


def get_private_pdf_bytes(relative_path: str | None) -> bytes | None:
    if not isinstance(relative_path, str) or not relative_path:
        return None
    path = PurePosixPath(relative_path)
    parts = path.parts
    if path.is_absolute() or ".." in parts or len(parts) < 5:
        return None
    if parts[0] not in ("qp", "ms") or not parts[1].isdigit() or not parts[2].isdigit():
        return None
    repo = _setting("GITHUB_PRIVATE_PDF_REPO", "Veloce5/pastify-pdf-storage")
    tag = _setting("GITHUB_PRIVATE_PDF_RELEASE_TAG", "pdf-storage-v1.2.0")
    if repo != "Veloce5/pastify-pdf-storage":
        raise RuntimeError("Unexpected private PDF repository configuration.")
    name = f"{parts[1]}_{parts[2]}.zip"
    data = _archive_bytes(repo, tag, name)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        try:
            return archive.read(path.as_posix())
        except KeyError:
            return None
