from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./nail_salon.db"
    salon_name: str = "Beauty Nails Studio"
    salon_address: str = "г. Москва, ул. Примерная, 10"
    salon_phone: str = "+7 (999) 000-00-00"
    salon_instagram: str = "https://instagram.com/example"
    salon_site: str = "https://example.com"
    salon_map_url: str = "https://maps.google.com"
    salon_working_hours: str = "Ежедневно 10:00–21:00"
    reminders_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
