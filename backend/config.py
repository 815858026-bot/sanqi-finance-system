import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "三七设计财务系统")
    app_version: str = os.getenv("APP_VERSION", "4.1.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sanqi_finance.db")
    secret_key: str = os.getenv("SECRET_KEY", "sanqi-finance-dev-secret-key")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    wechat_appid: str = os.getenv("WECHAT_APPID", "")
    wechat_callback_url: str = os.getenv("WECHAT_CALLBACK_URL", "")


settings = Settings()
