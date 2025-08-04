from app.db import engine, Base
from app.models import User, RefreshToken, UserModeStats

def create_tables():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)
    print("테이블이 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    create_tables() 