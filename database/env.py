from alembic import context
from gaia.config import engine, settings
from gaia.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        try:
            if is_sqlite:
                # Batch DDL rebuilds parent tables. Keep child history intact.
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
                if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 0:
                    raise RuntimeError("Cannot disable SQLite FK enforcement for migration")
                connection.commit()
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
                if is_sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("Foreign key violations after migration; rolling back")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if is_sqlite:
                connection.rollback()
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()
                if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                    raise RuntimeError("Failed to restore SQLite FK enforcement")
