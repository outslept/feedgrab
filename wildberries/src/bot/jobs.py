from src.database import Database
from src.parsers.wildberries_parser import WildberriesParser
import logging
from datetime import datetime

class JobHandlers:
    def __init__(self, database, scheduler, parser):
        self.database = database
        self.scheduler = scheduler
        self.parser = parser
        self.logger = logging.getLogger(__name__)

    async def periodic_review_check(self, context):
        self.logger.info("Starting periodic review check.")
        subscriptions = self.database.get_all_subscriptions()

        for user_uuid, product_id, last_check_time in subscriptions:
            try:
                product_info = await self.parser.get_product_info(product_id)
                if not product_info:
                    self.logger.warning(f"Product info not found for article: {product_id}")
                    continue

                last_review = self.database.get_latest_review(product_id)
                if last_review:
                    new_reviews = await self.parser.check_new_reviews(product_id, last_review['date'])
                    if new_reviews:
                        for review in new_reviews:
                            notification_message = (
                                f"🆕 Новый отзыв для товара '{product_info['name']}' (артикул {product_info['article']})\n\n"
                                f"⭐️ Рейтинг: {review['stars']}/5\n"
                                f"📋 Текст отзыва: {review['text']}\n"
                                f"👤 Автор: {review['name']}\n"
                                f"🗓️ Дата: {review['date']}"
                            )
                            await context.bot.send_message(chat_id=self.database.get_telegram_id(user_uuid), text=notification_message)
                        
                        self.database.save_reviews(product_id, new_reviews)
                        self.logger.info(f"Sent notifications for new reviews of article {product_id} to user {user_uuid}.")

                self.database.subscription_manager.update_subscription_check_time(user_uuid, product_id)
            except Exception as e:
                self.logger.exception(f"Error checking new reviews for article {product_id}")

        self.logger.info("Periodic review check completed.")
