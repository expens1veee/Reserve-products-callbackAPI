from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import set_db
from app.middleware import LoggingMiddleware
from app.routes import router, reservation_router
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await set_db()
    logger.info(f"Setting up database")
    yield
    logger.info(f"Shutting up connection")


app = FastAPI(lifespan=lifespan)
app.add_middleware(LoggingMiddleware)
app.include_router(reservation_router)
app.include_router(router)

