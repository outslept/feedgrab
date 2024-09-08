import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = "https://www.wildberries.ru"
FEEDBACKS_URL_1 = "https://feedbacks1.wb.ru/feedbacks/v1/"
FEEDBACKS_URL_2 = "https://feedbacks2.wb.ru/feedbacks/v1/"
DATABASE_NAME = "reviews.db"
FEEDBACK_FOLDER = "feedback"

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'wildberries_bot.log'