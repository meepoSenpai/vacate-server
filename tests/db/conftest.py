import pytest_asyncio
import os

from sqlmodel import SQLModel
from api.db.user import User


@pytest_asyncio.fixture(autouse=True)
async def drop_and_recreate_db():
    from sqlalchemy.ext.asyncio import create_async_engine

    from api.db.user import User
    from api.db.database import Database

    try:
        await Database.connect_database()
    except Exception:
        Database.engine = create_async_engine(
            f"sqlite+aiosqlite:///{os.getenv('DB_NAME')}"
        )
    if Database.engine is not None:
        async with Database.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
    await User.create(
        username="admin",
        mail="admin@localhost",
        password="supersecurepassword",
        is_admin=True,
    )
    yield


@pytest_asyncio.fixture()
async def sample_user():
    user = await User.create(username="User", password="passwort", mail="user@mail.com")
    yield user
