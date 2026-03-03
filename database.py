import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    report_number = Column(String, unique=True, index=True)
    product_model = Column(String)
    laboratory = Column(String)
    test_date = Column(Date)
    overall_result = Column(String)
    ai_summary = Column(Text)
    file_path = Column(String)
    status = Column(String, default='已確認')
    created_at = Column(DateTime, default=datetime.datetime.now)
    metrics = relationship("TestMetric", back_populates="report", cascade="all, delete-orphan")

class TestMetric(Base):
    __tablename__ = 'test_metrics'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'))
    metric_name = Column(String)
    metric_value = Column(String)
    unit = Column(String)
    is_pass = Column(Boolean)
    report = relationship("Report", back_populates="metrics")

# --- 動態資料庫工廠 ---
def get_user_db_engine(user_name):
    """根據使用者名稱產生專屬的資料庫連線"""
    # 確保資料存放目錄存在
    if not os.path.exists("user_data"):
        os.makedirs("user_data")
    
    db_path = f"user_data/{user_name}.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    
    # 自動初始化該用戶的資料表
    Base.metadata.create_all(bind=engine)
    return engine

def get_db_session(user_name):
    engine = get_user_db_engine(user_name)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
