from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Presence(Base):  # Change class name and table name
    __tablename__ = 'presence'  # Match the table name in MySQL
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    status = Column(String(10), default='present')  # Status defaults to 'present'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)  # Auto-set time

# MySQL database setup
DATABASE_URI = 'mysql+pymysql://root:@localhost/attendance_system'

engine = create_engine(DATABASE_URI, echo=True)
Base.metadata.create_all(engine)  # Create the table if it doesn't exist
Session = sessionmaker(bind=engine)
session = Session()
