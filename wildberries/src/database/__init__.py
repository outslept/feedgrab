import logging
from .db_connection import DatabaseConnection
from .review_manager import ReviewManager
from .product_manager import ProductManager
from .subscription_manager import SubscriptionManager
from ..config.settings import config
from datetime import datetime
from telegram import User

class Database:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = DatabaseConnection(config.DATABASE_NAME)
        self.review_manager = ReviewManager(self.connection)
        self.product_manager = ProductManager(self.connection)
        self.subscription_manager = SubscriptionManager(self.connection)

    def init_db(self):
        try:
            self.connection.init_db()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.exception("Failed to initialize database")
            raise

    def get_user_uuid(self, telegram_id):
        try:
            return self.subscription_manager.get_or_create_user(telegram_id)
        except Exception as e:
            self.logger.exception(f"Error getting user UUID for telegram_id: {telegram_id}")
            raise

    def get_telegram_id(self, user_uuid):
        try:
            session = self.connection.get_session()
            user = session.query(User).filter_by(uuid=user_uuid).first()
            return user.telegram_id if user else None
        except Exception as e:
            self.logger.exception(f"Error getting telegram_id for user_uuid: {user_uuid}")
            raise
        finally:
            session.close()

    def save_reviews(self, product_id, reviews):
        try:
            self.review_manager.save_reviews(product_id, reviews, datetime.now().isoformat())
            self.logger.info(f"Saved {len(reviews)} reviews for product_id: {product_id}")
        except Exception as e:
            self.logger.exception(f"Error saving reviews for product_id: {product_id}")
            raise

    def save_product_info(self, product_info):
        try:
            self.product_manager.save_product_info(product_info)
            self.logger.info(f"Saved product info for article: {product_info['article']}")
        except Exception as e:
            self.logger.exception(f"Error saving product info for article: {product_info['article']}")
            raise

    def get_user_subscriptions(self, user_uuid):
        try:
            return self.subscription_manager.get_user_subscriptions(user_uuid)
        except Exception as e:
            self.logger.exception(f"Error getting subscriptions for user_uuid: {user_uuid}")
            raise

    def is_user_subscribed(self, user_uuid, product_id):
        try:
            return self.subscription_manager.is_user_subscribed(user_uuid, product_id)
        except Exception as e:
            self.logger.exception(f"Error checking subscription for user_uuid: {user_uuid}, product_id: {product_id}")
            raise

    def subscribe_user(self, user_uuid, product_id):
        try:
            self.subscription_manager.subscribe_user(user_uuid, product_id)
            self.logger.info(f"User {user_uuid} subscribed to product_id: {product_id}")
        except Exception as e:
            self.logger.exception(f"Error subscribing user_uuid: {user_uuid} to product_id: {product_id}")
            raise

    def unsubscribe_user(self, user_uuid, product_id):
        try:
            self.subscription_manager.unsubscribe_user(user_uuid, product_id)
            self.logger.info(f"User {user_uuid} unsubscribed from product_id: {product_id}")
        except Exception as e:
            self.logger.exception(f"Error unsubscribing user_uuid: {user_uuid} from product_id: {product_id}")
            raise

    def get_product_info(self, product_id):
        try:
            return self.product_manager.get_product_info(product_id)
        except Exception as e:
            self.logger.exception(f"Error getting product info for product_id: {product_id}")
            raise

    def get_latest_review(self, product_id):
        try:
            return self.review_manager.get_latest_review(product_id)
        except Exception as e:
            self.logger.exception(f"Error getting latest review for product_id: {product_id}")
            raise
    
    def get_all_subscriptions(self):
        try:
            return self.subscription_manager.get_all_subscriptions()
        except Exception as e:
            self.logger.exception("Error getting all subscriptions")
            raise

    def update_subscription_check_time(self, user_uuid, product_id):
        try:
            self.subscription_manager.update_subscription_check_time(user_uuid, product_id)
            self.logger.info(f"Updated check time for user {user_uuid}, product {product_id}")
        except Exception as e:
            self.logger.exception(f"Error updating check time for user {user_uuid}, product {product_id}")
            raise
