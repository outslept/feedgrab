from telegram import Update
from src.utils.excel_generator import ExcelGenerator
import logging
import re

class MessageHandlers:
    def __init__(self, database, scheduler, parser):
        self.database = database
        self.scheduler = scheduler
        self.parser = parser
        self.excel_generator = ExcelGenerator()
        self.logger = logging.getLogger(__name__)

    async def handle_input(self, update: Update, context):
        user_id = update.effective_user.id
        user_uuid = self.database.get_user_uuid(user_id)
        user_input = update.message.text.strip()

        try:
            if context.user_data.get('awaiting_subscription'):
                await self.process_subscription(update, context, user_input, user_uuid)
            elif self.is_valid_input(user_input):
                await self.process_review_request(update, context, user_input, user_uuid)
            else:
                await update.message.reply_text("Invalid input format. Please send a valid article number or product URL.")
        except Exception as e:
            self.logger.exception(f"Error handling user input: {user_input}")
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")

    def is_valid_input(self, user_input):
        if user_input.startswith('[') and user_input.endswith(']'):
            return all(self.is_valid_article(item.strip()) for item in user_input[1:-1].split(','))
        return self.is_valid_article(user_input) or self.is_valid_url(user_input)

    def is_valid_article(self, article):
        return article.isdigit() and len(article) >= 6

    def is_valid_url(self, url):
        wb_domains = "|".join(self.parser.config.WILDBERRIES_DOMAINS)
        pattern = rf"https?://({wb_domains})/(catalog/\d+/detail\.aspx|product/.+/\d+)"
        return re.match(pattern, url) is not None

    async def process_review_request(self, update: Update, context, user_input, user_uuid):
        await update.message.reply_text("Processing your request. Please wait...")

        try:
            if user_input.startswith('[') and user_input.endswith(']'):
                articles = [item.strip() for item in user_input[1:-1].split(',')]
            else:
                articles = [user_input]

            results = await self.parser.parse_multiple_products(articles)
            
            for product_info, reviews in results:
                if reviews:
                    self.database.save_reviews(product_info['article'], reviews)
                    self.database.save_product_info(product_info)
                    excel_file, filename = self.excel_generator.generate_excel(reviews, product_info)
                    await update.message.reply_document(
                        document=excel_file, 
                        filename=filename,
                        caption=f"Current reviews for article {product_info['article']}"
                    )
                else:
                    await update.message.reply_text(f"No reviews found for article {product_info['article']}.")
        except Exception as e:
            self.logger.exception(f"Error processing review request: {user_input}")
            await update.message.reply_text("An error occurred while fetching the reviews. Please try again later.")

    async def process_subscription(self, update: Update, context, user_input, user_uuid):
        try:
            article = self.parser.extract_article_from_url(user_input)
            if not article:
                await update.message.reply_text("Invalid input format. Please send a valid article number or product URL.")
                return

            if self.database.is_user_subscribed(user_uuid, article):
                await update.message.reply_text(f"You are already subscribed to notifications for article {article}.")
            else:
                self.database.subscribe_user(user_uuid, article)
                self.scheduler.add_job(user_uuid, article)
                await update.message.reply_text(f"You have successfully subscribed to notifications for article {article}.")

            context.user_data['awaiting_subscription'] = False
        except Exception as e:
            self.logger.exception(f"Error processing subscription: {user_input}")
            await update.message.reply_text("An error occurred while processing your subscription. Please try again later.")
            context.user_data['awaiting_subscription'] = False
