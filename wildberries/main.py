import logging
from logging.handlers import RotatingFileHandler
from src.bot.bot import WildberriesBot
from src.config.settings import Config
from src.database import Database
from src.utils.scheduler import Scheduler

def setup_logging():
    config = Config()
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set levels for third-party loggers
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Wildberries bot")
    
    try:
        config = Config()
        database = Database()
        database.init_db()
        
        scheduler = Scheduler(database)
        scheduler.start()
        
        bot = WildberriesBot(config, database, scheduler)
        bot.run()
    except Exception as e:
        logger.exception("Fatal error in main loop")

if __name__ == '__main__':
    main()
