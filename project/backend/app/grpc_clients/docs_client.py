import grpc
import docssummary_pb2, docssummary_pb2_grpc
import asyncio

class DocsSummaryClient:
    def __init__(self, host="llm-worker-docs", port=50053):
        self.target = f"{host}:{port}"

    async def docssummary_stream(self, chunks: list[str], user_id: str, content_type: str = "default", content_period: str = "none"):
        # 비동기 gRPC 채널 사용
        async with grpc.aio.insecure_channel(self.target) as channel:
            stub = docssummary_pb2_grpc.DocsSummaryServiceStub(channel)
            async def request_iter():
                for chunk in chunks:
                    yield docssummary_pb2.DocsSummaryRequest(
                        user_id=user_id, 
                        chunk=chunk,
                        content_type=content_type,
                        content_period=content_period
                    )
            async for response in stub.SummarizeStream(request_iter()):
                yield response.line