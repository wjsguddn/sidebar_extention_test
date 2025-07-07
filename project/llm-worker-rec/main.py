import os, json, time
import openai
import requests
import asyncio
import grpc

from recommendation_pb2 import RecommendResponse
import recommendation_pb2_grpc


# OpenAI API 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


# 유저별 작업 관리
user_tasks = {}


# GPT generate
def generate_recommendations(url: str, title: str, text: str) -> str:
    if not openai.api_key:
        return "OpenAI API 키가 설정되지 않아 추천을 생성할 수 없습니다."

    print("GPT API로 추천 생성 중...")

    
    max_text_length = 3000
    if len(text) > max_text_length:
        text = text[:max_text_length] + "..."

    prompt = f"""
웹페이지 정보:
- URL: {url}
- Page Title: {title}
- Page Text: {text}
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """
너는 사용자 브라우저 컨텐츠를 모니터링하며 사용자가 어떤 주제에 주목중인지를 추론하고 해당 주제에 대한 관련 컨텐츠를 추천해주는 브라우저 에이전트다.
너에게 입력 될 정보는 사용자의 현재 웹페이지 정보(URL, Page Title, Page Text)이며, Page Text의 경우 웹 페이지의 구조상 불필요한 정보들이 포함되어있을 수 있다.
해당 웹 페이지 정보들을 기반으로 사용자가 현재 가장 주목중인 주제(대상)를 추론 및 선정하고 해당 주제에 대한 간략한 요약 설명 및 컨텐츠 추천이 이루어져야 한다.
출력은 반드시 다음과 같은 형식이어야만 한다.
1. 주제(대상)에 대한 50~100자 내외의 한국어 요약 설명
2. 주제와 관련되어 사용자가 관심있어 할 것이라고 생각되는 컨텐츠 5가지 추천: 컨텐츠는 url로 접근 가능하여야 하며 해당 사이트(컨텐츠)에 대한 간략한 한국어 설명과 url 링크를 포함한다.
"""}, 
            {"role": "user", "content": prompt}
        ],
        max_tokens=4096,
        temperature=0.7,
        stream=True
    )
    for chunk in response:
        delta = chunk["choices"][0]["delta"]
        content = delta.get("content")
        if content:
            yield content


# Perplexity generate
# def generate_recommendations(url: str, title: str, text: str) -> Dict:
#
#     if not PERPLEXITY_API_KEY:
#         return {
#             "summary": "Perplexity API 키가 설정되지 않아 추천을 생성할 수 없습니다.",
#             "recommendations": []
#         }
#
#     print("Perplexity API로 추천 생성 중...")
#
#     try:
#         prompt = f"""
# 웹페이지 정보:
# - URL: {url}
# - Page Title: {title}
# """
#
#         payload = {
#             "model": "sonar",
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": """
# 너는 사용자 브라우저 컨텐츠를 모니터링하며 사용자가 어떤 주제에 주목중인지를 추론하고 해당 주제에 대한 관련 컨텐츠를 추천해주는 브라우저 에이전트다.
# 너에게 입력 될 정보는 사용자의 현재 웹페이지 정보(URL, Page Title)이며, 네가 URL을 통해 직접 해당 페이지를 탐색하고 사용자가 어떤 주제(대상)에 가장 관심이 있는지를 파악해야한다.
# 사용자가 현재 가장 주목중인 주제(대상)를 추론 및 선정하였다면, 해당 주제에 대한 간략한 요약 설명 및 컨텐츠 추천이 이루어져야 한다.
# 출력은 반드시 다음과 같은 형식이어야만 한다.
# 1. 주제(대상)에 대한 50~100자 내외의 한국어 요약 설명 (summary 라는 키값을 갖도록)
# 2. 주제와 관련되어 사용자가 관심있어 할 것이라고 생각되는 컨텐츠 3가지 추천: 컨텐츠는 url로 접근 가능하여야 하며 해당 사이트(컨텐츠)에 대한 간략한 한국어 설명과 url 링크를 포함한다.(recommendations 라는 키값을 갖도록)
#
# 출력 예시:
# {
#   "summary": "Logparser는 비정형 로그 메세지에서 공통된 이벤트 템플릿을 자동으로 추출하고, 구조화된 형식으로 변환해주는 Python 기반 로그 분석 도구입니다. Drain, Spell, IPLoM 등 다양한 파싱 알고리즘이 내장되어 있어 알고리즘 간 성능을 비교하거나 실제 로그에 적용해보기에 적합합니다.",
#   "recommendations": [
#     {
#       "title": "[Drain3: 실시간 로그 파싱을 위한 Python 라이브러리]",
#       "exp1": "- Github 오픈소스 - Python - Kafka 지원",
#       "url": "https://github.com/logpai/Drain3",
#       "exp2": "로그 스트림 처리에 적합한 Drain 알고리즘의 실시간 버전"
#     },
#     {
#       "title": "[로그 파싱 알고리즘 16종 비교 논문 (ICSE`19)]",
#       "exp1": "- 학술 논문 - 성능 벤치마크 - 오픈데이터셋 사용",
#       "url": "https://arxiv.org/abs/1811.03509",
#       "exp2": "다양한 로그 파서 성능을 분석한 IEEE ICSE 논문"
#     },
#     {
#       "title": "...",
#       "exp1": "...",
#       "url": "https://example.com",
#       "exp2": "..."
#     }
#   ]
# }
# 출력은 위와 동일한 key값 구성의 JSON 형식이어야 하며, JSON외엔 그 어떤 내용도 답변에 포함되지 않도록 해야한다.
# """
#                 },
#                 {
#                     "role": "user",
#                     "content": prompt
#                 }
#             ],
#             "temperature": 0.3,
#             "max_tokens": 2048
#         }
#
#         headers = {
#             "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
#             "Content-Type": "application/json"
#         }
#
#         res = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload)
#         res.raise_for_status()
#         content = res.json()["choices"][0]["message"]["content"].strip()
#
#         try:
#             result = json.loads(content)
#             recommendations = result.get("recommendations", [])
#
#             return {
#                 "summary": result.get("summary", "요약을 생성할 수 없습니다."),
#                 "recommendations": recommendations
#             }
#
#         except json.JSONDecodeError as e:
#             print(f"JSON 파싱 실패: {e}")
#             print(f"응답 원문: {content}")
#             return {
#                 "summary": "응답 파싱에 실패했습니다.",
#                 "recommendations": [],
#             }
#
#     except Exception as e:
#         print(f"API 호출 실패: {e}")
#         return {
#             "summary": f"추천 생성 중 오류가 발생했습니다: {str(e)}",
#             "recommendations": []
#         }


