import pytest
from sqlalchemy import select

from app.models import ProductsModel, ReservationsModel


@pytest.mark.asyncio
async def test_reserve_product_happy_path(client, sample_product, db_session):
    assert sample_product.available_quantity == 100

    payload = {
        "product_id": 1,
        "quantity": 10,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "success"
    assert "reservation_id" in data
    reservation_id = data["reservation_id"]
    assert reservation_id > 0

    result = await db_session.execute(
        select(ProductsModel.available_quantity)
        .where(ProductsModel.product_id == sample_product.product_id)
    )
    available_quantity = result.scalar_one()

    assert available_quantity == sample_product.available_quantity - payload["quantity"]

    stmt = await db_session.get(ReservationsModel, reservation_id)

    assert stmt is not None

    response = await client.get(f"/reservation/{reservation_id}")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_reserve_insufficient_stock(client, sample_product):
    assert sample_product.available_quantity == 100

    payload = {
        "product_id": 1,
        "quantity": 200,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 400
    assert data["detail"]["status"] == "error"


@pytest.mark.asyncio
async def test_reserve_product_not_found(client, sample_product):
    assert sample_product.product_id == 1

    payload = {
        "product_id": 2,
        "quantity": 100,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 404
    assert data["detail"]["status"] == "error"


@pytest.mark.asyncio
async def test_reserve_negative_quantity(client, sample_product):
    payload = {
        "product_id": 1,
        "quantity": -100,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reserve_invalid_json(client, sample_product):
    payload = {
        "product_id": 1,
        "quantity": -100,
        "timestamp": "2024-09-04T12:00:00Z",
        "status": "success"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_seed_data_success(client, db_session):
    result = await db_session.execute(select(ProductsModel.product_id))
    products_before = result.scalars().all()
    assert len(products_before) == 0

    response = await client.post("/seed-data")
    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "База данных успешно заполнена тестовыми данными"
    assert data["products_added"] == 6
    assert data["reservations_added"] == 5

    result = await db_session.execute(select(ProductsModel))
    products = result.scalars().all()
    assert len(products) == 6

    result = await db_session.execute(select(ReservationsModel))
    reservations = result.scalars().all()
    assert len(reservations) == 5

    product_names = {p.product_name for p in products}
    expected_names = {
        "Ноутбук Dell XPS 15",
        "iPhone 15 Pro",
        "Samsung Galaxy S24",
        "MacBook Pro M3",
        "Наушники Sony WH-1000XM5",
        "Планшет iPad Air"
    }
    assert product_names == expected_names


@pytest.mark.asyncio
async def test_seed_data_already_has_data(client, db_session, sample_product):
    result = await db_session.execute(select(ProductsModel.product_id))
    products_before = result.scalars().all()
    assert len(products_before) > 0

    response = await client.post("/seed-data")
    data = response.json()

    assert response.status_code == 400
    assert "уже содержит данные" in data["detail"]


@pytest.mark.asyncio
async def test_seed_data_creates_reservations(client, db_session):
    response = await client.post("/seed-data")
    assert response.status_code == 200

    result = await db_session.execute(select(ReservationsModel))
    reservations = result.scalars().all()
    assert len(reservations) == 5

    result = await db_session.execute(select(ProductsModel.product_id))
    product_ids = {pid for pid in result.scalars().all()}

    for reservation in reservations:
        assert reservation.product_id in product_ids
        assert reservation.quantity > 0
        assert reservation.timestamp is not None


@pytest.mark.asyncio
async def test_get_reservation_not_found(client, db_session):
    response = await client.get("/reservation/99999")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data["status"] == "reservation_id does not exist"


@pytest.mark.asyncio
async def test_get_reservation_success(client, db_session, sample_product):
    from app.models import ReservationsModel, TaskStatus
    from datetime import datetime

    reservation = ReservationsModel(
        product_id=sample_product.product_id,
        quantity=5,
        status=TaskStatus.pending,
        timestamp=datetime.now()
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)

    response = await client.get(f"/reservation/{reservation.reservation_id}")
    data = response.json()
    
    assert response.status_code == 200
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_reservation_with_completed_status(client, db_session, sample_product):
    from app.models import ReservationsModel, TaskStatus
    from datetime import datetime
    
    reservation = ReservationsModel(
        product_id=sample_product.product_id,
        quantity=5,
        status=TaskStatus.completed,
        timestamp=datetime.now()
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)
    
    response = await client.get(f"/reservation/{reservation.reservation_id}")
    data = response.json()
    
    assert response.status_code == 200
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_get_reservation_with_failed_status(client, db_session, sample_product):
    from app.models import ReservationsModel, TaskStatus
    from datetime import datetime
    
    reservation = ReservationsModel(
        product_id=sample_product.product_id,
        quantity=5,
        status=TaskStatus.failed,
        timestamp=datetime.now()
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)
    
    response = await client.get(f"/reservation/{reservation.reservation_id}")
    data = response.json()
    
    assert response.status_code == 200
    assert data["status"] == "failed"


@pytest.mark.asyncio
async def test_reserve_exact_quantity_available(client, db_session, sample_product):
    payload = {
        "product_id": 1,
        "quantity": 100,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "success"

    result = await db_session.execute(
        select(ProductsModel.available_quantity)
        .where(ProductsModel.product_id == sample_product.product_id)
    )
    available_quantity = result.scalar_one()
    assert available_quantity == 0


@pytest.mark.asyncio
async def test_reserve_quantity_one(client, db_session, sample_product):
    payload = {
        "product_id": 1,
        "quantity": 1,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["reservation_id"] > 0


@pytest.mark.asyncio
async def test_reserve_multiple_times_same_product(client, db_session, sample_product):
    payload1 = {
        "product_id": 1,
        "quantity": 30,
        "timestamp": "2024-09-04T12:00:00Z"
    }
    response1 = await client.post("/reservation/reserve", json=payload1)
    assert response1.status_code == 200

    payload2 = {
        "product_id": 1,
        "quantity": 50,
        "timestamp": "2024-09-04T12:00:00Z"
    }
    response2 = await client.post("/reservation/reserve", json=payload2)
    assert response2.status_code == 200

    result = await db_session.execute(
        select(ProductsModel.available_quantity)
        .where(ProductsModel.product_id == sample_product.product_id)
    )
    available_quantity = result.scalar_one()
    assert available_quantity == 100 - 30 - 50


@pytest.mark.asyncio
async def test_reserve_with_different_timestamps(client, db_session, sample_product):
    from datetime import datetime, timezone
    
    payload = {
        "product_id": 1,
        "quantity": 10,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 200
    
    # Проверяем, что резервация создана
    result = await db_session.execute(
        select(ReservationsModel)
        .where(ReservationsModel.product_id == sample_product.product_id)
    )
    reservations = result.scalars().all()
    assert len(reservations) == 1
    assert reservations[0].quantity == 10


@pytest.mark.asyncio
async def test_reserve_product_with_zero_available(client, db_session):
    from app.models import ProductsModel

    product = ProductsModel(
        product_id=999,
        product_name="Out of Stock Product",
        available_quantity=0
    )
    db_session.add(product)
    await db_session.commit()
    
    payload = {
        "product_id": 999,
        "quantity": 1,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    assert response.status_code == 400
    assert data["detail"]["status"] == "error"
    assert "Not enough stock" in data["detail"]["message"]


@pytest.mark.asyncio
async def test_reserve_with_invalid_product_id_type(client):
    # Попытка передать строку вместо числа (будет обработано FastAPI как 422)
    payload = {
        "product_id": "invalid",
        "quantity": 10,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reserve_with_missing_fields(client):
    payload = {
        "product_id": 1,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reserve_with_zero_quantity(client, sample_product):
    payload = {
        "product_id": 1,
        "quantity": 0,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_reservation_with_invalid_id_type(client):
    response = await client.get("/reservation/invalid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_seed_data_error_handling_on_commit(client, db_session):
    """Тест обработки ошибок в seed_database при ошибке commit"""
    from app.routes import seed_database
    from fastapi import HTTPException
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=0)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add_all = MagicMock()
    mock_session.flush = AsyncMock()

    async def failing_commit():
        raise Exception("Database commit failed")
    
    mock_session.commit = AsyncMock(side_effect=failing_commit)
    mock_session.rollback = AsyncMock()

    # Вызываем функцию напрямую с мокнутой сессией
    with pytest.raises(HTTPException) as exc_info:
        await seed_database(mock_session)
    
    # Проверяем что это правильная ошибка
    assert exc_info.value.status_code == 500
    assert "Ошибка при заполнении базы данных" in str(exc_info.value.detail)
    
    # Проверяем что rollback был вызван
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_seed_data_error_handling_on_flush(client, db_session):
    """Тест обработки ошибок в seed_database при ошибке flush"""
    from app.routes import seed_database
    from fastapi import HTTPException
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=0)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add_all = MagicMock()

    async def failing_flush():
        raise Exception("Database flush failed")
    
    mock_session.flush = AsyncMock(side_effect=failing_flush)
    mock_session.rollback = AsyncMock()

    # Вызываем функцию напрямую с мокнутой сессией
    with pytest.raises(HTTPException) as exc_info:
        await seed_database(mock_session)
    
    assert exc_info.value.status_code == 500
    assert "Ошибка при заполнении базы данных" in str(exc_info.value.detail)
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_reserve_checks_product_exists_before_stock_check(client, db_session):
    payload = {
        "product_id": 99999,
        "quantity": 1000,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    data = response.json()

    # Должна быть ошибка 404 (продукт не найден), а не 400 (недостаточно товара)
    assert response.status_code == 404
    assert data["detail"]["status"] == "error"
    assert "Invalid product ID" in data["detail"]["message"]


@pytest.mark.asyncio
async def test_reserve_refresh_after_commit(client, db_session, sample_product):
    payload = {
        "product_id": 1,
        "quantity": 10,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "reservation_id" in data
    assert data["reservation_id"] > 0

    result = await db_session.execute(
        select(ReservationsModel).where(ReservationsModel.reservation_id == data["reservation_id"])
    )
    reservation = result.scalar_one_or_none()
    assert reservation is not None
    assert reservation.product_id == sample_product.product_id


@pytest.mark.asyncio
async def test_reserve_creates_reservation_with_correct_status(client, db_session, sample_product):
    payload = {
        "product_id": 1,
        "quantity": 10,
        "timestamp": "2024-09-04T12:00:00Z"
    }

    response = await client.post("/reservation/reserve", json=payload)
    assert response.status_code == 200
    data = response.json()

    result = await db_session.execute(
        select(ReservationsModel).where(ReservationsModel.reservation_id == data["reservation_id"])
    )
    reservation = result.scalar_one_or_none()
    assert reservation is not None
    assert reservation.status.value == "completed"


