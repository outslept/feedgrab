from datetime import datetime
from src.models.models import Subscription, ProductInfo, User
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
import uuid

class SubscriptionManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_or_create_user(self, telegram_id):
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, uuid=str(uuid.uuid4()))
                session.add(user)
                session.commit()
            return user.uuid
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка при получении или создании пользователя: {str(e)}")
        finally:
            session.close()

    def subscribe_user(self, user_uuid, product_id):
        session = self.db.get_session()
        try:
            subscription = Subscription(
                user_uuid=user_uuid,
                product_id=product_id,
                last_check_time=datetime.now().isoformat()
            )
            session.merge(subscription)
            session.commit()
            self.db.logger.info(f"Пользователь {user_uuid} подписался на товар {product_id}")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка при подписке пользователя {user_uuid} на товар {product_id}: {str(e)}")
        finally:
            session.close()

    def unsubscribe_user(self, user_uuid, product_id):
        session = self.db.get_session()
        try:
            session.query(Subscription).filter_by(user_uuid=user_uuid, product_id=product_id).delete()
            session.commit()
            self.db.logger.info(f"Пользователь {user_uuid} отписался от товара {product_id}")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка при отписке пользователя {user_uuid} от товара {product_id}: {str(e)}")
        finally:
            session.close()

    def get_user_subscriptions(self, user_uuid):
        session = self.db.get_session()
        try:
            subscriptions = session.query(Subscription.product_id, ProductInfo.name)\
                .join(ProductInfo, Subscription.product_id == ProductInfo.product_id)\
                .filter(Subscription.user_uuid == user_uuid)\
                .all()
            return subscriptions
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка при получении подписок пользователя {user_uuid}: {str(e)}")
        finally:
            session.close()
        return []

    def is_user_subscribed(self, user_uuid, product_id):
        session = self.db.get_session()
        try:
            subscription = session.query(Subscription)\
                .filter_by(user_uuid=user_uuid, product_id=product_id)\
                .first()
            return subscription is not None
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка при проверке подписки пользователя {user_uuid} на товар {product_id}: {str(e)}")
        finally:
            session.close()
        return False

    def get_product_subscribers(self, product_id):
        session = self.db.get_session()
        try:
            subscribers = session.query(Subscription.user_uuid)\
                .filter_by(product_id=product_id)\
                .all()
            return [subscriber.user_uuid for subscriber in subscribers]
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка при получении подписчиков товара {product_id}: {str(e)}")
        finally:
            session.close()
        return []

    def update_subscription_check_time(self, user_uuid, product_id):
        session = self.db.get_session()
        try:
            subscription = session.query(Subscription)\
                .filter_by(user_uuid=user_uuid, product_id=product_id)\
                .first()
            if subscription:
                subscription.last_check_time = datetime.now().isoformat()
                session.commit()
                self.db.logger.info(f"Обновлено время последней проверки для пользователя {user_uuid} и товара {product_id}")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка при обновлении времени проверки для пользователя {user_uuid} и товара {product_id}: {str(e)}")
        finally:
            session.close()

    def get_all_subscriptions(self):
        session = self.db.get_session()
        try:
            subscriptions = session.query(Subscription).all()
            return [(sub.user_uuid, sub.product_id, sub.last_check_time) for sub in subscriptions]
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка при получении всех подписок: {str(e)}")
        finally:
            session.close()
        return []