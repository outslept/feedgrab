import sqlite3
import json
from config import DATABASE_NAME
from datetime import datetime
import logging

logger = logging.getLogger('database')

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reviews
                 (product_id TEXT, review_data TEXT, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS statistics
                 (date TEXT, product_id TEXT, review_count INTEGER)''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_reviews(product_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT review_data, last_updated FROM reviews WHERE product_id = ?", (product_id,))
    result = c.fetchone()
    conn.close()
    if result:
        logger.info(f"Получены отзывы для товара {product_id}")
        return json.loads(result[0]), result[1]
    logger.info(f"Отзывы для товара {product_id} не найдены в базе данных")
    return None, None

def save_reviews(product_id, reviews, last_updated):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO reviews (product_id, review_data, last_updated) VALUES (?, ?, ?)",
                  (product_id, json.dumps(reviews), last_updated))
        conn.commit()
        logger.info(f"Отзывы для товара {product_id} успешно сохранены")
    except Exception as e:
        logger.error(f"Ошибка при сохранении отзывов для товара {product_id}: {str(e)}")
    finally:
        conn.close()

def get_all_products():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT product_id FROM reviews")
    products = [row[0] for row in c.fetchall()]
    conn.close()
    logger.info(f"Получен список всех продуктов: {len(products)} продуктов")
    return products

def get_all_reviews():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT product_id, review_data FROM reviews")
    results = c.fetchall()
    conn.close()
    
    all_reviews = []
    for product_id, review_data in results:
        reviews = json.loads(review_data)
        for review in reviews:
            review['product_id'] = product_id
        all_reviews.extend(reviews)
    
    logger.info(f"Получены все отзывы: {len(all_reviews)} отзывов")
    return all_reviews