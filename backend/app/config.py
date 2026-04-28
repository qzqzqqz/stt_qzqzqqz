from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "STT Transcription API"
    DEBUG: bool = True

    # Database — 从 .env 文件读取，无默认值，启动时必须提供
    DATABASE_URL: str

    # Redis — 从 .env 文件读取，无默认值，启动时必须提供
    REDIS_URL: str

    # JWT — 密钥从 .env 文件读取，无默认值，启动时必须提供
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_AUDIO_EXTENSIONS: set = {"wav", "mp3", "flac", "m4a", "ogg"}

    # Celery — 从 .env 文件读取，无默认值，启动时必须提供
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # MLX-Audio
    STT_MODEL: str = "mlx-community/VibeVoice-ASR-bf16"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
