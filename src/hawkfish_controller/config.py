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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()


