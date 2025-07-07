FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./protos /protos

# gRPC Python 파일을 /app/app에 생성 (app/main.py와 같은 위치)
RUN python -m grpc_tools.protoc -I/protos --python_out=/app --grpc_python_out=/app /protos/*.proto

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]