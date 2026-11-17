import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from auth_service.infrastructure.database import create_database
from auth_service.infrastructure.db_models import Base


def test_auth_schema_can_be_created_with_async_sqlite() -> None:
    async def create_schema() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_schema())


def test_database_runtime_readiness_executes_a_query() -> None:
    async def check_database() -> None:
        runtime = create_database("sqlite+aiosqlite:///:memory:")
        assert await runtime.check_ready()
        await runtime.dispose()

    asyncio.run(check_database())
