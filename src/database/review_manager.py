import json
from datetime import datetime, timedelta
from src.models.models import Review
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

class ReviewManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def save_reviews(self, product_id, reviews, last_updated):
        session = self.db.get_session()
        try:
            review = Review(
                product_id=product_id,
                review_data=json.dumps(reviews, ensure_ascii=False),
                last_updated=last_updated
            )
            session.merge(review)
            session.commit()
            self.db.logger.info(f"Отзывы для товара {product_id} успешно сохранены")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка сохранения отзывов для товара {product_id}: {str(e)}")
        finally:
            session.close()

    def get_reviews(self, product_id):
        session = self.db.get_session()
        try:
            review = session.query(Review).filter_by(product_id=product_id).first()
            if review:
                return json.loads(review.review_data), review.last_updated
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка получения отзывов для товара {product_id}: {str(e)}")
        finally:
            session.close()
        return None, None

    def get_latest_review(self, product_id):
        reviews, _ = self.get_reviews(product_id)
        if reviews:
            return max(reviews, key=lambda x: x['date'])
        return None

    def cleanup_old_reviews(self, days_to_keep=30):
        session = self.db.get_session()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            deleted = session.query(Review).filter(Review.last_updated < cutoff_date).delete()
            session.commit()
            self.db.logger.info(f"Удалено {deleted} устаревших записей отзывов")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка при очистке старых отзывов: {str(e)}")
        finally:
            session.close()