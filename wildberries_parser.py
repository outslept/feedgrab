import re
import aiohttp
import asyncio
from playwright.async_api import async_playwright
from config import BASE_URL, FEEDBACKS_URL_1, FEEDBACKS_URL_2
from tqdm import tqdm
import logging
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='wildberries_parser.log',
    filemode='a'
)
logger = logging.getLogger('wildberries_parser')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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

rate_limiter = RateLimiter(2000)

async def extract_imt_id(page):
    reviews_link = await page.query_selector('.product-page__reviews')
    if reviews_link:
        href = await reviews_link.get_attribute('href')
        match = re.search(r'imtId=(\d+)', href)
        if match:
            return match.group(1)
    logger.warning("Не удалось извлечь imt_id")
    return None

async def get_valid_feedback_url(imt_id):
    async with aiohttp.ClientSession() as session:
        for url in [FEEDBACKS_URL_1, FEEDBACKS_URL_2]:
            full_url = f"{url}{imt_id}"
            await rate_limiter.wait()
            async with session.get(full_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('feedbacks'):
                        return full_url
    logger.error(f"Не удалось найти действительный URL для отзывов с imt_id: {imt_id}")
    return None

async def parse_reviews(feedback_url):
    async with aiohttp.ClientSession() as session:
        reviews = []
        page = 1
        total_reviews = None
        
        with tqdm(desc="Собираем отзывы", unit=" отзыв") as pbar:
            while True:
                url = f"{feedback_url}?page={page}&take=99"
                await rate_limiter.wait()
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка при запросе отзывов: статус {response.status}")
                        break
                    data = await response.json()
                    feedbacks = data.get('feedbacks', [])
                    
                    if total_reviews is None:
                        total_reviews = data.get('totalCount', 0)
                        pbar.total = total_reviews
                    
                    if not feedbacks:
                        break
                    
                    for feedback in feedbacks:
                        review = {
                            'date': feedback.get('createdDate'),
                            'stars': feedback.get('productValuation'),
                            'text': feedback.get('text'),
                            'color': feedback.get('color'),
                            'size': feedback.get('size'),
                            'name': feedback.get('wbUserDetails', {}).get('name')
                        }
                        reviews.append(review)
                        pbar.update(1)
                    
                    if len(reviews) >= total_reviews:
                        break
                
                page += 1
        
        logger.info(f"Собрано {len(reviews)} отзывов")
        return reviews

async def parse_product_reviews(user_input):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        if user_input.isdigit():
            url = f"{BASE_URL}/catalog/{user_input}/detail.aspx"
        elif user_input.startswith(BASE_URL):
            url = user_input
        else:
            logger.error(f"Неверный формат ввода: {user_input}")
            raise ValueError("Неверный ввод. Пожалуйста, укажите действительный номер артикула или URL-адрес Wildberries.")

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            imt_id = await extract_imt_id(page)
        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы продукта {user_input}: {str(e)}")
            raise
        finally:
            await browser.close()

        if not imt_id:
            logger.error(f"Не удалось извлечь идентификатор IMT для {user_input}")
            raise ValueError("Не удалось извлечь идентификатор IMT со страницы продукта.")

        feedback_url = await get_valid_feedback_url(imt_id)
        if not feedback_url:
            logger.error(f"Не удалось найти действительный URL для отзывов продукта {user_input}")
            raise ValueError("Не удалось найти действительный URL-адрес обратной связи для этого продукта.")

        reviews = await parse_reviews(feedback_url)
        
        return user_input, reviews

async def parse_multiple_products(user_input):
    if user_input.startswith('[') and user_input.endswith(']'):
        input_list = [item.strip() for item in user_input[1:-1].split(',')]
    else:
        input_list = [user_input]

    results = []
    for item in input_list:
        try:
            logger.info(f"Начало обработки продукта: {item}")
            result = await parse_product_reviews(item)
            results.append(result)
            logger.info(f"Продукт {item} успешно обработан")
        except Exception as e:
            logger.error(f"Ошибка при обработке {item}: {str(e)}")
            results.append((item, None)) 

    return results