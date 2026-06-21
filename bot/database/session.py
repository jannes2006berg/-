from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from bot.config.settings import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
