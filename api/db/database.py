import os

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from logging import getLogger

logger = getLogger(__name__)


class Database:
    engine: AsyncEngine | None = None
    _name = os.getenv("DB_NAME", "")

    _admin_name = os.getenv("ADMIN_USERNAME", "admin")
    _admin_password = os.getenv("ADMIN_PASSWORD", "password")
    _admin_mail = os.getenv("ADMIN_MAIL", "info@mail.com")

    @classmethod
    async def connect_database(cls, create_tables: bool = True):
        from .user import User
        from .vacation import Vacation  # noqa: F401

        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls._name}")

        if create_tables and cls.engine is not None:
            async with cls.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(f"SQLite database connected: {cls._name}")
        try:
            async with AsyncSession(cls.engine) as session:
                (await session.exec(select(User).where(User.id == 1))).one()
                logger.info("Admin user already exists")
        except NoResultFound:
            await User.create(
                cls._admin_name, cls._admin_mail, cls._admin_password, True
            )
            logger.info("Admin user created")

    @classmethod
    def session(cls, expire_on_commit=False) -> AsyncSession:
        return AsyncSession(cls.engine, expire_on_commit=expire_on_commit)
