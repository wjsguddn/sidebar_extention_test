FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY ./protos /protos

# gRPC Python 파일을 /app에 생성 (main.py와 같은 위치)
RUN python -m grpc_tools.protoc -I/protos --python_out=/app --grpc_python_out=/app /protos/docssummary.proto
CMD ["python", "-u", "main.py"]


