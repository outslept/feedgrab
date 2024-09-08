import asyncio
from database import get_all_products, save_reviews
from wildberries_parser import parse_product_reviews
from datetime import datetime
import logging

logger = logging.getLogger('cron_job')

async def update_reviews():
    products = get_all_products()
    for product_id in products:
        try:
            _, reviews = await parse_product_reviews(product_id)
            if reviews:
                save_reviews(product_id, reviews, datetime.now().isoformat())
                logger.info(f"Отзывы для товара {product_id} успешно обновлены")
            else:
                logger.warning(f"Не удалось получить отзывы для товара {product_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении отзывов для товара {product_id}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(update_reviews())