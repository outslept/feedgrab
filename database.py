import sqlite3
import json
from datetime import datetime, timedelta
import logging

class Database:
    def __init__(self, database_name):
        self.database_name = database_name
        self.logger = logging.getLogger('database')

    def connect(self):
        return sqlite3.connect(self.database_name)

    def init_db(self):
        conn = self.connect()
        c = conn.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS reviews
            (product_id TEXT, review_data TEXT, last_updated TEXT);
            
            CREATE TABLE IF NOT EXISTS product_info
            (product_id TEXT PRIMARY KEY, imt_id TEXT, name TEXT, brand TEXT, seller_id TEXT);
            
            CREATE TABLE IF NOT EXISTS subscriptions
            (user_id INTEGER, product_id TEXT, last_check_time TEXT, UNIQUE(user_id, product_id));
            
            CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
        ''')
        conn.commit()
        conn.close()
        self.logger.info("База данных инициализирована")

    def save_reviews(self, product_id, reviews, last_updated):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("INSERT OR REPLACE INTO reviews (product_id, review_data, last_updated) VALUES (?, ?, ?)",
                      (product_id, json.dumps(reviews), last_updated))
            conn.commit()
            self.logger.info(f"Отзывы для товара {product_id} успешно сохранены")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении отзывов для товара {product_id}: {str(e)}")
        finally:
            conn.close()

    def get_reviews(self, product_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT review_data, last_updated FROM reviews WHERE product_id = ?", (product_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return json.loads(result[0]), result[1]
        return None, None

    def get_all_products(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT DISTINCT product_id FROM product_info")
        products = [row[0] for row in c.fetchall()]
        conn.close()
        return products

    def save_product_info(self, product_info):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO product_info 
                (product_id, imt_id, name, brand, seller_id) 
                VALUES (?, ?, ?, ?, ?)
            """, (product_info['article'], product_info['imt_id'], product_info['name'], 
                  product_info['brand'], product_info['seller_id']))
            conn.commit()
            self.logger.info(f"Информация о товаре {product_info['article']} успешно сохранена")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении информации о товаре {product_info['article']}: {str(e)}")
        finally:
            conn.close()

    def get_product_info(self, product_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM product_info WHERE product_id = ?", (product_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return {
                'article': result[0],
                'imt_id': result[1],
                'name': result[2],
                'brand': result[3],
                'seller_id': result[4]
            }
        return None

    def subscribe_user(self, user_id, product_id):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("INSERT OR REPLACE INTO subscriptions (user_id, product_id, last_check_time) VALUES (?, ?, ?)", 
                      (user_id, product_id, datetime.now().isoformat()))
            conn.commit()
            self.logger.info(f"Пользователь {user_id} подписался на товар {product_id}")
        except Exception as e:
            self.logger.error(f"Ошибка при подписке пользователя {user_id} на товар {product_id}: {str(e)}")
        finally:
            conn.close()

    def unsubscribe_user(self, user_id, product_id):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM subscriptions WHERE user_id = ? AND product_id = ?", (user_id, product_id))
            conn.commit()
            self.logger.info(f"Пользователь {user_id} отписался от товара {product_id}")
        except Exception as e:
            self.logger.error(f"Ошибка при отписке пользователя {user_id} от товара {product_id}: {str(e)}")
        finally:
            conn.close()

    def get_user_subscriptions(self, user_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT s.product_id, p.name 
            FROM subscriptions s
            JOIN product_info p ON s.product_id = p.product_id
            WHERE s.user_id = ?
        """, (user_id,))
        subscriptions = c.fetchall()
        conn.close()
        return subscriptions

    def is_user_subscribed(self, user_id, product_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT 1 FROM subscriptions WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        result = c.fetchone() is not None
        conn.close()
        return result

    def get_product_subscribers(self, product_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT user_id FROM subscriptions WHERE product_id = ?", (product_id,))
        subscribers = [row[0] for row in c.fetchall()]
        conn.close()
        return subscribers

    def get_latest_review(self, product_id):
        reviews, _ = self.get_reviews(product_id)
        if reviews:
            return max(reviews, key=lambda x: x['date'])
        return None

    def update_product_info(self, product_info):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE product_info 
                SET imt_id = ?, name = ?, brand = ?, seller_id = ?
                WHERE product_id = ?
            """, (product_info['imt_id'], product_info['name'], product_info['brand'], 
                  product_info['seller_id'], product_info['article']))
            conn.commit()
            self.logger.info(f"Информация о товаре {product_info['article']} успешно обновлена")
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении информации о товаре {product_info['article']}: {str(e)}")
        finally:
            conn.close()

    def get_products_page(self, page, products_per_page):
        conn = self.connect()
        c = conn.cursor()
        offset = (page - 1) * products_per_page
        c.execute("""
            SELECT product_id, name 
            FROM product_info 
            ORDER BY product_id 
            LIMIT ? OFFSET ?
        """, (products_per_page, offset))
        products = c.fetchall()
        conn.close()
        return products

    def get_total_products_count(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM product_info")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_reviews_count(self, product_id):
        reviews, _ = self.get_reviews(product_id)
        return len(reviews) if reviews else 0

    def get_latest_reviews(self, product_id, limit=5):
        reviews, _ = self.get_reviews(product_id)
        if reviews:
            sorted_reviews = sorted(reviews, key=lambda x: x['date'], reverse=True)
            return sorted_reviews[:limit]
        return []

    def search_products(self, query):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT product_id, name 
            FROM product_info 
            WHERE name LIKE ? OR product_id LIKE ?
            ORDER BY product_id
            LIMIT 50
        """, (f'%{query}%', f'%{query}%'))
        products = c.fetchall()
        conn.close()
        return products

    def get_product_stats(self, product_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT 
                COUNT(*) as total_reviews,
                AVG(CAST(json_extract(value, '$.stars') AS INTEGER)) as avg_rating,
                MIN(json_extract(value, '$.date')) as first_review_date,
                MAX(json_extract(value, '$.date')) as last_review_date
            FROM reviews, json_each(reviews.review_data)
            WHERE product_id = ?
        """, (product_id,))
        stats = c.fetchone()
        conn.close()
        if stats:
            return {
                'total_reviews': stats[0],
                'avg_rating': round(stats[1], 2) if stats[1] else None,
                'first_review_date': stats[2],
                'last_review_date': stats[3]
            }
        return None

    def cleanup_old_reviews(self, days_to_keep=30):
        conn = self.connect()
        c = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        try:
            c.execute("DELETE FROM reviews WHERE last_updated < ?", (cutoff_date,))
            conn.commit()
            self.logger.info(f"Удалено {c.rowcount} устаревших записей отзывов")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке устаревших отзывов: {str(e)}")
        finally:
            conn.close()

    def get_all_subscriptions(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT user_id, product_id, last_check_time FROM subscriptions")
        subscriptions = c.fetchall()
        conn.close()
        return subscriptions

    def update_subscription_check_time(self, user_id, product_id):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("UPDATE subscriptions SET last_check_time = ? WHERE user_id = ? AND product_id = ?",
                      (datetime.now().isoformat(), user_id, product_id))
            conn.commit()
            self.logger.info(f"Обновлено время последней проверки для пользователя {user_id} и товара {product_id}")
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении времени проверки для пользователя {user_id} и товара {product_id}: {str(e)}")
        finally:
            conn.close()

    def get_products_without_info(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT r.product_id
            FROM reviews r
            LEFT JOIN product_info p ON r.product_id = p.product_id
            WHERE p.product_id IS NULL
        """)
        products = [row[0] for row in c.fetchall()]
        conn.close()
        return products

    def delete_product(self, product_id):
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM product_info WHERE product_id = ?", (product_id,))
            c.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))
            c.execute("DELETE FROM subscriptions WHERE product_id = ?", (product_id,))
            conn.commit()
            self.logger.info(f"Товар {product_id} и связанные данные удалены из базы")
        except Exception as e:
            self.logger.error(f"Ошибка при удалении товара {product_id}: {str(e)}")
        finally:
            conn.close()