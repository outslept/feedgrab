from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from src.bot.handlers.command_handlers import CommandHandlers
from src.bot.handlers.message_handlers import MessageHandlers
from src.bot.handlers.callback_handlers import CallbackHandlers
from src.bot.jobs import JobHandlers
from src.parsers.wildberries_parser import WildberriesParser
from src.utils.rate_limiter import RateLimiter
import logging

class WildberriesBot:
    def __init__(self, config, database, scheduler):
        self.config = config
        self.database = database
        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(calls_per_second=self.config.RATE_LIMIT)
        self.parser = WildberriesParser(self.rate_limiter)

    def run(self):
        try:
            command_handlers = CommandHandlers(self.database)
            message_handlers = MessageHandlers(self.database, self.scheduler, self.parser)
            callback_handlers = CallbackHandlers(self.database, self.scheduler, self.parser)
            job_handlers = JobHandlers(self.database, self.scheduler, self.parser)

            application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()

            application.add_handler(CommandHandler("start", command_handlers.start))
            application.add_handler(CommandHandler("menu", command_handlers.menu))
            application.add_handler(CommandHandler("help", command_handlers.help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handlers.handle_input))
            application.add_handler(CallbackQueryHandler(callback_handlers.button_callback))

            job_queue = application.job_queue
            job_queue.run_repeating(job_handlers.periodic_review_check, interval=3600, first=10)

            self.logger.info("Starting the Wildberries bot")
            application.run_polling()
        except Exception as e:
            self.logger.exception("Error running the Wildberries bot")
