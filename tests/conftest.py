import pytest_asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from app.main import app

from app.db import Base, get_db

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    TEST_DATABASE_URL = "postgresql+asyncpg://user:password@db:5432/mydb_test"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

test_session_maker = async_sessionmaker(
    test_engine,
    expire_on_commit=False,
    class_=AsyncSession
)


async def get_override_db():
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.commit()

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.commit()


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database):
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client():
    app.dependency_overrides[get_db] = get_override_db

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_product(db_session):
    from app.models import ProductsModel

    product = ProductsModel(
        product_id=1,
        product_name='Test Product',
        available_quantity=100
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def multiple_products(db_session):
    from app.models import ProductsModel

    products = [
        ProductsModel(
            product_id=i,
            product_name=f'Test Product {i}',
            available_quantity=i * 10
        )
        for i in range(6)
    ]
    db_session.add_all(products)
    await db_session.commit()

    for product in products:
        await db_session.refresh(product)

    return products


@pytest_asyncio.fixture
async def sample_reservation(db_session, sample_product):
    from app.models import ReservationsModel, TaskStatus
    from datetime import datetime

    reservation = ReservationsModel(
        product_id=sample_product.product_id,
        quantity=10,
        status=TaskStatus.completed,
        timestamp=datetime.utcnow(),
    )

    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)

    return reservation
