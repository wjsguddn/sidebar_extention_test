from sqlalchemy import Column, String, Integer, DateTime, Enum
from sqlalchemy.sql import func
from .db import Base
import enum

class ModeType(enum.Enum):
    DOCUMENT = "document"
    BROWSER = "browser"
    YOUTUBE = "youtube"

class User(Base):
    __tablename__ = "users"
    id = Column(String(128), primary_key=True)  # 구글 sub
    email = Column(String(256), unique=True, index=True)
    name = Column(String(128))
    picture = Column(String(512))


class UserModeStats(Base):
    __tablename__ = "user_mode_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False)
    mode_type = Column(Enum(ModeType), nullable=False)

    # 카운트 관련
    request_count = Column(Integer, default=0)

    # 토큰 관련
    total_request_tokens = Column(Integer, default=0)
    total_response_tokens = Column(Integer, default=0)

    # 딜레이 관련 (누적값)
    total_first_token_delay_ms = Column(Integer, default=0)  # 첫 토큰 도착까지
    total_stream_duration_ms = Column(Integer, default=0)  # 스트림 지속 시간
    total_final_processing_ms = Column(Integer, default=0)  # 최종 처리 시간 (document만)

    # 타임스탬프
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())