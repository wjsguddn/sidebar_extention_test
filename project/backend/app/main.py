from fastapi import FastAPI
from .db import SessionLocal, Base, engine
from .collect_browser_router import collect_browser_router
from .auth_google_router import auth_google_router
from .result_consumer import start_result_consumer
from .websocket_router import router as websocket_router
from .models import User

#테이블이 없으면 생성, 있으면 무시 (개발환경에서만 사용 권장)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(collect_browser_router)
app.include_router(auth_google_router)
app.include_router(websocket_router)

@app.on_event("startup")
def startup_event():
    start_result_consumer()
