
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import OperationalError
import datetime

# --- CONFIGURATION ---
DB_USER = "postgres"
DB_PASS = "password123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "azdDB"

# --- DATABASE SETUP ---
# We first connect to the default 'postgres' db to check/create our target db
DEFAULT_DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
TARGET_DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()

# --- MODELS ---
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False) # In real app, hash this!
    full_name = Column(String(100))
    specialty = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    patient_name = Column(String(100))
    age = Column(String(10))
    gender = Column(String(20))
    phone = Column(String(20))
    medical_history = Column(Text)
    
    prediction = Column(String(50))
    confidence = Column(String(10))
    created_by_user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Store images as BLOBs (Binary Large Objects)
    original_image = Column(LargeBinary)
    heatmap_image = Column(LargeBinary)

    creator = relationship("User")

def init_db():
    print("Initialize Database...")
    # 1. Create Database if not exists
    engine = create_engine(DEFAULT_DB_URL, isolation_level='AUTOCOMMIT')
    try:
        with engine.connect() as conn:
            # Check if db exists
            result = conn.execute(sqlalchemy.text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'"))
            if not result.fetchone():
                print(f"Creating database {DB_NAME}...")
                conn.execute(sqlalchemy.text(f"CREATE DATABASE \"{DB_NAME}\""))
            else:
                print(f"Database {DB_NAME} already exists.")
    except Exception as e:
        print(f"Database creation warning (might already exist or connection failed): {e}")

    # 2. Create Tables
    engine = create_engine(TARGET_DB_URL)
    Base.metadata.create_all(engine)
    print("Tables created/verified.")
    
    return sessionmaker(bind=engine)

if __name__ == "__main__":
    init_db()
