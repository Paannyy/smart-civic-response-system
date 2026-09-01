from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.db.database import Base, Settings, engine
from app.models.user import User
from app.models.complaint import Complaint
from app.models.complaint_history import ComplaintStatusHistory
from app.models.notification import Notification
from app.models.attachment import Attachment


# Alembic Config object
config = context.config


# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Load application settings from .env
settings = Settings()


# Metadata from SQLAlchemy models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()