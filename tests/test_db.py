import pytest


@pytest.mark.asyncio
async def test_database_connection(sample_product, db_session):
    assert db_session is not None

    assert sample_product.product_id == 1
    assert sample_product.product_name == "Test Product"
    assert sample_product.available_quantity == 100

    from app.models import ProductsModel

    product_id_db = await db_session.get(ProductsModel, sample_product.product_id)
    assert product_id_db is not None
    assert product_id_db.product_name == "Test Product"
