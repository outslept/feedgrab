import io
import pandas as pd
from dateutil import parser
import logging

class ExcelGenerator:
    def __init__(self):
        self.logger = logging.getLogger('excel_generator')

    def generate_excel(self, reviews, product_info):
        for review in reviews:
            try:
                review['date'] = parser.parse(review['date']).strftime('%d.%m.%Y')
            except ValueError:
                review['date'] = 'Неверная дата'
                self.logger.warning(f"Неверный формат даты для отзыва товара {product_info['article']}")

        df = pd.DataFrame(reviews)
        
        column_names = {
            'date': 'Дата',
            'stars': 'Количество звезд',
            'text': 'Текст отзыва',
            'name': 'Имя',
            'color': 'Цвет',
            'size': 'Размер'
        }
        
        df = df.rename(columns=column_names)
        df = df[list(column_names.values())]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f"Отзывы для артикула {product_info['article']}")
            
            product_df = pd.DataFrame([{
                'Артикул': product_info['article'],
                'IMT ID': product_info['imt_id'],
                'Название': product_info['name'],
                'Бренд': product_info['brand'],
                'ID продавца': product_info['seller_id']
            }])
            product_df.to_excel(writer, index=False, sheet_name='Информация о товаре')
            
        output.seek(0)
        
        self.logger.info(f"Excel файл для товара {product_info['article']} успешно создан")
        return output, f"отзывы_{product_info['article']}.xlsx"