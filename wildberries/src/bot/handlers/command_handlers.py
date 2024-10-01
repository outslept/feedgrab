from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import uuid

class CommandHandlers:
    def __init__(self, database):
        self.database = database

    async def start(self, update: Update, context):
        user_id = update.effective_user.id
        user_uuid = self.database.get_user_uuid(user_id)
        if not user_uuid:
            user_uuid = str(uuid.uuid4())
            self.database.add_user(user_id, user_uuid)
        
        welcome_message = f"🤖 Добро пожаловать в бот отзывов Wildberries!\n\nВаш уникальный идентификатор: {user_uuid[:8]}..."
        await update.message.reply_text(welcome_message)
        await self.menu(update, context)

    async def menu(self, update: Update, context):
        keyboard = [
            [InlineKeyboardButton("📊 Получить отзывы", callback_data='get_reviews')],
            [InlineKeyboardButton("🔔 Управление уведомлениями", callback_data='manage_notifications')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "Выберите опцию:"
        if update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context):
        help_text = """
🤖 *Помощь бота отзывов Wildberries*

Доступные команды:

🏁 /start - Запустить бота и показать главное меню
🏠 /menu - Показать главное меню
❓ /help - Показать это сообщение помощи

📊 Получить отзывы - Отправьте ссылку на товар или артикул для получения отзывов
🔔 Управление уведомлениями - Подписаться или отписаться от уведомлений о новых отзывах

Вы можете отправить:
1. Артикул товара (только цифры, минимум 6 знаков)
2. Ссылку на товар с Wildberries

Для получения отзывов по нескольким товарам сразу, отправьте список артикулов в формате: [артикул1, артикул2, ...]

По любым вопросам или для обратной связи, пожалуйста, свяжитесь с @destroy2create.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')