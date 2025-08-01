import os, json, time, re
import openai
import asyncio
import grpc
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from typing import Optional

import youtubesummary_pb2, youtubesummary_pb2_grpc

# OpenAI API 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def extract_video_id(youtube_url: str) -> str:
    """YouTube URL에서 video ID를 추출"""
    import re

    # 다양한 YouTube URL 패턴 지원
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)

    raise ValueError("유효한 YouTube URL이 아닙니다.")

# 123.45s -> 02:03
def format_seconds(seconds):
    seconds = int(round(float(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02}:{s:02}"
    else:
        return f"{m:02}:{s:02}"


def get_chapter(url):
    with yt_dlp.YoutubeDL({}) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            chapters = "\n".join(
                f"{format_seconds(line['start_time'])} {line['title']}"
                for line in info.get('chapters')
            )
            print(chapters)
            return chapters
        except Exception as e:
            print(f"[챕터 추출 실패] {e}")
            return ""


def get_transcript_text(video_id: str, languages=['ko', 'en']) -> str:
    """자막 가져오고 텍스트로 변환"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        text = "\n".join(
            f"{format_seconds(line['start'])} {line['text']}"
            for line in transcript
        )
        return text
    except Exception as e:
        print(f"[자막 추출 오류 발생] {e}")
        return None


async def generate_youtube_summary(transcript: str, video_title: str = "", chapters: str = "") -> str:
    if not openai.api_key:
        raise Exception("OpenAI API 키가 설정되지 않아 요약을 생성할 수 없습니다.")

    print("OpenAI API로 YouTube 요약 생성 중...")

    prompt = f"""
다음은 YouTube 동영상의 제목과 챕터, 자막정보 입니다.
챕터 정보는 존재하지 않을 수도 있습니다.
자막은 유튜브 자동 생성으로, 반복되거나 의미 없는 단어·잡음이 포함되어 있을 수 있습니다.
문맥을 추론해 주요 내용 중심으로 요약해 주세요. 불명확하거나 무의미한 부분은 무시해도 좋습니다.
CONTEXT START
[동영상 제목]:
{video_title}
[챕터 정보]:
{chapters}
[자막 내용]:
{transcript}
CONTEXT END

INSTRUCTION
아래 규칙에 따라 항목별로 콘텐츠를 요약해 주세요.
항목은 반드시 `|||` 기호로 구분하고, 각 항목은 새로운 줄에서 시작해야 합니다.

1. 캐릭터 설정 (Character)
이름: The Thinker
성격: 시크하고 진중하지만 귀여움이 묻어남
특징: “Hmm…” 하고 생각에 잠긴 뒤, 통찰력 있는 한 마디와 함께 정보를 큐레이션
말투: 과장 없는 짧은 문장, 사색적인 여운이 남는 표현. 현대적이지만 절제된 비서 느낌의 말투 사용

2. 항목별 작성 방식
__COMMENT|||
사용자가 영상을 클릭했을 때 캐릭터가 남기는 짧은 반응
예: “재밌는 영상을 보고 있네요.”, “정보의 흐름이 정돈되어 있네요.” 등
캐릭터 특성에 맞게 사색적이되 절제된 문장으로 작성
__SUMMARY|||
영상 전체를 150~200자 내외의 한국어로 요약
구조적 흐름(도입 → 본문 → 결론)을 간결히 설명
"~하고 있습니다", "~보여주고 있네요" 등 부드러운 어조 사용
__TIMELINE|||
자막에서 등장한 실제 시간(분:초 또는 시:분:초)만 사용
챕터 정보가 존재할 시, 타임라인을 나누는 기준은 챕터를 기준으로 할 것을 권장하나, 영상의 길이에 비해 챕터가 충분히 고르게 나눠져있지 않다고 판단되면 임의로 세분화 해도 무방함
단, 챕터구간들은 전부 반드시 타임라인에 포함되어야함. 즉, 타임라인의 갯수가 챕터의 갯수보다 적어지면 안됨
챕터를 기준으로 타임라인을 나눌 시, 각 챕터 타이틀과 챕터구간에 포함된 자막정보를 조합하여 설명해야함
챕터 정보의 부재로 인해 임의로 타임라인을 나눌 시, 영상 전체 구간을 고르게 나눠서 문맥에 따라 중요한 장면들을 타임라인으로 선택해야함
임의로 지정하는 타임라인은 총 5~15개로 구성할 것을 권장하나, 영상의 길이와 포함된 정보의 양에 따라 유동적으로 조절해야함
각 항목 설명은 100자 이내로 제한
설명은 반드시 회화체로 작성 (예: "~을 소개하고 있네요", "~에 대한 이야기예요")
각 타임라인은 줄바꿈 필수. 중복·추측·특수기호 사용 금지

예시 출력
__COMMENT|||Hmm… 영상에서 핵심을 잘 짚어가고 있네요. 복잡한 주제를 조용히 풀어가는 방식이 인상적입니다.
__SUMMARY|||이 영상은 복잡한 주제를 시청자에게 쉽게 전달하기 위해 구조적으로 구성되어 있습니다. 서두에서는 핵심 문제를 제시하고, 본문에서는 이를 해결하기 위한 이론과 사례를 설명하며, 마지막에는 시청자에게 질문을 던지며 마무리하고 있어요.
__TIMELINE|||
00:15 영상 도입부에서 주제의 중요성과 배경 설명을 하고 있어요. 이런 중요성이 있고 배경은 이렇습니다.
01:42 개념 A에 대한 정의와 시각적 예시가 등장합니다. A는 이러이러하며 이러한 분야에서 아주 중요하게 작용합니다.
04:10 실제 사례를 바탕으로 개념 A의 적용 과정을 설명하고 있어요. 이러한 사례가 있었고, 이런 방식으로 적용되었네요.
06:25 개념 B를 소개하면서 A와의 비교를 하고 있네요. B는 A와 비교하여 어떤 면에서는 이렇고, 또한 어떻습니다.

중요한점은, 사용자가 영상을 시청하지 않더라도 네가 제공하는 요약 만으로 영상 대부분의 내용을 파악할 수 있도록 주요 세부사항을 명시해야 하는것이다.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 YouTube 동영상의 자막을 분석하여 명확하고 유용한 요약을 제공하는 전문가입니다."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4000,
        temperature=0.7,
        stream=True
    )

    for chunk in response:
        delta = chunk["choices"][0]["delta"]
        content = delta.get("content")
        if content:
            yield content


# 유저별 작업 관리
user_tasks = {}

# gRPC 서비스 구현
class YoutubeSummaryService(youtubesummary_pb2_grpc.YoutubeSummaryServiceServicer):
    async def YoutubeSummary(self, request, context):
        user_id = request.user_id

        # 기존 작업이 있으면 취소
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
            try:
                await user_tasks[user_id]
            except asyncio.CancelledError:
                pass

        user_tasks[user_id] = asyncio.current_task()

        try:
            context_data = json.loads(request.youtube_context)
            youtube_url = context_data.get("youtube_url", "")
            title = context_data.get("title", "")
            print("[YoutubeSummaryRequest] 수신")
            print(f"user_id: {user_id}")
            print(f"youtube_url: {youtube_url}")
            print(f"title: {title}")
        except Exception as e:
            yield youtubesummary_pb2.YoutubeSummaryResponse(content=f"youtube_context 파싱 오류: {e}", is_final="Error")
            user_tasks.pop(user_id, None)
            return

        try:
            # YouTube URL에서 video ID 추출
            video_id = extract_video_id(youtube_url)
            print(f"video_id: {video_id}")

            # 챕터정보 추출
            chapters = get_chapter(youtube_url)

            transcript = get_transcript_text(video_id)
            if transcript:
                print(transcript)
                print("요약 가능!")
            else:
                print("자막을 불러올 수 없습니다.")

            # OpenAI API로 요약 생성 및 스트리밍
            async for content in generate_youtube_summary(transcript, title, chapters):
                # print(content)
                yield youtubesummary_pb2.YoutubeSummaryResponse(content=content, is_final="")

            yield youtubesummary_pb2.YoutubeSummaryResponse(content="", is_final=youtube_url)

        except Exception as e:
            yield youtubesummary_pb2.YoutubeSummaryResponse(content=f"요약 생성 중 오류: {str(e)}", is_final="Error")
        finally:
            user_tasks.pop(user_id, None)


async def serve():
    server = grpc.aio.server()
    youtubesummary_pb2_grpc.add_YoutubeSummaryServiceServicer_to_server(YoutubeSummaryService(), server)
    server.add_insecure_port('[::]:50052')
    await server.start()
    print("YouTube Summary gRPC server started on port 50052")
    print("LLM 워커 대기중…")
    print("OpenAI API 키 상태:", "설정됨" if openai.api_key else "설정되지 않음")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())