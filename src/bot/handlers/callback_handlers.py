from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

class CallbackHandlers:
    def __init__(self, database, scheduler, parser):
        self.database = database
        self.scheduler = scheduler
        self.parser = parser

    async def button_callback(self, update: Update, context):
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        user_uuid = self.database.get_user_uuid(user_id)

        if query.data == 'get_reviews':
            await query.message.reply_text("🔗 Пожалуйста, отправьте ссылку на товар Wildberries или артикул.")
        elif query.data == 'manage_notifications':
            await self.manage_notifications(update, context, user_uuid)
        elif query.data == 'help':
            await self.help_command(update, context)
        elif query.data == 'menu':
            await self.menu(update, context)
        elif query.data == 'subscribe':
            await self.subscribe(update, context)
        elif query.data == 'unsubscribe':
            await self.unsubscribe(update, context, user_uuid)
        elif query.data == 'list_subscriptions':
            await self.list_subscriptions(update, context, user_uuid)
        elif query.data.startswith('unsub_'):
            product_id = query.data.split('_')[1]
            await self.unsubscribe_product(update, context, user_uuid, product_id)

    async def manage_notifications(self, update: Update, context, user_uuid):
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

    async def unsubscribe(self, update: Update, context, user_uuid):
        query = update.callback_query
        subscriptions = self.database.get_user_subscriptions(user_uuid)
    
        if not subscriptions:
            await query.message.edit_text("У вас нет активных подписок.")
            return

        keyboard = []
        for product_id, product_name in subscriptions:
            keyboard.append([InlineKeyboardButton(f"❌ {product_id} - {product_name[:30]}...", callback_data=f'unsub_{product_id}')])
    
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data='menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Выберите товар для отписки:", reply_markup=reply_markup)

    async def list_subscriptions(self, update: Update, context, user_uuid):
        query = update.callback_query
        subscriptions = self.database.get_user_subscriptions(user_uuid)
    
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

    async def unsubscribe_product(self, update: Update, context, user_uuid, product_id):
        query = update.callback_query
        self.database.unsubscribe_user(user_uuid, product_id)
        self.scheduler.remove_job(user_uuid, product_id)
        product_info = self.database.get_product_info(product_id)
        product_name = product_info['name'] if product_info else product_id
        await query.message.edit_text(f"✅ Вы успешно отписались от товара {product_name} (артикул {product_id})")

    async def menu(self, update: Update, context):
        query = update.callback_query
        keyboard = [
            [InlineKeyboardButton("📊 Получить отзывы", callback_data='get_reviews')],
                        [InlineKeyboardButton("🔔 Управление уведомлениями", callback_data='manage_notifications')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🤖 Главное меню бота отзывов Wildberries! Выберите опцию:", reply_markup=reply_markup)

    async def help_command(self, update: Update, context):
        query = update.callback_query
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
        await query.message.edit_text(help_text, parse_mode='Markdown')
