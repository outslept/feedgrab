import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import re
from src.parsers.json_parser import JSONParser
from src.parsers.html_parser import HTMLParser

class WildberriesParser:
    def __init__(self, rate_limiter):
        self.rate_limiter = rate_limiter
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.json_parser = JSONParser(rate_limiter)
        self.html_parser = HTMLParser(rate_limiter)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def parse_product(self, product_input):
        try:
            article = self.extract_article_from_url(product_input) if product_input.startswith('http') else product_input
            if not article:
                raise ValueError("Invalid input: unable to extract article number")

            product_info = await self.get_product_info(article)
            if not product_info:
                self.logger.warning(f"Product info not found for article: {article}")
                return None

            reviews = await self.parse_reviews(product_info)
            return product_info, reviews
        except Exception as e:
            self.logger.exception(f"Error parsing product: {product_input}")
            raise

    def extract_article_from_url(self, url):
        patterns = [
            r'https?://[^/]+/catalog/(\d+)/detail\.aspx',
            r'https?://[^/]+/product/[^/]+/(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def get_product_info(self, article):
        try:
            return await self.json_parser.get_product_info(article)
        except Exception as e:
            self.logger.exception(f"Error getting product info for article: {article}")
            return None

    async def parse_reviews(self, product_info):
        try:
            json_reviews = await self.json_parser.parse_reviews(product_info['imt_id'])
            if not json_reviews:
                self.logger.info(f"No JSON reviews found for article: {product_info['article']}. Falling back to HTML parsing.")
                html_reviews = await self.html_parser.parse_reviews(product_info)
                return html_reviews
            return json_reviews
        except Exception as e:
            self.logger.exception(f"Error parsing reviews for article: {product_info['article']}")
            return []

    async def check_new_reviews(self, article, last_review_date):
        try:
            product_info = await self.get_product_info(article)
            if not product_info:
                self.logger.warning(f"Product info not found for article: {article}")
                return None

            all_reviews = await self.parse_reviews(product_info)
            new_reviews = [review for review in all_reviews if self.is_newer_date(review['date'], last_review_date)]
            return new_reviews
        except Exception as e:
            self.logger.exception(f"Error checking new reviews for article: {article}")
            return None

    def is_newer_date(self, review_date, last_review_date):
        try:
            review_date = datetime.strptime(review_date, '%d.%m.%Y')
            last_review_date = datetime.strptime(last_review_date, '%d.%m.%Y')
            return review_date > last_review_date
        except ValueError:
            self.logger.warning(f"Invalid date format: review_date={review_date}, last_review_date={last_review_date}")
            return False

    async def parse_multiple_products(self, product_inputs):
        results = []
        for product_input in product_inputs:
            try:
                product_info, reviews = await self.parse_product(product_input)
                if product_info and reviews:
                    results.append((product_info, reviews))
                else:
                    self.logger.warning(f"No data found for product: {product_input}")
            except Exception as e:
                self.logger.exception(f"Error parsing product: {product_input}")
        return results
