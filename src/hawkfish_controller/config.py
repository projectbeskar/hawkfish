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
    tls_cert_path: str | None = Field(default=None, alias="HF_TLS_CERT")
    tls_key_path: str | None = Field(default=None, alias="HF_TLS_KEY")
    
    # UI
    ui_enabled: bool = Field(default=False, alias="HF_UI_ENABLED")
    
        # Libvirt Connection Pool
    libvirt_pool_min: int = Field(default=1, alias="HF_LIBVIRT_POOL_MIN")
    libvirt_pool_max: int = Field(default=10, alias="HF_LIBVIRT_POOL_MAX")
    libvirt_pool_ttl_sec: int = Field(default=300, alias="HF_LIBVIRT_POOL_TTL_SEC")

    # Console Access
    console_enabled: bool = Field(default=True, alias="HF_CONSOLE_ENABLED")
    console_token_ttl: int = Field(default=300, alias="HF_CONSOLE_TOKEN_TTL")  # 5 minutes
    console_idle_timeout: int = Field(default=600, alias="HF_CONSOLE_IDLE_TIMEOUT")  # 10 minutes

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


