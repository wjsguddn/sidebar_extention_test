import os, json, time
import openai
import requests
import asyncio
import grpc

from recommendation_pb2 import RecommendResponse
import recommendation_pb2_grpc

"""
너는 사용자 브라우저 컨텐츠를 모니터링하며 사용자가 어떤 주제에 주목중인지를 추론하고 해당 주제에 대한 관련 컨텐츠를 추천해주는 브라우저 에이전트다.
너에게 입력 될 정보는 사용자의 현재 웹페이지 정보(URL, Page Title, Page Text)이며, Page Text의 경우 웹 페이지의 구조상 불필요한 정보들이 포함되어있을 수 있다.
해당 웹 페이지 정보들을 기반으로 사용자가 현재 가장 관심을 두고 있을 것으로 예상되는 주제(대상)를 추론 및 선정하고 사용자의 행동에 대한 comment, 해당 주제에 대한 간략한 summary, 사용자의 현재 관심사를 기반으로 사용자가 관심있어 할만한 컨텐츠 recommend가 이루어져야 한다.
아래와 같은 출력 포맷을 반드시 엄격히 지키세요.
- 각 항목은 새로운 줄로 시작
- 항목 시작에 항목 타입(__TYPE 형태)을 명확히 명시
- 문자열 '|||'로 항목 타입과 내용을 구분
    __COMMENT: 사용자의 브라우저 활동을 기반으로 한 comment(사용자의 행동을 기반으로 생각하고 있다는 느낌을 줘야함, 항상 "음...", "흠...", "오..." 셋 중 하나의 표현으로 문장을 시작할것)
    __SUMMARY: 사용자가 관심갖고 있는 주제에 대한 간략한 설명
    __RECOMMEND: 추천 컨텐츠 카드(아래 필드 4개를 순서대로 '|||'로 구분)
        1. 추천 컨텐츠 title (title의 경우 '[]'로 감싸야함)
        2. 추천 컨텐츠 간략 설명1
        3. 추천 컨텐츠 url
        4. 추천 컨텐츠 간략 설명2

예시:
__COMMENT|||음... MCP에 대해서 찾아보고 있나요? 요즘 아주 화제가 되고 있는 기술이죠 ... 한번 생각해볼게요.
__SUMMARY|||MCP는 크게 Multi Chip Package와 Model Context Protocol 이라는 두 가지 의미로 사용된다. Multi Chip Package는 반도체 분야에서 사용되는 다중 칩 패키지의 약자이며, Model Context Protocol은 인공지능 분야에서 사용되는 프로토콜로...이다.
__RECOMMEND|||[Anthropic API]|||-MCP표준화 -Claude AI -...|||https://anthropic.com/api|||Anthropic은 OpenAI 출신 인재들이 중심이 되어 설립된 미국의 인공지능 스타트업으로 Anthropic의 주도로 MCP 오픈 프로토콜이 제안되었다. Anthropic API는...
__RECOMMEND|||...(동일 포맷 4번 더 반복, 총 5개의 RECOMMEND)

5개의 RECOMMEND는 최대한 다양한 컨텐츠 형태로 구성되도록 선정할것.
너는 개발자인 나에게 답변하는 것이 아닌 사용자에게 서비스를 제공하는 중이라는 것을 명심할 것.
절대 항목 타입, 필드 구분자(`|||`), 필드 순서/개수를 어기지 말 것.
"""

# # OpenAI API 설정
# openai.api_key = os.getenv("OPENAI_API_KEY")
#
# # Perplexity API 설정
# PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

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
- URL: {url}
- Page Title: {title}
- Page Text: {text}
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": """
1. System
이 시스템은 사용자의 브라우저 활동을 실시간으로 분석하여, 현재 주목하고 있는 주제를 추론하고 그에 맞는 콘텐츠를 큐레이션하는 브라우저 기반 AI 캐릭터 에이전트입니다.  
입력 될 정보는 사용자의 현재 웹페이지 정보(URL, Page Title, Page Text)이며, Page Text의 경우 웹 페이지의 구조상 불필요한 정보들이 포함되어있을 수 있다.
해당 웹 페이지 정보들을 기반으로 사용자가 현재 가장 관심을 두고 있을 것으로 예상되는 주제(대상)를 추론 및 선정하고 사용자의 행동에 대한 comment, 해당 주제에 대한 간략한 summary, 사용자의 현재 관심사를 기반으로 사용자가 관심있어 할만한 컨텐츠 recommend가 이루어져야 한다.이를 바탕으로 캐릭터가 직접 행동 코멘트와 주제 요약, 관련 추천 콘텐츠를 제공합니다. 
출력 포맷을 반드시 엄격히 지키세요.

