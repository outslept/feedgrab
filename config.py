import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.MAIN_DOMAIN = "https://www.wildberries.ru"
        self.FEEDBACKS_URL_1 = "https://feedbacks1.wb.ru/feedbacks/v1/"
        self.FEEDBACKS_URL_2 = "https://feedbacks2.wb.ru/feedbacks/v1/"
        self.DATABASE_NAME = "reviews.db"
        self.FEEDBACK_FOLDER = "feedback"
        self.LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.LOG_LEVEL = 'DEBUG'
        self.LOG_FILE = 'wildberries_bot.log'
        
        self.WILDBERRIES_DOMAINS = [
            "www.wildberries.ru",
            "www.wildberries.by",
            "www.wildberries.am",
            "www.wildberries.kg",
            "www.wildberries.uz"
        ]

config = Config()