from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN
from wildberries_parser import parse_multiple_products
from excel_generator import generate_excel
from database import init_db, get_reviews, save_reviews, get_all_products
from datetime import datetime, timedelta
from dateutil import parser
import logging

logger = logging.getLogger('telegram_bot')

PRODUCTS_PER_PAGE = 10

async def menu(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📊 Получить отзывы", callback_data='get_reviews')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    
    products = get_all_products()
    if products:
        keyboard.append([InlineKeyboardButton("📋 Список продуктов", callback_data='list_products_0')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("🤖 Добро пожаловать в бот отзывов Wildberries! Пожалуйста, выберите опцию:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("🤖 Добро пожаловать в бот отзывов Wildberries! Пожалуйста, выберите опцию:", reply_markup=reply_markup)

async def list_products(update: Update, context, page=0):
    products = get_all_products()
    start = page * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    current_products = products[start:end]
    
    keyboard = [[InlineKeyboardButton(f"🏷️ {product}", callback_data=f'show_product_{product}')] for product in current_products]
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f'list_products_{page-1}'))
    if end < len(products):
        nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f'list_products_{page+1}'))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data='menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text("📋 Список продуктов:", reply_markup=reply_markup)

async def show_product(update: Update, context, product_id):
    reviews, _ = get_reviews(product_id)
    if reviews:
        excel_file, filename = generate_excel(reviews, product_id)
        await update.callback_query.message.reply_document(
            document=excel_file, 
            filename=filename,
            caption=f"📊 Отзывы для артикула {product_id}"
        )
    else:
        await update.callback_query.message.reply_text("❌ Отзывов для этого товара не найдено.")

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_reviews':
        await query.message.reply_text("🔗 Пожалуйста, отправьте ссылку на товар Wildberries или артикул.")
    elif query.data == 'help':
        help_text = """
        🤖 *Помощь бота отзывов Wildberries*

        Вот доступные команды:

        🏁 /start - Запустить бота и показать главное меню
        🏠 /menu - Показать главное меню
        ❓ /help - Показать это сообщение помощи

        Вы также можете отправить ссылку на товар Wildberries или артикул напрямую, чтобы получить отзывы.

        По любым вопросам или для обратной связи, пожалуйста, свяжитесь с @destroy2create.
        """
        await query.message.reply_text(help_text, parse_mode='Markdown')
    elif query.data.startswith('list_products_'):
        page = int(query.data.split('_')[-1])
        await list_products(update, context, page)
    elif query.data.startswith('show_product_'):
        product_id = query.data.split('_')[-1]
        await show_product(update, context, product_id)
    elif query.data == 'menu':
        await menu(update, context)

async def handle_input(update: Update, context):
    user_input = update.message.text.strip()
    if user_input.startswith('[') and user_input.endswith(']') or user_input.startswith('http') or user_input.isdigit():
        await process_review_request(update, context, user_input)
    else:
        await menu(update, context)

async def process_review_request(update: Update, context, user_input):
    await update.message.reply_text("⏳ Обрабатываем ваш запрос. Пожалуйста, подождите...")

    try:
        results = await parse_multiple_products(user_input)
        
        for product_input, reviews in results:
            product_id = product_input.split('/')[-2] if '/' in product_input else product_input
            
            if reviews:
                save_reviews(product_id, reviews, datetime.now().isoformat())
                excel_file, filename = generate_excel(reviews, product_id)
                await update.message.reply_document(
                    document=excel_file, 
                    filename=filename,
                    caption=f"📊 Отзывы для артикула {product_id}"
                )
            else:
                await update.message.reply_text(f"❌ Отзывов для товара {product_id} не найдено или произошла ошибка при обработке.")
        
        if len(results) > 1:
            await update.message.reply_text("✅ Обработка всех запрошенных товаров завершена.")
    
    except Exception as e:
        error_message = f"❗ Произошла ошибка: {str(e)}"
        logger.error(error_message)
        await update.message.reply_text(error_message)

async def help_command(update: Update, context):
    help_text = """
🤖 *Помощь бота отзывов Wildberries*

Вот доступные команды:

🏁 /start - Запустить бота и показать главное меню
🏠 /menu - Показать главное меню
❓ /help - Показать это сообщение помощи

Вы также можете отправить ссылку на товар Wildberries или артикул напрямую, чтобы получить отзывы.

По любым вопросам или для обратной связи, пожалуйста, свяжитесь с @destroy2create.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def start(update: Update, context):
    await menu(update, context)

def main():
    init_db()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Бот запущен")
    application.run_polling()

if __name__ == '__main__':
    main()