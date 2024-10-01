from src.models.models import ProductInfo
from sqlalchemy.exc import SQLAlchemyError

class ProductManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def save_product_info(self, product_info):
        session = self.db.get_session()
        try:
            product = ProductInfo(
                product_id=product_info['article'],
                imt_id=product_info['imt_id'],
                name=product_info['name'],
                brand=product_info['brand'],
                seller_id=product_info['seller_id']
            )
            session.merge(product)
            session.commit()
            self.db.logger.info(f"Информация о товаре {product_info['article']} успешно сохранена")
        except SQLAlchemyError as e:
            session.rollback()
            self.db.logger.error(f"Ошибка сохранения информации о товаре {product_info['article']}: {str(e)}")
        finally:
            session.close()

    def get_product_info(self, product_id):
        session = self.db.get_session()
        try:
            product = session.query(ProductInfo).filter_by(product_id=product_id).first()
            if product:
                return {
                    'article': product.product_id,
                    'imt_id': product.imt_id,
                    'name': product.name,
                    'brand': product.brand,
                    'seller_id': product.seller_id
                }
        except SQLAlchemyError as e:
            self.db.logger.error(f"Ошибка получения информации о товаре {product_id}: {str(e)}")
        finally:
            session.close()
        return None