from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database.db_connection import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    uuid = Column(String, unique=True)

class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    product_id = Column(String, ForeignKey('product_info.product_id'))
    review_data = Column(Text)
    last_updated = Column(String)

    __table_args__ = (Index('idx_reviews_product_id', 'product_id'),)

class ProductInfo(Base):
    __tablename__ = 'product_info'

    product_id = Column(String, primary_key=True)
    imt_id = Column(String)
    name = Column(String)
    brand = Column(String)
    seller_id = Column(String)

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_uuid = Column(String, ForeignKey('users.uuid'))
    product_id = Column(String, ForeignKey('product_info.product_id'))
    last_check_time = Column(String)

    __table_args__ = (Index('idx_subscriptions_user_uuid', 'user_uuid'),)