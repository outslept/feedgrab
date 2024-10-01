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
            "www.wildberries.by",
            "www.wildberries.am",
            "www.wildberries.kg",
            "www.wildberries.uz"
        ]
        self.BASKET_URL_TEMPLATE = "https://basket-{:02d}.wbbasket.ru/vol{}/part{}/{}/info/ru/card.json"
        self.RATE_LIMIT = 3
        self.RATE_LIMIT_PERIOD = 1
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 5
        self.PROXY_SOURCES = [
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http"
        ]
        self.PROXY_TIMEOUT = 10
        self.USER_AGENTS = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
        ]

config = Config()