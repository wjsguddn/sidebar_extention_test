import grpc
import recommendation_pb2, recommendation_pb2_grpc


class RecClient:
    def __init__(self, host="llm-worker-rec", port=50051):
        self.target = f"{host}:{port}"

    async def recommend_stream(self, user_id: str, browser_context: str, content_type: str = "default", content_period: str = "none"):
        # 비동기 gRPC 채널 사용
        async with grpc.aio.insecure_channel(self.target) as channel:
            stub = recommendation_pb2_grpc.RecommendationServiceStub(channel)
            request = recommendation_pb2.RecommendRequest(
                user_id=user_id,
                browser_context=browser_context,
                content_type=content_type,
                content_period=content_period
            )
            # stream 응답을 async generator로 반환
            async for response in stub.Recommend(request):
                yield response