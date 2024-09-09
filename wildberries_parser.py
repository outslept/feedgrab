import re
import aiohttp
import asyncio
from playwright.async_api import async_playwright
from config import Config
from bs4 import BeautifulSoup
import logging
import time
import random
from cachetools import TTLCache

class RateLimiter:
    def __init__(self, calls_per_second):
        self.calls_per_second = calls_per_second
        self.last_call = 0

    async def wait(self):
        current_time = time.time()
        time_since_last_call = current_time - self.last_call
        if time_since_last_call < 1 / self.calls_per_second:
            await asyncio.sleep(1 / self.calls_per_second - time_since_last_call)
        self.last_call = time.time()

class Parser:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('wildberries_parser')
        self.rate_limiter = RateLimiter(2000)
        self.cache = TTLCache(maxsize=1000, ttl=3600)  # Cache with 1-hour TTL
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
        ]

    def extract_article_from_url(self, url):
        match = re.search(r'/(\d+)/detail\.aspx', url) or re.search(r'/catalog/(\d+)/', url)
        return match.group(1) if match else None

    async def parse_multiple_products(self, user_input):
        inputs = user_input.strip('[]').split(',') if user_input.startswith('[') else [user_input]
        tasks = [self.parse_single_product(product_input.strip()) for product_input in inputs]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result]

    async def parse_single_product(self, product_input):
        article = self.extract_article_from_url(product_input) if product_input.startswith('http') else product_input

        if article:
            product_info = await self.get_product_info(article)
            if product_info:
                reviews = await self.parse_product(product_info)
                return (article, reviews)
            else:
                self.logger.error(f"Не удалось получить информацию о товаре: {article}")
        else:
            self.logger.error(f"Не удалось извлечь артикул из: {product_input}")
        return None

    async def get_product_info(self, article):
        cache_key = f"product_info_{article}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        for basket in range(1, 19):
            url = f"https://basket-{basket:02d}.wbbasket.ru/vol{int(article) // 100000}/part{int(article) // 1000}/{article}/info/ru/card.json"
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                headers = {'User-Agent': random.choice(self.user_agents)}
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        product_info = {
                            'article': article,
                            'imt_id': data.get('imt_id'),
                            'name': data.get('imt_name'),
                            'brand': data.get('selling', {}).get('brand_name'),
                            'seller_id': data.get('selling', {}).get('supplier_id'),
                            'colors': data.get('colors', []),
                            'sizes': [size['tech_size'] for size in data.get('sizes_table', {}).get('values', [])]
                        }
                        self.cache[cache_key] = product_info
                        return product_info
        
        self.logger.error(f"Не удалось получить информацию о товаре: {article}")
        return None

    async def parse_product(self, product_info):
        imt_id = product_info['imt_id']
        
        json_reviews = await self.parse_json_reviews(imt_id)
        html_reviews = await self.parse_html_reviews(product_info)
        
        combined_reviews = self.combine_reviews(json_reviews, html_reviews)
        
        return combined_reviews
    
    async def parse_json_reviews(self, imt_id):
        async with aiohttp.ClientSession() as session:
            reviews = []
            page = 1
            
            while True:
                for url in [self.config.FEEDBACKS_URL_1, self.config.FEEDBACKS_URL_2]:
                    full_url = f"{url}{imt_id}?page={page}&take=99"
                    await self.rate_limiter.wait()
                    headers = {'User-Agent': random.choice(self.user_agents)}
                    try:
                        async with session.get(full_url, headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                feedbacks = data.get('feedbacks', [])
                                if not feedbacks:
                                    return reviews
                                
                                for feedback in feedbacks:
                                    review = {
                                        'date': feedback.get('createdDate'),
                                        'stars': feedback.get('productValuation'),
                                        'text': feedback.get('text'),
                                        'color': feedback.get('color'),
                                        'size': feedback.get('size'),
                                        'name': feedback.get('wbUserDetails', {}).get('name'),
                                        'source': 'json'
                                    }
                                    reviews.append(review)
                    except aiohttp.ClientError as e:
                        self.logger.error(f"Ошибка при получении JSON-отзывов: {str(e)}")
                        continue
                
                page += 1
                if page > 50:  # Ограничение на количество страниц
                    break
        
        return reviews

    async def parse_html_reviews(self, product_info):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            reviews_url = f"{self.config.MAIN_DOMAIN}/catalog/{product_info['article']}/feedbacks"
            try:
                await page.goto(reviews_url)
                
                # Проверяем сортировку
                sort_button = await page.query_selector('.sorting__mobile--arrow')
                if sort_button:
                    button_text = await sort_button.inner_text()
                    if 'По дате ↓' not in button_text:
                        await sort_button.click()
                        await page.wait_for_load_state('networkidle')
                
                reviews = []
                last_review_count = 0
                
                while True:
                    # Прокручиваем страницу вниз для загрузки новых отзывов
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)  # Ждем загрузки новых отзывов
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    review_items = soup.find_all('li', class_='comments__item')
                    
                    if len(review_items) == last_review_count:
                        break  # Если новых отзывов нет, прекращаем загрузку
                    
                    for item in review_items[last_review_count:]:
                        try:
                            stars = len(item.find_all('span', class_='star'))
                            date = item.find('span', class_='feedback__date').text.strip()
                            text = item.find('p', class_='feedback__text').text.strip()
                            name = item.find('p', class_='feedback__header').text.strip()
                            color = item.find('li', class_='feedback__params-item--color')
                            color = color.text.strip() if color else None
                            size = item.find('li', class_='feedback__params-item--size')
                            size = size.text.strip() if size else None
                            
                            review = {
                                'date': date,
                                'stars': stars,
                                'text': text,
                                'color': color,
                                'size': size,
                                'name': name,
                                'source': 'html'
                            }
                            reviews.append(review)
                        except AttributeError as e:
                            self.logger.error(f"Ошибка при парсинге HTML-отзыва: {str(e)}")
                    
                    last_review_count = len(review_items)
                    
                    if len(reviews) >= 1000:  # Ограничение на количество отзывов
                        break
            
            except Exception as e:
                self.logger.error(f"Ошибка при парсинге HTML-отзывов: {str(e)}")
            finally:
                await browser.close()
            
            return reviews

    def combine_reviews(self, json_reviews, html_reviews):
        combined = json_reviews.copy()
        
        for html_review in html_reviews:
            if not any(self.reviews_match(html_review, json_review) for json_review in json_reviews):
                combined.append(html_review)
        
        return combined

    def reviews_match(self, review1, review2):
        return (review1['date'] == review2['date'] and
                review1['stars'] == review2['stars'] and
                review1['name'] == review2['name'] and
                review1['text'] == review2['text'])

    def get_image_links(self, product_id, pics_count):
        basket = f"{(product_id // 100000 % 18) + 1:02d}"
        short_id = product_id // 100000
        return [
            f"https://basket-{basket}.wb.ru/vol{short_id}/part{product_id // 1000}/{product_id}/images/big/{i}.jpg"
            for i in range(1, pics_count + 1)
        ]
        
    def combine_reviews(self, json_reviews, html_reviews):
        combined = json_reviews + html_reviews
        combined.sort(key=lambda x: x['date'], reverse=True)  # Сортировка по убыванию даты
        return combined
    
    async def check_new_reviews(self, article, last_review_date):
        product_info = await self.get_product_info(article)
        if not product_info:
            return None

        reviews = await self.parse_product(product_info)
        new_reviews = [review for review in reviews if review['date'] > last_review_date]
        return new_reviews