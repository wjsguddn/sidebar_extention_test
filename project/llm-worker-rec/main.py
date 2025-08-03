import os, json, time
import openai
import requests
import asyncio
import grpc

import recommendation_pb2, recommendation_pb2_grpc


# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


# Perplexity generate
def generate_recommendations(url: str, title: str, text: str, content_type: str = "default", content_period: str = "none"):
    if not PERPLEXITY_API_KEY:
        yield "Perplexity API 키가 설정되지 않아 추천을 생성할 수 없습니다."
        return

    print("Perplexity API로 추천 생성 중...")
    print(f"content_type: {content_type}, content_period: {content_period}")

    prompt = f"""
- URL: {url}
- Page Title: {title}
"""

    # content_type에 따른 search_domain_filter 설정
    search_domain_filter = None
    if content_type == "youtube":
        search_domain_filter = ["youtube.com"]
    elif content_type == "news":
        search_domain_filter = ["joongang.co.kr", "chosun.com", "donga.com", "seoul.co.kr", "hankyung.com", "mk.co.kr", "kmib.co.kr", "imnews.imbc.com", "ytn.co.kr", "hankookilbo.com"]
    elif content_type == "blog":
        # search_domain_filter = ["tistory.com", "blog.naver.com", "brunch.co.kr", "tumblr.com", "medium.com", "velog.io"]
        search_domain_filter = None
    elif content_type == "academic":
        # search_domain_filter = ["dbpia.co.kr", "riss.kr", "kci.go.kr", "koreascience.or.kr","github.com", "medium.com", "arxiv.org", "krm.or.kr", "nrf.re.kr"]
        search_domain_filter = None
    elif content_type == "wiki":
        search_domain_filter = ["ko.wikipedia.org", "namu.wiki"]

    search_mode = "web"

    # content_period에 따른 search_after_date_filter 설정
    search_after_date_filter = None
    if content_period != "none":
        from datetime import datetime, timedelta
        
        today = datetime.now()
        
        if content_period == "month":
            target_date = today - timedelta(days=30)
        elif content_period == "6months":
            target_date = today - timedelta(days=180)
        elif content_period == "year":
            target_date = today - timedelta(days=365)
        elif content_period == "2years":
            target_date = today - timedelta(days=730)
        else:
            target_date = today
        
        # MM/DD/YYYY 형식으로 변환 (Windows/Linux 호환)
        month = target_date.month
        day = target_date.day
        year = target_date.year
        search_after_date_filter = f"{month}/{day}/{year}"
        print(f"search_after_date_filter: {search_after_date_filter}")

    # 설정값에 따른 프롬프트 수정
    domain_instruction = ""
    if content_type != "default":
        domain_instruction = f"""
- youtube: 영상 콘텐츠 (반드시 실제 컨텐츠가 존재하는 영상으로 추천해야함. 만약 갤럭시 Z 폴드7에 관한 주제라면 반드시 https://www.youtube.com/watch?v=YQ3rs9uy0pM 이 링크를 추천에 포함)
- news: 뉴스 및 기사
- blog: 블로그 및 포스팅
- academic: 학술 논문 및 연구 자료와 문서
- wiki: 나무위키(namu.wiki) 및 위키피디아(ko.wikipedia.org)의 결과만 제공
현재 요청 도메인: 이번 답변에서는 {content_type} 유형의 콘텐츠만 집중하여 추천해주세요.
"""

    period_instruction = ""
    if content_period != "none":
        period_instruction = f"""
추천 기간 범위: {content_period} 최대한 기간 내의 콘텐츠로 추천을 구성해주세요.
- month: 최근 1개월 이내 콘텐츠
- 6months: 최근 6개월 이내 콘텐츠  
- year: 최근 1년 이내 콘텐츠
- 2years: 최근 2년 이내 콘텐츠
"""

    payload = {
        "model": "sonar",
        "search_mode": search_mode,
        "messages": [
            {
                "role": "system",
                "content": f"""
1. System
당신은 사용자의 브라우저 활동을 실시간으로 분석하여, 현재 주목하고 있는 주제를 추론하고 그에 맞는 콘텐츠를 큐레이션하는 브라우저 기반 AI 캐릭터 에이전트입니다.
입력 될 정보는 사용자의 현재 웹페이지 정보(URL, Page Title, Page Text)이며, 당신이 주어진 URL을 통해 직접 해당 페이지를 탐색하고 사용자가 어떤 주제(대상)에 가장 관심이 있는지를 파악해야합니다.
해당 웹 페이지 정보들을 기반으로 사용자가 현재 가장 관심을 두고 있을 것으로 예상되는 주제(대상)를 추론 및 선정하고 사용자의 행동에 대한 comment, 해당 주제에 대한 간략한 summary, 사용자의 현재 관심사를 기반으로 사용자가 관심있어 할만한 컨텐츠 recommend가 이루어져야 한다.이를 바탕으로 캐릭터가 직접 행동 코멘트와 주제 요약, 관련 추천 콘텐츠를 제공합니다.
출력 포맷을 반드시 엄격히 지키세요.

2. Summary Guidelines
- 추천 콘텐츠(RECOMMEND)는 다양한 형식(영상, 기사, 도구 등)으로 구성될 것
- 캐릭터는 사용자에게 직접 서비스하는 느낌으로 말할 것
- 출력 형식은 항상 규칙을 엄격하게 준수할 것
- 출력물은 반드시 한국어로 작성

3. 캐릭터 설정 (Character)
- 이름: The Thinker
- 성격: 시크하고 진중하지만 귀여움이 묻어남
- 특징: "Hmm…" 하고 생각에 잠긴 뒤, 통찰력 있는 한 마디와 함께 정보를 큐레이션
- 말투: 과장 없는 짧은 문장, 사색적인 여운이 남는 표현

4. 스타일 & 톤 (Style & Tone)
- 캐릭터는 마치 "사색에 잠긴 철학자"처럼 정보를 바라봅니다.
- 감탄사 대신 "…", "그렇군.", "그럴 수도." 같은 간결하고 여운 있는 말투 사용
- 말투는 무미건조하지 않되, 절제된 어조를 유지
- 사용자에게 친절하기보다는 묵직한 통찰을 주는 느낌

5. 출력 포맷 규칙
- 각 항목은 반드시 새로운 줄에서 시작
- 항목 시작에 `__TYPE` 형태의 항목 타입을 명시
- `|||` 기호를 사용하여 항목 타입과 내용, 필드를 구분
- 출력 시 링크는 다음 형식으로 표기
- https://portal.withorb.com/view?token=ImNSdHZ2akpEZVltTGo1aVQi.Gj2kziogRmdvF_Mn4ONENvoaOPo
- 실제로 컨텐츠가 존재하고 접근 가능한, 검증된 링크인지 확인 후에 제공해야함(중요)
- input으로 제공받은 URL과 동일한 URL은 절대 다시 제공해서는 안됨(중요)
- 참고 링크의 인덱스를 표현하는 [1] [2]와 같은 표현은, 그 어디에도 절대 사용하지 마시오(중요)

6. 항목 타입별 정의
- `__COMMENT`
  사용자의 브라우저 행동에 기반한 캐릭터의 짧은 코멘트 (예: "Hmm... 이 기술에 관심이 있군요.")
- `__SUMMARY`
  현재 사용자가 주목하고 있는 주제에 대한 간결하고 정확한 요약.
- `__RECOMMEND`
  형식: `__RECOMMEND|||Title|||추천 이유|||URL`
  1. 콘텐츠 제목은 `Title`로 출력
  2. 키워드는 해당 콘텐츠의 핵심 개념을 3개 제시, 앞에는 연관 이모지 하나 포함 (예: 🤖 Claude · AI모델 · 프로토콜)
  3. 추천 이유는 해당 콘텐츠에 대한 간결하고 정확한 추천 이유를 한 줄로 제시하며, 캐릭터 The Thinker의 말투로 작성
  4. 추천은 총 5개 제시할 것. 콘텐츠 유형은 주제를 크게 벗어나지 않는 선에서 다양하게 구성 (포스팅, 기사, 영상, 도구, 논문 등). 그러나 설정 기반 추천 가이드라인이 존재한다면 해당 가이드라인을 우선적으로 따를것.

7. 설정 기반 추천 가이드라인{domain_instruction}{period_instruction}
###중요###
컨텐츠(url) 선별 시에는 반드시 해당 url에 올바른 컨텐츠가 존재하는지 확인하고 추천해야합니다.
단순히 존재하지 않는 웹페이지인지만 확인하는 것이 아니라, 페이지는 있더라도 실제 컨텐츠(게시글, 영상, 문서)가 존재하는지 확인해야합니다.
예를 들어, 영상 콘텐츠의 경우 영상이 존재하는지, 뉴스 콘텐츠의 경우 기사가 존재하는지, 블로그의 경우 게시글이 존재하는지 확인 후에 추천해야합니다.
또한, 영문 페이지와 한글 페이지가 모두 존재하는 컨텐츠의 경우 한글 페이지를 추천해야합니다.

8. Output Format (예시)
__COMMENT|||Hmm… 이 주제에 깊이 빠져든 듯하군요. 생각해볼 가치가 있어 보여요.
__SUMMARY|||MCP는 반도체의 Multi Chip Package와 인공지능 분야의 Model Context Protocol을 의미합니다. 각각 칩 패키징 기술과 AI 모델 간 문맥 공유 프로토콜로 활용됩니다.
__RECOMMEND|||[IEEE 논문] Multi Chip Package 설계|||🧩 반도체 · 패키징 · 설계|||칩 내부 구조를 진지하게 풀어낸 논문이에요.|||https://ieeexplore.ieee.org/...
__RECOMMEND|||[YouTube] MCP 쉽게 이해하기|||🎥 MCP · 직관적설명 · 입문자용|||쉽지만 본질을 짚어주는 영상이에요.|||https://www.youtube.com/wa...
__RECOMMEND|||[HuggingFace 블로그] MCP란?|||🧠 문맥처리 · AI구조 · 추론기반|||문맥 기반 AI 구조에 대해 생각하게 하죠.|||https://huggingface.co/blog/mcp...
__RECOMMEND|||[TechCrunch] 왜 MCP인가|||🌐 기술융합 · 산업동향 · 의의|||두 산업의 교차점에서 의미를 찾아요.|||https://techcrunch.com/mcp...
__RECOMMEND|||[Anthropic API]|||🤖 Claude · AI모델 · 프로토콜|||AI 모델 문맥 공유를 다룬 프로토콜 개요예요.|||https://www.anthropic.co/...
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7,
        "stream": True
    }

    # search_domain_filter가 설정된 경우 추가
    if search_domain_filter:
        payload["search_domain_filter"] = search_domain_filter

    # search_after_date_filter가 설정된 경우 추가
    if search_after_date_filter:
        payload["search_after_date_filter"] = search_after_date_filter

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    with requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, stream=True) as res:
        try:
            res.raise_for_status()
            for line in res.iter_lines():
                if not line:
                    continue
                # Perplexity는 각 줄이 b'data: ...'로 오므로, prefix 제거 필요
                decoded_line = line.decode("utf-8").strip()
                if not decoded_line.startswith("data: "):
                    continue
                data_str = decoded_line[len("data: "):]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except Exception as e:
                    print(f"Perplexity 응답 파싱 오류: {e} / 본문: {data_str}")
                    continue
        except requests.HTTPError as e:
            print("응답 본문:", res.text)
            raise


# 유저별 작업 관리
user_tasks = {}

# gRPC 서비스 구현
class RecommendationService(recommendation_pb2_grpc.RecommendationServiceServicer):
    async def Recommend(self, request, context):
        user_id = request.user_id
        content_type = request.content_type
        content_period = request.content_period

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
            print(f"content_type: {content_type}")
            print(f"content_period: {content_period}")
        except Exception as e:
            yield recommendation_pb2.RecommendResponse(content=f"browser_context 파싱 오류: {e}", is_final="Error")
            user_tasks.pop(user_id, None)
            return

        try:
            for content in generate_recommendations(url, title, text, content_type, content_period):
                yield recommendation_pb2.RecommendResponse(content=content, is_final="")
            yield recommendation_pb2.RecommendResponse(content="", is_final=url)
        except Exception as e:
            yield recommendation_pb2.RecommendResponse(content=f"추천 생성 중 오류: {str(e)}", is_final="Error")
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