import aiohttp
import random
from src.config.settings import config
from datetime import datetime
import logging

class JSONParser:
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

    async def parse_reviews(self, imt_id):
        async with aiohttp.ClientSession() as session:
            reviews = []
            page = 1
            
            while True:
                for url in [config.FEEDBACKS_URL_1, config.FEEDBACKS_URL_2]:
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
                                        'date': self.parse_date(feedback.get('createdDate')),
                                        'stars': feedback.get('productValuation'),
                                        'text': feedback.get('text'),
                                        'color': feedback.get('color'),
                                        'size': feedback.get('size'),
                                        'name': feedback.get('wbUserDetails', {}).get('name'),
                                        'source': 'json'
                                    }
                                    reviews.append(review)
                    except aiohttp.ClientError as e:
                        logging.error(f"Ошибка при получении JSON отзывов: {str(e)}")
                        continue
                
                page += 1
                if page > 50:  # Limit to 50 pages
                    break
        
        return reviews

    def parse_date(self, date_str):
        try:
            return datetime.fromisoformat(date_str).strftime('%d.%m.%Y')
        except ValueError:
            logging.warning(f"Неверный формат даты: {date_str}")
            return date_str