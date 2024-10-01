import logging
from abc import ABC, abstractmethod

class BaseParser(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def parse_product(self, product_input):
        pass

    @abstractmethod
    async def get_product_info(self, article):
        pass

    @abstractmethod
    async def parse_reviews(self, product_info):
        pass

    @abstractmethod
    async def check_new_reviews(self, article, last_review_date):
        pass
    
    @abstractmethod
    async def parse_multiple_products(self, product_input):
        pass