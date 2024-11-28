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

# database_operations.py

def get_today_presences():
    """
    Fetch the list of presences recorded for the current day.
    """
    start_of_day = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1)

    # Query the database for presences between the start and end of the current day
    presences = (
        session.query(Presence)
        .filter(Presence.timestamp >= start_of_day, Presence.timestamp < end_of_day)
        .order_by(Presence.timestamp)
        .all()
    )

    # Return as a list of dictionaries for easier use in templates
    return [{"name": presence.name, "timestamp": presence.timestamp} for presence in presences]

