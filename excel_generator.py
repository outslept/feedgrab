import io
import pandas as pd
from dateutil import parser
import logging

logger = logging.getLogger('excel_generator')

def generate_excel(reviews, product_id):
    try:
        for review in reviews:
            try:
                review['date'] = parser.parse(review['date']).strftime('%d/%m/%Y')
            except ValueError:
                review['date'] = 'Invalid Date'
                logger.warning(f"Неверный формат даты для отзыва товара {product_id}")

        df = pd.DataFrame(reviews)
        
        column_names = {
            'date': ('Дата'),
            'stars': ('Количество звезд'),
            'text': ('Текст отзыва'),
            'name': ('Имя'),
            'color': ('Цвет'),
            'size': ('Размер'),
        }
        
        df = df.rename(columns=column_names)
        df = df[list(column_names.values())]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f"{('Отзывы артикула')} {product_id}")
        output.seek(0)
        
        logger.info(f"Excel-файл для товара {product_id} успешно создан")
        return output, f"reviews_{product_id}.xlsx"
    except Exception as e:
        logger.error(f"Ошибка при создании Excel-файла для товара {product_id}: {str(e)}")
        raise