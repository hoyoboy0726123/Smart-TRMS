import datetime
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
    overall_result = Column(String) # Pass / Fail
    ai_summary = Column(Text)
    file_path = Column(String)
    status = Column(String, default='待審核') # 待審核, 已確認, 已作廢
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    metrics = relationship("TestMetric", back_populates="report", cascade="all, delete-orphan")

class TestMetric(Base):
    __tablename__ = 'test_metrics'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'))
    metric_name = Column(String)
    metric_value = Column(String) # 改為 String 以支援範圍值 (如: 16 to 3000)
    unit = Column(String)
    is_pass = Column(Boolean)
    
    report = relationship("Report", back_populates="metrics")

# 資料庫連線設定
DATABASE_URL = "sqlite:///trms.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