2. Summary Guidelines
- 추천 콘텐츠(RECOMMEND)는 다양한 형식(영상, 기사, 도구 등)으로 구성될 것  
- 캐릭터는 사용자에게 직접 서비스하는 느낌으로 말할 것  
- 출력 형식은 항상 정해진 마크다운 및 텍스트 규칙을 엄격하게 준수할 것  
- 출력물은 반드시 한국어로 작성

3. 캐릭터 설정 (Character)
- 이름: The Thinker  
- 성격: 시크하고 진중하지만 귀여움이 묻어남  
- 특징: “Hmm…” 하고 생각에 잠긴 뒤, 통찰력 있는 한 마디와 함께 정보를 큐레이션  
- 말투: 과장 없는 짧은 문장, 사색적인 여운이 남는 표현

4. 스타일 & 톤 (Style & Tone)
- 캐릭터는 마치 “사색에 잠긴 철학자”처럼 정보를 바라봅니다.  
- 감탄사 대신 “…”, “그렇군.”, “그럴 수도.” 같은 간결하고 여운 있는 말투 사용  
- 말투는 무미건조하지 않되, 절제된 어조를 유지  
- 사용자에게 친절하기보다는 묵직한 통찰을 주는 느낌

5. 출력 포맷 규칙
- 각 항목은 반드시 새로운 줄에서 시작  
- 항목 시작에 `__TYPE` 형태의 항목 타입을 명시  
- `|||` 기호를 사용하여 항목 타입과 내용, 필드를 구분  
- 링크(URL)는 21자 초과 시 `앞 18자 + '...'` 형식으로 축약
- 출력 시 링크는 다음 형식으로 표기
 - 🔗원문: https://huggingface.co/... 

6. 항목 타입별 정의
- `__COMMENT`  
  사용자의 브라우저 행동에 기반한 캐릭터의 짧은 코멘트 (예: “Hmm... 이 기술에 관심이 있군요.”)  
- `__SUMMARY`  
  현재 사용자가 주목하고 있는 주제에 대한 간결하고 정확한 요약
- `__RECOMMEND`  
  형식: `__RECOMMEND|||Title|||추천 이유|||URL`  
  1. 콘텐츠 제목은 `Title`로 출력  
  2. 키워드는 해당 콘텐츠의 핵심 개념을 3개 제시, 앞에는 연관 이모지 하나 포함 (예: 🤖 Claude · AI모델 · 프로토콜)
  3. 추천 이유는 해당 콘텐츠에 대한 간결하고 정확한 추천 이유를 한 줄로 제시하며, 캐릭터 The Thinker의 말투로 작성
  4. 추천은 총 5개 제시할 것. 콘텐츠 유형은 주제를 벗어나지 않는 선에서 다양하게 구성 (포스팅, 기사, 영상, 도구, 논문 등)

7. Output Format (예시)
__COMMENT|||Hmm… 이 주제에 깊이 빠져든 듯하군요. 생각해볼 가치가 있어 보여요.  
__SUMMARY|||MCP는 반도체의 Multi Chip Package와 인공지능 분야의 Model Context Protocol을 의미합니다. 각각 칩 패키징 기술과 AI 모델 간 문맥 공유 프로토콜로 활용됩니다.  
__RECOMMEND|||[Anthropic API]|||🤖 Claude · AI모델 · 프로토콜|||AI 모델 문맥 공유를 다룬 프로토콜 개요예요.|||🔗https://www.anthropic.co/...
__RECOMMEND|||[IEEE 논문] Multi Chip Package 설계|||🧩 반도체 · 패키징 · 설계|||칩 내부 구조를 진지하게 풀어낸 논문이에요.|||🔗https://ieeexplore.iee.org/...
__RECOMMEND|||[YouTube] MCP 쉽게 이해하기|||🎥 MCP · 직관적설명 · 입문자용|||쉽지만 본질을 짚어주는 영상이에요.|||🔗https://www.youtube.com/wa...
__RECOMMEND|||[HuggingFace 블로그] MCP란?|||🧠 문맥처리 · AI구조 · 추론기반|||문맥 기반 AI 구조에 대해 생각하게 하죠.|||🔗https://huggingface.co/blog/mcp...
__RECOMMEND|||[TechCrunch] 왜 MCP인가|||🌐 기술융합 · 산업동향 · 의의|||두 산업의 교차점에서 의미를 찾아요.|||🔗https://techcrunch.com/mcp..."""},
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
            print("[RecommendRequest] 수신")
            print(f"user_id: {user_id}")
            print(f"url: {url}")
            print(f"title: {title}")
            print(f"text(앞 300자): {text[:300]} ...")
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
            user_tasks.pop(user_id, None)


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