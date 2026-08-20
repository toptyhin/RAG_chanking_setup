"""Resolve CA bundle path for GigaChat SSL verification."""

from __future__ import annotations

import os
from pathlib import Path


def _is_pem_certificate_file(path: Path) -> bool:
    """True if file is a PEM CERTIFICATE (or PEM bundle), not DER/mixed.

    OpenSSL/httpx need PEM. DER dumps and DER-prepended bundles raise
    ``[X509: NO_CERTIFICATE_OR_CRL_FOUND]`` when used as ``cafile``.
    """
    try:
        if not path.is_file() or path.stat().st_size <= 0:
            return False
        sample = path.read_bytes()[:8192]
    except OSError:
        return False
    stripped = sample.lstrip()
    return stripped.startswith(b"-----BEGIN CERTIFICATE-----")


def _cert_files_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files: list[Path] = []
    for pattern in ("*.crt", "*.pem", "*.cer"):
        files.extend(
            p
            for p in directory.glob(pattern)
            if _is_pem_certificate_file(p)
        )
    # Stable order; prefer the classic Russian Trusted Root PEM name.
    files = sorted(set(files), key=lambda p: p.name.lower())
    preferred = [p for p in files if "russian_trusted_root_ca_pem" in p.name.lower()]
    rest = [p for p in files if p not in preferred]
    return preferred + rest


def resolve_gigachat_ca_bundle() -> Path | None:
    """Return a CA file usable by httpx, or None to use the system store."""
    env = os.environ.get("GIGACHAT_CA_BUNDLE", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(
        [
            Path("/etc/ssl/certs/rageval/ca-bundle.pem"),
            Path("/certs"),
            Path.cwd() / "certs",
        ]
    )
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)

        if _is_pem_certificate_file(path):
            return path
        files = _cert_files_in(path)
        if not files:
            continue
        # Multiple PEMs: httpx accepts one file — use preferred / first.
        return files[0]
    return None


def httpx_verify_arg(*, verify_ssl: bool) -> bool | str:
    """Value for ``httpx.Client(verify=...)``."""
    if not verify_ssl:
        return False
    bundle = resolve_gigachat_ca_bundle()
    if bundle is not None:
        return str(bundle)
    return True
