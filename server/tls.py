"""Self-signed TLS certificate generation.

Lets a deployment speak HTTPS with zero external moving parts: no reverse
proxy, no manual ``openssl`` step, no cert-manager. When TLS is enabled but no
certificate is supplied, ``ensure_cert`` mints a self-signed one on first run
and persists it (default: ``<DATA_DIR>/tls``) so every later start reuses it.

The generated cert is intended for local/self-hosted testing over HTTPS —
browsers will warn it is untrusted, which is expected for a self-signed cert.
Point ``TLS_CERT_FILE`` / ``TLS_KEY_FILE`` at a real cert for anything public.
"""

from __future__ import annotations

import datetime as _dt
import ipaddress
import logging
from pathlib import Path

logger = logging.getLogger("faster_whisper_api")

# 10 years: this is a self-signed dev/self-host cert, not a public one, so a
# long life avoids surprise expiry on a long-running box.
_VALIDITY_DAYS = 3650


def ensure_cert(
    cert_path: Path,
    key_path: Path,
    *,
    common_name: str = "localhost",
    extra_sans: list[str] | None = None,
) -> tuple[Path, Path]:
    """Return ``(cert_path, key_path)``, generating a self-signed pair if absent.

    A no-op when both files already exist, so restarts reuse the persisted cert.
    """
    if cert_path.exists() and key_path.exists():
        return cert_path, key_path

    cert_pem, key_pem = _generate_self_signed(common_name, extra_sans or [])
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    # Key first, locked down, before the cert so a reader never sees a cert
    # without its key.
    key_path.write_bytes(key_pem)
    key_path.chmod(0o600)
    cert_path.write_bytes(cert_pem)
    logger.info(
        "Generated self-signed TLS certificate for '%s' at %s", common_name, cert_path
    )
    return cert_path, key_path


def _generate_self_signed(common_name: str, extra_sans: list[str]) -> tuple[bytes, bytes]:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError(
            "TLS self-signed cert generation requires the 'cryptography' package. "
            "Install it, or provide TLS_CERT_FILE / TLS_KEY_FILE, or set "
            "TLS_ENABLED=false."
        ) from exc

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Subject Alternative Names: the CN plus localhost/loopback so the cert
    # validates whether reached by hostname, "localhost", or 127.0.0.1/::1.
    san_names: list[str] = [common_name, "localhost", *extra_sans]
    entries: list[x509.GeneralName] = []
    seen: set[str] = set()
    for name in san_names:
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            entries.append(x509.IPAddress(ipaddress.ip_address(name)))
        except ValueError:
            entries.append(x509.DNSName(name))
    for ip in ("127.0.0.1", "::1"):
        if ip not in seen:
            seen.add(ip)
            entries.append(x509.IPAddress(ipaddress.ip_address(ip)))

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=5))
        .not_valid_after(now + _dt.timedelta(days=_VALIDITY_DAYS))
        .add_extension(x509.SubjectAlternativeName(entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return cert_pem, key_pem
