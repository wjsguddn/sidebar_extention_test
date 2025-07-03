from fastapi import FastAPI
from .db import SessionLocal, Base, engine
from .collect_browser_router import collect_browser_router
from .auth_google_router import auth_google_router
from .models import User

#테이블이 없으면 생성, 있으면 무시 (개발환경에서만 사용 권장)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(collect_browser_router)
app.include_router(auth_google_router)


@app.get("/recommend")
async def recommend(url: str):
    """URL 1개에 대한 추천 결과 임시 모킹"""
    return {"url": url, "recommend": ["추천 A", "추천 B", "추천 C", "추천 D", "추천 E"]}
