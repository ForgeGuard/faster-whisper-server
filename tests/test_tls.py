"""Self-signed TLS certificate generation: idempotency, perms, and SANs."""

import ssl
from pathlib import Path

from server.tls import ensure_cert


def test_ensure_cert_creates_files_with_key_perms(tmp_path):
    cert = tmp_path / "tls" / "cert.pem"
    key = tmp_path / "tls" / "key.pem"

    ensure_cert(cert, key, common_name="localhost")

    assert cert.exists() and key.exists()
    # Private key must be owner-only (0600).
    assert (key.stat().st_mode & 0o777) == 0o600
    # The cert is a parseable X.509 PEM.
    assert cert.read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")


def test_ensure_cert_is_idempotent(tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"

    ensure_cert(cert, key, common_name="localhost")
    first_cert = cert.read_bytes()
    first_key = key.read_bytes()

    # A second call is a no-op: same bytes, no regeneration.
    ensure_cert(cert, key, common_name="localhost")
    assert cert.read_bytes() == first_cert
    assert key.read_bytes() == first_key


def test_cert_has_expected_sans(tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    ensure_cert(cert, key, common_name="whisper.local", extra_sans=["192.168.1.50"])

    # ssl can decode the SAN list from the PEM.
    decoded = ssl._ssl._test_decode_cert(str(cert))
    sans = {value for _, value in decoded.get("subjectAltName", ())}
    assert "whisper.local" in sans
    assert "localhost" in sans
    assert "127.0.0.1" in sans
    assert "192.168.1.50" in sans


def test_cert_and_key_load_into_ssl_context(tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    ensure_cert(cert, key, common_name="localhost")

    # The pair must be usable by uvicorn's SSL layer.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(cert), keyfile=str(key))
    assert Path(cert).exists()
