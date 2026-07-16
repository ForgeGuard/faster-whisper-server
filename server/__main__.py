"""Process entrypoint: ``python -m server``.

Runs the FastAPI app under uvicorn. Its one job over the plain
``uvicorn server.main:app`` CLI is TLS: when ``TLS_ENABLED`` is set it generates
(or reuses) a self-signed certificate and wires ``ssl_certfile``/``ssl_keyfile``
into ``uvicorn.run`` so the server speaks HTTPS directly — no reverse proxy, no
extra container. With TLS off it is a thin, behaviour-identical wrapper around
the same app, so HTTP deployments (Helm, the existing compose) are unchanged.
"""

from __future__ import annotations

import logging
import sys

import uvicorn

from server import config

LOGGER = logging.getLogger("faster_whisper_api")


def _tls_kwargs() -> dict[str, str]:
    """uvicorn SSL kwargs when TLS is enabled, generating a self-signed cert.

    Returns an empty dict (plain HTTP) unless ``TLS_ENABLED`` is set.
    """
    if not config.TLS_ENABLED:
        return {}

    from pathlib import Path

    cert = Path(config.TLS_CERT_FILE)
    key = Path(config.TLS_KEY_FILE)
    if not (cert.exists() and key.exists()):
        if not config.TLS_SELF_SIGNED:
            print(
                f"TLS_ENABLED=true but cert/key not found ({cert}, {key}) and "
                "TLS_SELF_SIGNED=false — provide TLS_CERT_FILE / TLS_KEY_FILE or "
                "enable self-signed generation.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        from server.tls import ensure_cert

        ensure_cert(cert, key, common_name=config.TLS_CN, extra_sans=config.TLS_SAN)
    return {"ssl_certfile": str(cert), "ssl_keyfile": str(key)}


def main() -> None:
    ssl_kwargs = _tls_kwargs()
    scheme = "https" if ssl_kwargs else "http"
    LOGGER.info("Starting uvicorn on %s://%s:%s", scheme, config.HOST, config.PORT)
    uvicorn.run(
        "server.main:app",
        host=config.HOST,
        port=config.PORT,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
