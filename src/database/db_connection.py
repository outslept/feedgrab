from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

Base = declarative_base()

class DatabaseConnection:
    def __init__(self, database_name):
        self.database_name = database_name
        self.engine = create_engine(f'sqlite:///{database_name}')
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger('database')

    def init_db(self):
        Base.metadata.create_all(self.engine)
        self.logger.info("База данных инициализирована")

    def get_session(self):
        return self.Session()
    