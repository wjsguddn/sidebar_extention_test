import grpc
from concurrent import futures
import asyncio
import docssummary_pb2
import docssummary_pb2_grpc

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained("google/mt5-small")
model = AutoModelForSeq2SeqLM.from_pretrained("google/mt5-small")

def summarize_mt5(text, max_length=100):
    # 최대 512토큰(=약 1500자)까지만 모델에 들어감(더 길면 잘림)
    input_ids = tokenizer.encode(text, return_tensors="pt", truncation=True, max_length=512)
    # 최대 100토큰(=1~2줄)로 요약
    summary_ids = model.generate(input_ids, max_length=max_length, num_beams=4, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)



class DocsSummaryService(docssummary_pb2_grpc.DocsSummaryServiceServicer):
    async def SummarizeStream(self, request_iterator, context):
        async for req in request_iterator:
            print(req.user_id)
            print(req.chunk)
            mini_summary = summarize_mt5(req.chunk)
            yield docssummary_pb2.DocsSummaryResponse(line=mini_summary)

async def serve():
    server = grpc.aio.server()
    docssummary_pb2_grpc.add_DocsSummaryServiceServicer_to_server(DocsSummaryService(), server)
    server.add_insecure_port('[::]:5002')
    await server.start()
    print("gRPC DocsSummaryService running on port 5002")
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        print("gRPC server cancelled (shutting down cleanly)")

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("Server stopped by user")