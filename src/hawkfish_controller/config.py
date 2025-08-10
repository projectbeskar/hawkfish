from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Libvirt
    libvirt_uri: str = Field(default="qemu:///system", alias="LIBVIRT_URI")

    # API
    api_host: str = Field(default="0.0.0.0", alias="HF_API_HOST")  # noqa: S104
    api_port: int = Field(default=8443, alias="HF_API_PORT")

    # Docs
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"

    # State
    state_dir: str = Field(default="/var/lib/hawkfish", alias="HF_STATE_DIR")
    iso_dir: str = Field(default="/var/lib/hawkfish/isos", alias="HF_ISO_DIR")
    network_name: str = Field(default="default", alias="HF_NETWORK")
    api_bind: str = Field(default="0.0.0.0:8080", alias="HF_API_BIND")
    dev_tls: str = Field(default="off", alias="HF_DEV_TLS")
    auth_mode: str = Field(default="none", alias="HF_AUTH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()


def ensure_directories() -> None:
    import os
    from contextlib import suppress

    for path in {settings.state_dir, settings.iso_dir}:
        with suppress(Exception):
            os.makedirs(path, exist_ok=True)


