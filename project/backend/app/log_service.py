import uuid
import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from .models import UserModeStats, ModeType
from .db import get_db


class DelayTracker:
    def __init__(self):
        self.request_start_time = None
        self.first_token_time = None
        self.last_mini_summary_time = None
        self.stream_end_time = None
        self.final_end_time = None

    def start_request(self):
        self.request_start_time = time.time()

    def first_token_received(self):
        self.first_token_time = time.time()

    def last_mini_summary_received(self):
        self.last_mini_summary_time = time.time()

    def stream_ended(self):
        self.stream_end_time = time.time()

    def final_processing_ended(self):
        self.final_end_time = time.time()

    def get_delays(self):
        if not self.request_start_time or not self.first_token_time:
            return None

        first_token_delay = int((self.first_token_time - self.request_start_time) * 1000)

        if self.last_mini_summary_time:  # document 모드
            stream_duration = int((self.last_mini_summary_time - self.first_token_time) * 1000)
            final_processing = int(
                (self.final_end_time - self.last_mini_summary_time) * 1000) if self.final_end_time else 0
        else:  # browser, youtube 모드
            # stream_end_time이 None일 수 있으므로 안전하게 처리
            if self.stream_end_time:
                stream_duration = int((self.stream_end_time - self.first_token_time) * 1000)
            else:
                stream_duration = 0  # None 대신 0으로 설정
            final_processing = 0

        return {
            'first_token_delay_ms': first_token_delay,
            'stream_duration_ms': stream_duration,
            'final_processing_ms': final_processing
        }


class LogService:
    def __init__(self):
        self.delay_trackers = {}

    def start_request_log(self, user_id: str, mode_type: ModeType) -> str:
        # 요청 시작 시 로그 초기화
        request_id = str(uuid.uuid4())
        self.delay_trackers[request_id] = DelayTracker()
        self.delay_trackers[request_id].start_request()
        return request_id

    def first_token_received(self, request_id: str):
        # 첫 토큰 수신 시 호출
        if request_id in self.delay_trackers:
            self.delay_trackers[request_id].first_token_received()

    def last_mini_summary_received(self, request_id: str):
        # 마지막 미니 서머리 수신 시 호출 (document 모드)
        if request_id in self.delay_trackers:
            self.delay_trackers[request_id].last_mini_summary_received()

    def stream_ended(self, request_id: str):
        # 스트림 종료 시 호출
        if request_id in self.delay_trackers:
            self.delay_trackers[request_id].stream_ended()

    def final_processing_ended(self, request_id: str):
        # 최종 처리 완료 시 호출 (document 모드)
        if request_id in self.delay_trackers:
            self.delay_trackers[request_id].final_processing_ended()

    async def complete_request_log(self, request_id: str, user_id: str, mode_type: ModeType,
                                   request_tokens: int = 0, response_tokens: int = 0):
        print(f"[LOG] complete_request_log 호출됨: request_id={request_id}, user_id={user_id}, mode_type={mode_type}")

        # 요청 완료 시 로그 저장
        if request_id not in self.delay_trackers:
            print(f"[LOG] request_id {request_id}가 delay_trackers에 없음")
            return

        tracker = self.delay_trackers.pop(request_id)
        delays = tracker.get_delays()
        print(f"[LOG] delays: {delays}")

        if not delays:
            print(f"[LOG] delays가 None이거나 비어있음")
            return

        # DB에 저장
        db = next(get_db())
        try:
            print(f"[LOG] DB 쿼리 시작: user_id={user_id}, mode_type={mode_type}")
            stats = db.query(UserModeStats).filter(
                UserModeStats.user_id == user_id,
                UserModeStats.mode_type == mode_type
            ).first()

            if not stats:
                print(f"[LOG] 새 stats 행 생성")
                stats = UserModeStats(
                    user_id=user_id,
                    mode_type=mode_type
                )
                db.add(stats)
            else:
                print(f"[LOG] 기존 stats 행 업데이트")

            # 안전한 통계 업데이트
            stats.request_count = (stats.request_count or 0) + 1
            stats.total_request_tokens = (stats.total_request_tokens or 0) + request_tokens
            stats.total_response_tokens = (stats.total_response_tokens or 0) + response_tokens
            stats.total_first_token_delay_ms = (stats.total_first_token_delay_ms or 0) + delays['first_token_delay_ms']
            stats.total_stream_duration_ms = (stats.total_stream_duration_ms or 0) + delays['stream_duration_ms']
            stats.total_final_processing_ms = (stats.total_final_processing_ms or 0) + delays['final_processing_ms']

            print(f"[LOG] 통계 업데이트 완료: request_count={stats.request_count}")
            db.commit()
            print(f"[LOG] DB 커밋 성공")

        except Exception as e:
            db.rollback()
            print(f"[LOG] 로그 저장 실패: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()


# 전역 인스턴스
log_service = LogService()