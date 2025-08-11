import argparse

import uvicorn

from .config import settings
from .main_app import create_app


def main() -> None:
    parser = argparse.ArgumentParser("hawkfish-controller")
    parser.add_argument("--host", default=settings.api_host)
    parser.add_argument("--port", type=int, default=settings.api_port)
    args = parser.parse_args()

    app = create_app()
    if settings.dev_tls in ("self-signed", "custom"):
        from .services.tls import ensure_self_signed
        import os
        cert = settings.tls_cert_path or os.path.join(settings.state_dir, "tls", "cert.pem")
        key = settings.tls_key_path or os.path.join(settings.state_dir, "tls", "key.pem")
        if settings.dev_tls == "self-signed":
            from pathlib import Path
            ensure_self_signed(Path(cert), Path(key))
        uvicorn.run(app, host=args.host, port=args.port, log_level="info", ssl_certfile=cert, ssl_keyfile=key)
    else:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()


