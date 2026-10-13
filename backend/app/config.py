"""Settings come from the environment so the same image runs in compose,
Kubernetes and CI without being rebuilt."""
import os


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://shelfwise:shelfwise@localhost:5432/shelfwise"
    )
    library_name: str = os.getenv("LIBRARY_NAME", "ShelfWise Central Library")
    default_loan_days: int = int(os.getenv("DEFAULT_LOAN_DAYS", "14"))
    app_version: str = os.getenv("APP_VERSION", "dev")


settings = Settings()
