import grpc
import docssummary_pb2, docssummary_pb2_grpc
import asyncio

class DocsSummaryClient:
    def __init__(self, host="llm-worker-docs", port=5002):
        self.target = f"{host}:{port}"

    async def docssummary_stream(self, user_id: str, chunks: list[str]):
        # 비동기 gRPC 채널 사용
        async with grpc.aio.insecure_channel(self.target) as channel:
            stub = docssummary_pb2_grpc.DocsSummaryServiceStub(channel)
            async def request_iter():
                for chunk in chunks:
                    yield docssummary_pb2.DocsSummaryRequest(user_id=user_id, chunk=chunk)
            async for response in stub.SummarizeStream(request_iter()):
                yield response.line