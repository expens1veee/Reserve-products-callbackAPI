import enum
from sqlalchemy import ForeignKey, Enum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from datetime import datetime


class TaskStatus(enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ProductsModel(Base):
    __tablename__ = 'products'

    product_id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    available_quantity: Mapped[int]


class ReservationsModel(Base):
    __tablename__ = 'reservations'

    reservation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.product_id'))
    quantity: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum"), nullable=False, default=TaskStatus.pending
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
