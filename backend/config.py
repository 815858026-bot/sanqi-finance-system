import os


class Settings:
    app_name = "三七设计财务系统"
    app_version = os.getenv("APP_VERSION", "4.0.0")
    debug = os.getenv("DEBUG", "True").lower() == "true"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./sanqi_finance.db")
    secret_key = os.getenv("SECRET_KEY", "SANQI_DESIGN_SECRET_KEY_CHANGE_IN_PRODUCTION")
    algorithm = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440").split("#")[0].strip())
    wechat_appid = os.getenv("WECHAT_APPID", "")
    wechat_appsecret = os.getenv("WECHAT_APPSECRET", "")
    wechat_login_url = os.getenv("WECHAT_LOGIN_URL", "https://api.weixin.qq.com/sns/oauth2/access_token")
    wechat_userinfo_url = os.getenv("WECHAT_USERINFO_URL", "https://api.weixin.qq.com/sns/userinfo")
    wechat_callback_url = os.getenv("WECHAT_CALLBACK_URL", "http://localhost:8000/api/auth/wechat/callback")
    upload_dir = os.getenv("UPLOAD_DIR", "./static/uploads")


settings = Settings()
