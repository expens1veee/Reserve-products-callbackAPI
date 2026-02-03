from fastapi import APIRouter, Depends, HTTPException, status
from app.logger import logger
from app.schema import Reservation, ResponseReservation, ResponseType
from typing import Annotated
from app.db import AsyncSession, get_db
from app.models import ProductsModel, ReservationsModel, TaskStatus
from sqlalchemy import select, update, func
from datetime import datetime


router = APIRouter(tags=["public"])
reservation_router = APIRouter(prefix="/reservation", tags=["reservation"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@reservation_router.post("/reserve", response_model=ResponseReservation)
async def reserve(reservation: Reservation, session: SessionDep) -> ResponseReservation:
    logger.info(f"Attempting reservation: {reservation.model_dump()}")

    res = await session.get(ProductsModel, reservation.product_id)

    if res is None:
        logger.error(f"Product {reservation.product_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": ResponseType.error.value,
                "message": "Invalid product ID.",
                "reservation_id": None
            }
        )

    stmt = (
        select(ProductsModel.available_quantity)
        .where(reservation.product_id == ProductsModel.product_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    available_quantity = result.scalar_one()
    if available_quantity < reservation.quantity:
        logger.warning(f"Insufficient stock for product {reservation.product_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": ResponseType.error.value,
                "message": f"Not enough stock available.",
                "reservation_id": None
            }
        )

    await session.execute(
        update(ProductsModel)
        .where(reservation.product_id == ProductsModel.product_id)
        .values(available_quantity=available_quantity - reservation.quantity)
    )

    reservation_row = ReservationsModel(
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=TaskStatus.completed,
        timestamp=reservation.timestamp
    )
    session.add(reservation_row)

    await session.commit()
    await session.refresh(reservation_row)

    logger.info(f"Reservation successful: {reservation_row.reservation_id}")
    return ResponseReservation(
        status=ResponseType.success,
        message=f"Reservation completed successfully.",
        reservation_id=reservation_row.reservation_id
    )


@reservation_router.get("/{reservation_id}")
async def get_reservation(reservation_id: int, session: SessionDep):
    stmt = select(ReservationsModel.status).where(reservation_id == ReservationsModel.reservation_id)
    result = await session.execute(stmt)
    result_status = result.scalar_one_or_none()
    if result_status is None:
        return {"status": "reservation_id does not exist"}
    return {"status": result_status.value}


@router.get("/seed-data")
async def seed_database(session: SessionDep):
    logger.info("Запрос на заполнение базы данных тестовыми данными")

    count_result = await session.execute(select(func.count(ProductsModel.product_id)))
    products_count = count_result.scalar()
    
    if products_count > 0:
        logger.warning("База данных уже содержит данные")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="База данных уже содержит данные. Очистите таблицы перед заполнением."
        )
    
    try:
        products = [
            ProductsModel(product_name="Ноутбук Dell XPS 15", available_quantity=10),
            ProductsModel(product_name="iPhone 15 Pro", available_quantity=25),
            ProductsModel(product_name="Samsung Galaxy S24", available_quantity=15),
            ProductsModel(product_name="MacBook Pro M3", available_quantity=8),
            ProductsModel(product_name="Наушники Sony WH-1000XM5", available_quantity=30),
            ProductsModel(product_name="Планшет iPad Air", available_quantity=12),
        ]
        
        session.add_all(products)
        await session.flush()

        reservations = [
            ReservationsModel(
                product_id=products[0].product_id,
                quantity=2,
                status=TaskStatus.completed,
                timestamp=datetime.now()
            ),
            ReservationsModel(
                product_id=products[1].product_id,
                quantity=5,
                status=TaskStatus.completed,
                timestamp=datetime.now()
            ),
            ReservationsModel(
                product_id=products[2].product_id,
                quantity=3,
                status=TaskStatus.pending,
                timestamp=datetime.now()
            ),
            ReservationsModel(
                product_id=products[3].product_id,
                quantity=1,
                status=TaskStatus.completed,
                timestamp=datetime.now()
            ),
            ReservationsModel(
                product_id=products[4].product_id,
                quantity=10,
                status=TaskStatus.completed,
                timestamp=datetime.now()
            ),
        ]
        
        session.add_all(reservations)
        await session.commit()
        
        logger.info(f"База данных заполнена: {len(products)} продуктов, {len(reservations)} резерваций")
        
        return {
            "message": "База данных успешно заполнена тестовыми данными",
            "products_added": len(products),
            "reservations_added": len(reservations)
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при заполнении БД: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при заполнении базы данных: {str(e)}"
        )
