from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.config.settings import config
from datetime import datetime, timedelta
import logging
import random
import aiohttp

class HTMLParser:
    def __init__(self, rate_limiter):
        self.rate_limiter = rate_limiter
        self.user_agents = config.USER_AGENTS
        
    async def get_product_info(self, article):
        for basket in range(1, 19):
            url = config.BASKET_URL_TEMPLATE.format(basket, article[:-5], article[:-3], article)
            async with aiohttp.ClientSession() as session:
                await self.rate_limiter.wait()
                headers = {'User-Agent': random.choice(self.user_agents)}
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'article': article,
                            'imt_id': data.get('imt_id'),
                            'name': data.get('imt_name'),
                            'brand': data.get('selling', {}).get('brand_name'),
                            'seller_id': data.get('selling', {}).get('supplier_id'),
                            'colors': data.get('colors', []),
                            'sizes': [size['tech_size'] for size in data.get('sizes_table', {}).get('values', [])]
                        }
        return None

    async def parse_reviews(self, product_info):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            reviews_url = f"{config.MAIN_DOMAIN}/catalog/{product_info['article']}/feedbacks"
            try:
                await page.goto(reviews_url)
                
                await self.sort_reviews_by_date(page)
                reviews = await self.scroll_and_parse_reviews(page)
                
                return reviews
            
            except Exception as e:
                logging.error(f"Ошибка при парсинге HTML отзывов: {str(e)}")
            finally:
                await browser.close()
            
            return []

    async def sort_reviews_by_date(self, page):
        sort_button = await page.query_selector('.sorting__mobile--arrow')
        if sort_button:
            button_text = await sort_button.inner_text()
            if 'По дате ↓' not in button_text:
                await sort_button.click()
                await page.wait_for_load_state('networkidle')

    async def scroll_and_parse_reviews(self, page):
        reviews = []
        last_review_count = 0
        
        while True:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)  # Wait for new reviews to load
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            review_items = soup.find_all('li', class_='comments__item')
            
            if len(review_items) == last_review_count:
                break  # No new reviews loaded, exit loop
            
            for item in review_items[last_review_count:]:
                review = self.parse_review_item(item)
                if review:
                    reviews.append(review)
            
            last_review_count = len(review_items)
            
            if len(reviews) >= 1000:  # Limit to 1000 reviews
                break
        
        return reviews

    def parse_review_item(self, item):
        try:
            stars = len(item.find_all('span', class_='star'))
            date_elem = item.find('span', class_='feedback__date')
            date = self.parse_date(date_elem.text.strip()) if date_elem else 'N/A'
            text = item.find('p', class_='feedback__text').text.strip()
            name = item.find('p', class_='feedback__header').text.strip()
            color = item.find('li', class_='feedback__params-item--color')
            color = color.text.strip() if color else None
            size = item.find('li', class_='feedback__params-item--size')
            size = size.text.strip() if size else None
            
            return {
                'date': date,
                'stars': stars,
                'text': text,
                'color': color,
                'size': size,
                'name': name,
                'source': 'html'
            }
        except AttributeError as e:
            logging.warning(f"Ошибка при парсинге HTML отзыва: {str(e)}")
            return None

    def parse_date(self, date_str):
        try:
            if 'Сегодня' in date_str:
                time = datetime.strptime(date_str.split(', ')[1], '%H:%M').time()
                return datetime.combine(datetime.now().date(), time).strftime('%d.%m.%Y')
            elif 'Вчера' in date_str:
                time = datetime.strptime(date_str.split(', ')[1], '%H:%M').time()
                yesterday = datetime.now().date() - timedelta(days=1)
                return datetime.combine(yesterday, time).strftime('%d.%m.%Y')
            else:
                return datetime.strptime(date_str, '%d %B %Y, %H:%M').strftime('%d.%m.%Y')
        except ValueError:
            logging.warning(f"Неверный формат даты: {date_str}")
            return date_str