# gRPC 서비스 구현
class RecommendationService(recommendation_pb2_grpc.RecommendationServiceServicer):
    async def Recommend(self, request, context):
        user_id = request.user_id

        # 기존 작업이 있으면 취소
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
            try:
                await user_tasks[user_id]
            except asyncio.CancelledError:
                pass

        user_tasks[user_id] = asyncio.current_task()

        # browser_context 파싱
        try:
            context_data = json.loads(request.browser_context)
            url = context_data.get("url", "")
            title = context_data.get("title", "")
            text = context_data.get("text", "")
            print(f"[gRPC Recommend] user_id={user_id}")
            print(f"[gRPC Recommend] url={url}")
            print(f"[gRPC Recommend] title={title}")
            print(f"[gRPC Recommend] text(앞 300자)={text[:300]} ...")
        except Exception as e:
            yield RecommendResponse(content=f"browser_context 파싱 오류: {e}", is_final=True)
            del user_tasks[user_id]
            return

        try:
            for content in generate_recommendations(url, title, text):
                yield RecommendResponse(content=content, is_final=False)
            yield RecommendResponse(content="", is_final=True)
        except Exception as e:
            yield RecommendResponse(content=f"추천 생성 중 오류: {str(e)}", is_final=True)
        finally:
            del user_tasks[user_id]

async def serve():
    server = grpc.aio.server()
    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(RecommendationService(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    print("gRPC server started on port 50051")
    print("LLM 워커 대기중…")
    print("OpenAI API 키 상태:", "설정됨" if openai.api_key else "설정되지 않음")
    print("Perplexity API 키 상태:", "설정됨" if PERPLEXITY_API_KEY else "설정되지 않음")
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())