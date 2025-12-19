from pydantic import BaseModel


class Settings(BaseModel):
    buda_base_url: str = "https://www.buda.com"
    buda_timeout_seconds: float = 10.0


settings = Settings()
