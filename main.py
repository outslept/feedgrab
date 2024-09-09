import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from wildberries_parser import Parser
from excel_generator import ExcelGenerator
from database import Database
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

class WildberriesBot:
    def __init__(self):
        self.config = Config()
        self.parser = Parser(self.config)
        self.excel_generator = ExcelGenerator()
        self.database = Database(self.config.DATABASE_NAME)
        self.logger = logging.getLogger('telegram_bot')
        self.setup_logging()
        self.application = None

    def setup_logging(self):
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = 'wildberries_bot.log'
        log_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
        log_handler.setFormatter(log_formatter)
        self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    async def menu(self, update: Update, context):
        keyboard = [
            [InlineKeyboardButton("📊 Получить отзывы", callback_data='get_reviews'),
            InlineKeyboardButton("🔄 Проверить новые", callback_data='check_new_reviews')],
            [InlineKeyboardButton("📋 Список продуктов", callback_data='list_products'),
            InlineKeyboardButton("🔔 Управление уведомлениями", callback_data='manage_notifications')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "🤖 Добро пожаловать в бот отзывов Wildberries! Выберите опцию:"
        if update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup)

    async def handle_input(self, update: Update, context):
        user_input = update.message.text.strip()
        if context.user_data.get('awaiting_subscription'):
            await self.process_subscription(update, context, user_input)
        elif user_input.startswith('[') and user_input.endswith(']') or user_input.startswith('http') or user_input.isdigit():
            await self.process_review_request(update, context, user_input)
        else:
            await self.menu(update, context)

    async def process_review_request(self, update: Update, context, user_input):
        await update.message.reply_text("⏳ Обрабатываем ваш запрос. Пожалуйста, подождите...")

        try:
            results = await self.parser.parse_multiple_products(user_input)
            
            for article, reviews in results:
                if reviews:
                    product_info = await self.parser.get_product_info(article)
                    if product_info:
                        self.database.save_reviews(article, reviews, datetime.now().isoformat())
                        self.database.save_product_info(product_info)
                        excel_file, filename = self.excel_generator.generate_excel(reviews, product_info)
                        await update.message.reply_document(
                            document=excel_file, 
                            filename=filename,
                            caption=f"📊 Отзывы для артикула {article}"
                        )
                    else:
                        await update.message.reply_text(f"❌ Не удалось получить информацию о товаре {article}")
                else:
                    await update.message.reply_text(f"❌ Отзывов для товара {article} не найдено или произошла ошибка при обработке.")
            
            if len(results) > 1:
                await update.message.reply_text("✅ Обработка всех запрошенных товаров завершена.")
                
        except Exception as e:
            error_message = f"❗ Произошла ошибка: {str(e)}"
            self.logger.error(error_message)
            await update.message.reply_text(error_message)

    async def process_subscription(self, update: Update, context, user_input):
        context.user_data['awaiting_subscription'] = False
        user_id = update.effective_user.id
    
        if user_input.startswith('http'):
            article = self.parser.extract_article_from_url(user_input)
        else:
            article = user_input

        if not article:
            await update.message.reply_text("❌ Неверный формат ввода. Пожалуйста, отправьте корректный артикул или ссылку на товар.")
            return

        product_info = await self.parser.get_product_info(article)
        if not product_info:
            await update.message.reply_text(f"❌ Товар с артикулом {article} не найден.")
            return

        self.database.subscribe_user(user_id, article)
        await update.message.reply_text(f"✅ Вы успешно подписались на уведомления о новых отзывах для товара {product_info['name']} (артикул {article}).")
        
        keyboard = [
            [InlineKeyboardButton("Да", callback_data=f'fetch_subscribed_{article}')],
            [InlineKeyboardButton("Нет", callback_data='menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Хотите получить актуальные данные для подписанного товара?", reply_markup=reply_markup)

    async def fetch_subscribed_products(self, update: Update, context, articles):
        query = update.callback_query
        await query.answer()
        await query.message.edit_text("⏳ Получаем актуальные данные. Пожалуйста, подождите...")

        results = await asyncio.gather(*[self.parser.parse_single_product(article) for article in articles.split(',')])
        
        for article, reviews in results:
            if reviews:
                product_info = await self.parser.get_product_info(article)
                if product_info:
                    self.database.save_reviews(article, reviews, datetime.now().isoformat())
                    self.database.save_product_info(product_info)
                    excel_file, filename = self.excel_generator.generate_excel(reviews, product_info)
                    await query.message.reply_document(
                        document=excel_file, 
                        filename=filename,
                        caption=f"📊 Отзывы для артикула {article}"
                    )
                else:
                    await query.message.reply_text(f"❌ Не удалось получить информацию о товаре {article}")
            else:
                await query.message.reply_text(f"❌ Отзывов для товара {article} не найдено или произошла ошибка при обработке.")
        await query.message.reply_text("✅ Обработка всех запрошенных товаров завершена.")

    async def list_products(self, update: Update, context):
        query = update.callback_query
        await query.answer()
        page = int(context.user_data.get('product_page', 1))
        products_per_page = 10
        
        total_products = self.database.get_total_products_count()
        total_pages = (total_products - 1) // products_per_page + 1
        
        products = self.database.get_products_page(page, products_per_page)
    
        if not products:
            await query.message.edit_text("В базе данных нет товаров.")
            return

        keyboard = []
        for product_id, product_name in products:
            keyboard.append([
                InlineKeyboardButton(f"🛍️ {product_id} - {product_name[:30]}...", callback_data=f'product_info_{product_id}'),
                InlineKeyboardButton("📥", callback_data=f'download_{product_id}')
            ])

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'product_page_{page-1}'))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data=f'product_page_{page+1}'))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)

        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='menu')])
    
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"Список товаров (страница {page}/{total_pages}):", reply_markup=reply_markup)

    async def check_new_reviews_manual(self, update: Update, context):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        subscriptions = self.database.get_user_subscriptions(user_id)
        
        if not subscriptions:
            await query.message.edit_text("У вас нет активных подписок. Подпишитесь на товары, чтобы проверять новые отзывы.")
            return

        await query.message.edit_text("⏳ Проверяем наличие новых отзывов. Пожалуйста, подождите...")
        
        new_reviews_found = False
        for product_id, product_name in subscriptions:
            last_review = self.database.get_latest_review(product_id)
            if last_review:
                new_reviews = await self.parser.check_new_reviews(product_id, last_review['date'])
                if new_reviews:
                    new_reviews_found = True
                    product_info = await self.parser.get_product_info(product_id)
                    excel_file, filename = self.excel_generator.generate_excel(new_reviews, product_info)
                    await query.message.reply_document(
                        document=excel_file,
                        filename=filename,
                        caption=f"🆕 Новые отзывы для артикула {product_id} - {product_name}"
                    )
                    self.database.save_reviews(product_id, new_reviews, datetime.now().isoformat())

        if not new_reviews_found:
            await query.message.edit_text("✅ Новых отзывов не найдено.")
        else:
            await query.message.edit_text("✅ Проверка новых отзывов завершена.")

    async def button_callback(self, update: Update, context):
        query = update.callback_query
        await query.answer()

        if query.data == 'get_reviews':
            await query.message.reply_text("🔗 Пожалуйста, отправьте ссылку на товар Wildberries или артикул.")
        elif query.data == 'check_new_reviews':
            await self.check_new_reviews_manual(update, context)
        elif query.data == 'list_products':
            context.user_data['product_page'] = 1
            await self.list_products(update, context)
        elif query.data.startswith('product_page_'):
            context.user_data['product_page'] = int(query.data.split('_')[-1])
            await self.list_products(update, context)
        elif query.data == 'manage_notifications':
            await self.manage_notifications(update, context)
        elif query.data == 'help':
            await self.help_command(update, context)
        elif query.data == 'menu':
            await self.menu(update, context)
        elif query.data.startswith('download_'):
            product_id = query.data.split('_')[1]
            await self.download_product_reviews(update, context, product_id)
        elif query.data.startswith('fetch_subscribed_'):
            articles = query.data.split('_')[-1]
            await self.fetch_subscribed_products(update, context, articles)
        elif query.data == 'subscribe':
            await self.subscribe(update, context)
        elif query.data == 'unsubscribe':
            await self.unsubscribe(update, context)
        elif query.data == 'list_subscriptions':
            await self.list_subscriptions(update, context)
        elif query.data.startswith('unsub_'):
            product_id = query.data.split('_')[1]
            await self.unsubscribe_product(update, context, product_id)
        elif query.data.startswith('product_info_'):
            product_id = query.data.split('_')[-1]
            await self.show_product_info(update, context, product_id)

    async def download_product_reviews(self, update: Update, context, product_id):
        query = update.callback_query
        reviews, _ = self.database.get_reviews(product_id)
        if reviews:
            product_info = self.database.get_product_info(product_id)
            excel_file, filename = self.excel_generator.generate_excel(reviews, product_info)
            await query.message.reply_document(
                document=excel_file,
                filename=filename,
                caption=f"📊 Отзывы для артикула {product_id}"
            )
        else:
            await query.message.reply_text(f"❌ Отзывов для товара {product_id} не найдено.")

    async def periodic_review_check(self, context):
        self.logger.info("Начало периодической проверки новых отзывов.")
        subscriptions = self.database.get_all_subscriptions()

        for user_id, product_id, last_check_time in subscriptions:
            try:
                last_review = self.database.get_latest_review(product_id)
                if last_review:
                    new_reviews = await self.parser.check_new_reviews(product_id, last_review['date'])
                    if new_reviews:
                        product_info = await self.parser.get_product_info(product_id)
                        for review in new_reviews:
                            review_message = (
                                f"❗️Новый отзыв {review['stars']}⭐️\n"
                                f"От: {review['name']}\n"
                                f"{product_id} - {product_info['name']}\n"
                                f"Размер: {review.get('size', 'Не указан')}\n"
                                f"Цвет: {review.get('color', 'Не указан')}\n\n"
                                f"{review['text']}"
                            )
                            await self.application.bot.send_message(
                                chat_id=user_id,
                                text=review_message
                            )
                        self.database.save_reviews(product_id, new_reviews, datetime.now().isoformat())
                        self.logger.info(f"Новые отзывы для артикула {product_id} отправлены пользователю {user_id}.")
                self.database.update_subscription_check_time(user_id, product_id)
            except Exception as e:
                self.logger.error(f"Ошибка при проверке новых отзывов для артикула {product_id}: {str(e)}")

        self.logger.info("Периодическая проверка завершена.")

    async def manage_notifications(self, update: Update, context):
        query = update.callback_query
        keyboard = [
            [InlineKeyboardButton("➕ Подписаться", callback_data='subscribe'),
            InlineKeyboardButton("➖ Отписаться", callback_data='unsubscribe')],
            [InlineKeyboardButton("📋 Мои подписки", callback_data='list_subscriptions')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Управление уведомлениями:", reply_markup=reply_markup)

    async def subscribe(self, update: Update, context):
        query = update.callback_query
        await query.message.reply_text("Пожалуйста, отправьте артикул или ссылку на товар, на который хотите подписаться.")
        context.user_data['awaiting_subscription'] = True

    async def unsubscribe(self, update: Update, context):
        query = update.callback_query
        user_id = update.effective_user.id
        subscriptions = self.database.get_user_subscriptions(user_id)
    
        if not subscriptions:
            await query.message.edit_text("У вас нет активных подписок.")
            return

        keyboard = []
        for product_id, product_name in subscriptions:
            keyboard.append([InlineKeyboardButton(f"❌ {product_id} - {product_name[:30]}...", callback_data=f'unsub_{product_id}')])
    
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Выберите товар для отписки:", reply_markup=reply_markup)

    async def list_subscriptions(self, update: Update, context):
        query = update.callback_query
        user_id = update.effective_user.id
        subscriptions = self.database.get_user_subscriptions(user_id)
    
        if not subscriptions:
            await query.message.edit_text("У вас нет активных подписок.")
            return

        keyboard = []
        for product_id, product_name in subscriptions:
            keyboard.append([
                InlineKeyboardButton(f"{product_id} - {product_name[:30]}...", url=f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"),
                InlineKeyboardButton("❌", callback_data=f'unsub_{product_id}')
            ])

        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Ваши текущие подписки:", reply_markup=reply_markup)

    async def unsubscribe_product(self, update: Update, context, product_id):
        query = update.callback_query
        user_id = update.effective_user.id
        self.database.unsubscribe_user(user_id, product_id)
        product_info = self.database.get_product_info(product_id)
        product_name = product_info['name'] if product_info else product_id
        await query.message.edit_text(f"✅ Вы успешно отписались от товара {product_name} (артикул {product_id})")

    async def help_command(self, update: Update, context):
        help_text = """
🤖 *Помощь бота отзывов Wildberries*

Вот доступные команды:

🏁 /start - Запустить бота и показать главное меню
🏠 /menu - Показать главное меню
❓ /help - Показать это сообщение помощи
📊 Получить отзывы - Отправьте ссылку на товар или артикул для получения отзывов
🔄 Проверить новые отзывы - Проверить наличие новых отзывов для подписанных товаров
📋 Список продуктов - Просмотреть список всех отслеживаемых товаров
🔔 Управление уведомлениями - Подписаться или отписаться от уведомлений о новых отзывах

Вы также можете отправить ссылку на товар Wildberries или артикул напрямую, чтобы получить отзывы.

Для получения отзывов по нескольким товарам сразу, отправьте список артикулов в формате: [артикул1, артикул2, ...]

По любым вопросам или для обратной связи, пожалуйста, свяжитесь с @destroy2create.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def start(self, update: Update, context):
        await self.menu(update, context)

    def run(self):
        self.database.init_db()

        self.application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("menu", self.menu))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_input))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        self.schedule_jobs()

        self.logger.info("Бот запущен")
        self.application.run_polling()

    def schedule_jobs(self):
        if self.application:
            job_queue = self.application.job_queue
            job_queue.run_repeating(self.periodic_review_check, interval=3600, first=10)  # Проверка каждый час
            self.logger.info("Запланированы периодические задачи")
        else:
            self.logger.error("Невозможно запланировать задачи: application не инициализирован")

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='wildberries_bot.log',
        filemode='a'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger('').addHandler(console_handler)

    bot = WildberriesBot()
    bot.run()