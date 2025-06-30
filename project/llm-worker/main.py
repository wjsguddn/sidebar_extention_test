from confluent_kafka import KafkaException, Consumer
import os, json, time
import openai
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    print("경고: PERPLEXITY_API_KEY 환경변수가 설정되지 않았습니다.")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


BOOT = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
consumer = Consumer({
    "bootstrap.servers": BOOT,
    "group.id": "llm-worker",
    "auto.offset.reset": "earliest",
    "session.timeout.ms": 6000
})
consumer.subscribe(["browser.events"])


# GPT generate
def generate_recommendations(url: str, title: str, text: str) -> Dict:
    # JSON 형식으로 응답을 받아 파싱
    if not openai.api_key:
        return {
            "summary": "OpenAI API 키가 설정되지 않아 추천을 생성할 수 없습니다.",
            "recommendations": []
        }

    print("GPT API로 추천 생성 중...")

    try:
        # 텍스트 길이 제한 (GPT 토큰 제한 고려)
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
1. 주제(대상)에 대한 50~100자 내외의 한국어 요약 설명 (summary 라는 키값을 갖도록)
2. 주제와 관련되어 사용자가 관심있어 할 것이라고 생각되는 컨텐츠 5가지 추천: 컨텐츠는 url로 접근 가능하여야 하며 해당 사이트(컨텐츠)에 대한 간략한 한국어 설명과 url 링크를 포함한다.(recommendations 라는 키값을 갖도록)

출력 예시
{
  "summary": "Logparser는 비정형 로그 메세지에서 공통된 이벤트 템플릿을 자동으로 추출하고, 구조화된 형식으로 변환해주는 Python 기반 로그 분석 도구입니다. Drain, Spell, IPLoM 등 다양한 파싱 알고리즘이 내장되어 있어 알고리즘 간 성능을 비교하거나 실제 로그에 적용해보기에 적합합니다.",
  "recommendations": [
    {
      "title": "[Drain3: 실시간 로그 파싱을 위한 Python 라이브러리]",
      "exp1": "- Github 오픈소스 - Python - Kafka 지원",
      "url": "https://github.com/logpai/Drain3",
      "exp2": "로그 스트림 처리에 적합한 Drain 알고리즘의 실시간 버전"
    },
    {
      "title": "[로그 파싱 알고리즘 16종 비교 논문 (ICSE`19)]",
      "exp1": "- 학술 논문 - 성능 벤치마크 - 오픈데이터셋 사용",
      "url": "https://arxiv.org/abs/1811.03509",
      "exp2": "다양한 로그 파서 성능을 분석한 IEEE ICSE 논문"
    },
    {
      "title": "...",
      "exp1": "...",
      "url": "https://example3.com",
      "exp2": "..."
    },
    {
      "title": "...",
      "exp1": "...",
      "url": "https://example4.com",
      "exp2": "..."
    },
    {
      "title": "...",
      "exp1": "...",
      "url": "https://example5.com",
      "exp2": "..."
    }
  ]
}
출력은 위와 동일한 key값 구성의 JSON 형식이어야 하며, JSON외엔 그 어떤 내용도 답변에 포함되지 않도록 해야한다.
"""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.7
        )

        # JSON 응답 파싱
        response_content = response.choices[0].message.content.strip()

        # JSON 파싱 시도
        try:
            result = json.loads(response_content)

            # 추천 항목들을 리스트로 변환
            recommendations = result.get("recommendations", [])

            return {
                "summary": result.get("summary", "요약을 생성할 수 없습니다."),
                "recommendations": recommendations
            }

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 실패: {e}")
            print(f"응답 원문: {response_content}")
            # JSON 파싱 실패 시 fallback
            return {
                "summary": "응답 파싱에 실패했습니다.",
                "recommendations": []
            }

    except Exception as e:
        print(f"GPT API 호출 실패: {e}")
        return {
            "summary": f"추천 생성 중 오류가 발생했습니다: {str(e)}",
            "recommendations": []
        }

# Perplexity generate
# def generate_recommendations(url: str, title: str, text: str) -> Dict:
#     # JSON 형식으로 응답을 받아 파싱
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


def process_browser_data(data: Dict) -> Dict:
    # 브라우저 데이터 처리 및 추천 생성
    url = data.get("url", "")
    title = data.get("title", "")
    text = data.get("text", "")
    screenshot = data.get("screenshot_base64", "")
    
    print("메시지 수신:")
    print("  URL:", url)
    print("  Title:", title)
    print("  Screenshot:", screenshot[:50] + ("..." if len(screenshot) > 60 else ""))
    print("  Text 길이:", len(text), "문자")
    
    # 텍스트 미리보기 (처음 200자)
    if text:
        preview = text[:200] + ("..." if len(text) > 200 else "")
        print("  Text 미리보기:", preview)
    
    # LLM API로 추천 생성
    s_time = time.time()
    result_data = generate_recommendations(url, title, text)
    
    result = {
        "url": url,
        "title": title,
        "summary": result_data["summary"],
        "recommendations": result_data["recommendations"],
        "timestamp": time.time(),
        "delay": time.time() - s_time
    }
    
    # 추천 결과 로그 출력
    print("생성된 요약:")
    print(f"  {result_data['summary']}")
    print("생성된 추천:")
    for i, rec in enumerate(result_data["recommendations"], 1):
        print(f"  {i}. {rec.get('title', '제목 없음')}")
        print(f"     설명1: {rec.get('exp1', '')}")
        print(f"     URL: {rec.get('url', '')}")
        print(f"     설명2: {rec.get('exp2', '')}")
    print(f"Delay: {result['delay']}")
    return result

print("LLM 워커 대기중…")
print("OpenAI API 키 상태:", "설정됨" if openai.api_key else "설정되지 않음")
print("Perplexity API 키 상태:", "설정됨" if PERPLEXITY_API_URL else "설정되지 않음")

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print("Kafka error:", msg.error())
        continue
    try:
        data = json.loads(msg.value().decode())
    except Exception as e:
        print("JSON decode 실패:", e, "| RAW:", msg.value())
        continue

    # 브라우저 데이터 처리 및 추천 생성
    result = process_browser_data(data)
    print("추천 생성 완료.\n")
