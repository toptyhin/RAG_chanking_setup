"""GigaChat CA bundle resolution."""

from __future__ import annotations

from pathlib import Path

from rageval_llm_providers.ca import httpx_verify_arg, resolve_gigachat_ca_bundle


def test_resolve_prefers_russian_trusted_pem(tmp_path: Path, monkeypatch) -> None:
    certs = tmp_path / "certs"
    certs.mkdir()
    (certs / "other.crt").write_text(
        "-----BEGIN CERTIFICATE-----\nOTHER\n-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )
    preferred = certs / "russian_trusted_root_ca_pem.crt"
    preferred.write_text(
        "-----BEGIN CERTIFICATE-----\nROOT\n-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GIGACHAT_CA_BUNDLE", raising=False)
    assert resolve_gigachat_ca_bundle() == preferred


def test_resolve_skips_der_and_broken_env_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    """DER / non-PEM must not be returned — causes NO_CERTIFICATE_OR_CRL_FOUND."""
    certs = tmp_path / "certs"
    certs.mkdir()
    der = certs / "russian_trusted_root_ca_gost_2025_pem.crt"
    # Minimal non-PEM payload (looks like DER to our PEM detector).
    der.write_bytes(b"\x30\x82\x04\x80\x30\x82\x03\x68\x02\x01\x02")
    good = certs / "russian_trusted_root_ca_pem.crt"
    good.write_text(
        "-----BEGIN CERTIFICATE-----\nROOT\n-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )

    broken_bundle = tmp_path / "ca-bundle.pem"
    # Prepend DER then PEM — OpenSSL cannot load this as cafile.
    broken_bundle.write_bytes(der.read_bytes() + good.read_bytes())

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIGACHAT_CA_BUNDLE", str(broken_bundle))
    assert resolve_gigachat_ca_bundle() == good


def test_httpx_verify_false_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("GIGACHAT_CA_BUNDLE", raising=False)
    assert httpx_verify_arg(verify_ssl=False) is False


def test_httpx_verify_uses_env_file(tmp_path: Path, monkeypatch) -> None:
    bundle = tmp_path / "ca.pem"
    bundle.write_text(
        "-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIGACHAT_CA_BUNDLE", str(bundle))
    assert httpx_verify_arg(verify_ssl=True) == str(bundle)
