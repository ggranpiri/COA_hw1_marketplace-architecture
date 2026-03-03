from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    ACCESS_TOKEN_MINUTES: int = 20
    REFRESH_TOKEN_DAYS: int = 14
    ORDER_RATE_LIMIT_MINUTES: int = 2

    class Config:
        extra = "ignore"


settings = Settings()