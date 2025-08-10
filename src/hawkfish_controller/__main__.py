import argparse

import uvicorn

from .config import settings
from .main_app import create_app


def main() -> None:
    parser = argparse.ArgumentParser("hawkfish-controller")
    parser.add_argument("--host", default=settings.api_host)
    parser.add_argument("--port", type=int, default=settings.api_port)
    args = parser.parse_args()

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()


