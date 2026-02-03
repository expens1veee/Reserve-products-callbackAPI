from datetime import datetime
from pydantic import BaseModel, PositiveInt
import enum


class ResponseType(enum.Enum):
    error = "error"
    success = "success"


class Products(BaseModel):
    product_name: str
    available_quantity: PositiveInt


class Reservation(BaseModel):
    product_id: PositiveInt
    quantity: PositiveInt
    timestamp: datetime


class ResponseReservation(BaseModel):
    status: ResponseType
    message: str
    reservation_id: PositiveInt
