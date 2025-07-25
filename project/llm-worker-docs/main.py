import grpc
import asyncio
import docssummary_pb2
import docssummary_pb2_grpc
import threading

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os, json, requests
from dotenv import load_dotenv
from pathlib import Path

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference


# MT5 모델 (1단계 mini 요약용)
model_name = "csebuetnlp/mT5_multilingual_XLSum"

# tokenizer = AutoTokenizer.from_pretrained("google/mt5-small")
# model = AutoModelForSeq2SeqLM.from_pretrained("google/mt5-small")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
# model.eval()

# .env 경로를 project 루트로 지정
env_path = Path(__file__).resolve().parents[0] / ".env"
load_dotenv(dotenv_path=env_path)

# WatsonX 변수 설정
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")

# Perplexity API 설정
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def summarize_mt5(text, max_length=125):
    try:
        # 입력 텍스트가 너무 짧으면 그대로 반환
        if len(text.strip()) < 30:
            return text.strip()

        # 최대 512토큰까지만 모델에 들어감(더 길면 잘림) - 영어 1800~2000자, 한글 700자~1200자
        input_ids = tokenizer.encode(text, return_tensors="pt", truncation=True, max_length=512)

        # 최대 150토큰으로 요약 (더 긴 요약 생성)
        with torch.no_grad():
            summary_ids = model.generate(
                input_ids,
                max_length=max_length,
                min_length=30,  # 최소 길이 설정
                num_beams=8,  # 빔 서치 더 증가
                early_stopping=True,
                do_sample=False,  # 결정적 생성
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=3,  # 반복 방지 강화
                encoder_no_repeat_ngram_size=3,
                length_penalty=1.0,  # 더 긴 요약 선호
                repetition_penalty=1.3  # 반복 방지
            )

        # 특수 토큰들을 제거하고 깔끔하게 디코딩
        decoded_text = tokenizer.decode(summary_ids[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)

        # extra_id 토큰들 제거
        for i in range(10):
            decoded_text = decoded_text.replace(f'<extra_id_{i}>', '')

        # 연속된 공백 정리
        decoded_text = ' '.join(decoded_text.split())

        # 요약 품질 검증 - 원본과 너무 다른 경우 처리
        if len(decoded_text.strip()) < 20 or not any(word in text.lower() for word in decoded_text.lower().split()[:3]):
            print('decoded_text', decoded_text, '\n\n\n'+ '# 원본 텍스트에서 핵심 문장 추출 시도')
            # 원본 텍스트에서 핵심 문장 추출 시도
            sentences = text.split('.')
            if len(sentences) > 1:
                # 첫 번째 완전한 문장 반환
                first_sentence = sentences[0].strip()
                if len(first_sentence) > 10:
                    return first_sentence + "."
                else:
                    # 두 번째 문장까지 포함
                    return '. '.join(sentences[:2]).strip() + "."
            else:
                return text[:200].strip() + "..."

        return decoded_text.strip()

    except Exception as e:
        print(f"요약 중 오류 발생: {e}")
        # 오류 발생 시 원본 텍스트의 첫 부분 반환
        return text[:100].strip() + "..."


async def wrap_sync_generator(sync_gen_func, *args, **kwargs):
    # 동기 제너레이터를 비동기 코루틴으로 래핑하여 yield
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    def run_and_enqueue():
        try:
            for item in sync_gen_func(*args, **kwargs):
                asyncio.run_coroutine_threadsafe(queue.put(item), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # 종료 신호

    # 쓰레드에서 실행
    threading.Thread(target=run_and_enqueue, daemon=True).start()

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item


def summarize_with_watsonx(text):
    """WatsonX LLAMA 모델로 final summary 생성"""

    text_len = len(text)
    try:
        if not WATSONX_API_KEY:
            print("WatsonX API 키가 설정되지 않았습니다.")
            return "WatsonX API 키가 필요합니다."

        credentials = Credentials(
            url="https://us-south.ml.cloud.ibm.com",
            api_key=WATSONX_API_KEY,
        )

        client = APIClient(credentials)

        model = ModelInference(
            model_id="meta-llama/llama-3-3-70b-instruct",
            api_client=client,
            project_id=WATSONX_PROJECT_ID
        )

        print("Watsonx API로 요약 생성 중...")

        # 프롬프트 구성
        prompt_short = f"""
                You are a professional document summarization expert. Please analyze the following document and provide an accurate and concise summary in Korean.

                **Summary Guidelines**
                - Clearly identify the main topic and purpose of the document
                - Focus on preserving the most essential information from the content
                - Include only objective and accurate information
                - Evaluate the importance of content objectively regardless of section length or keyword density
                - Do not assume shorter sections are less important; generate balanced summaries considering the overall document context and structure
                - Output must be written in Korean
                
                **Document Contents:**
                <Document Start>
                {text}
                <Document End>
                
                **Output Format**
                Output ONLY in the following format without any additional titles or text:

                - Main Summary/Topic: (1-2 sentence summary of the document's main topic or purpose)
                - Key Points Summary:         
                    ◦ (Keyword1): (Brief explanation)  
                    ◦ (Keyword2): (Brief explanation)  
                    ◦ (Keyword3): (Brief explanation)    
                """

        prompt_medium = f"""
                You are a professional document summarization expert. Please analyze the following document and provide an accurate and concise summary in Korean.

                **Summary Guidelines:**
                - Clearly identify the main topic and purpose of the document
                - Extract the top 3 key points with keywords and brief descriptions
                - Summarize the full content in intro-body-conclusion format within 300 Korean characters
                - Include only objective and accurate information
                - Evaluate the importance of content objectively regardless of section length or keyword density
                - Do not assume shorter sections are less important; generate balanced summaries considering the overall document context and structure
                - **If the document involves comparison or evaluation of methods, clearly state which method performed best and why**
                - **Include performance metrics if available**
                - Output must be written in Korean
                
                **Document Contents:**
                <Document Start>
                {text}
                <Document End>
                
                **Output Format:**
                Main Summary/Topic:  
                (1–2 sentence summary of the document's main topic or purpose in Korean)
                Top 3 Key Points:  
                ◦ (Keyword1): (Brief explanation)  
                ◦ (Keyword2): (Brief explanation)  
                ◦ (Keyword3): (Brief explanation)
                Overall Content Summary:  
                (Summary of the whole document in Korean, using intro-body-conclusion format, max 300 characters)
                """

        prompt_long = f"""
                You are a professional document summarization expert. Please analyze the following document and provide an accurate and concise summary in Korean.

                **Summary Guidelines:**
                - Clearly identify the main topic and purpose of the document
                - Extract the top 4 key points with keywords and brief descriptions
                - Summarize the full content in intro-body-conclusion format within 500 Korean characters
                - Include only objective and accurate information
                - Evaluate the importance of content objectively regardless of section length or keyword density
                - **If the document involves comparison or evaluation of methods, clearly state which method performed best and why**
                - **Include performance metrics if available**
                - Do not assume shorter sections are less important; generate balanced summaries considering the overall document context and structure
                - Output must be written in Korean
                
                **Document Contents:**
                <Document Start>
                {text}
                <Document End>
                
                **Output Format:**
                Please follow this structure exactly and make as markdown form:
                Main Summary/Topic:  
                (1–2 sentence summary of the document's main topic or purpose in Korean)
                Top 4 Key Points:  
                ◦ (Keyword1): (Brief explanation)  
                ◦ (Keyword2): (Brief explanation)  
                ◦ (Keyword3): (Brief explanation)
                ◦ (Keyword4): (Brief explanation)
                Overall Content Summary:  
                (Summary of the whole document in Korean, using intro-body-conclusion format, max 500 characters)

                """
        # "max_new_tokens": 300은 약 1200~1500자 분량의 출력
        stream = model.generate_text_stream(
            prompt=(
                prompt_short if text_len < 1000 else
                prompt_medium if text_len < 5000 else
                prompt_long
            ),
            params={
                "decoding_method": "greedy",
                "max_new_tokens": 300,
            }
        )

        for chunk in stream:
            # print(f"[STREAM DEBUG] chunk: {chunk}")
            try:
                yield chunk
            except Exception as e:
                print("응답 파싱 실패:", str(e))
                yield "[STREAM ERROR: 응답 파싱 실패]"

    except Exception as e:
        print(f"WatsonX 요약 중 오류 발생: {e}")
        # return {"summary": f"WatsonX 요약 오류: {str(e)}"}
        yield f"WatsonX 요약 오류: {str(e)}"


# Perplexity generate
def generate_recommendations(text: str):
    if not PERPLEXITY_API_KEY:
        yield "Perplexity API 키가 설정되지 않아 추천을 생성할 수 없습니다."
        return

    print("Perplexity API로 추천 생성 중...")


    prompt = f"""
- Summarized Document: {text}
"""

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": """
1. System
당신은 요약된 문서의 내용을 분석하여, 해당 문서의 주제를 추론하고 그에 맞는 콘텐츠를 큐레이션하는 AI 캐릭터 에이전트입니다.
입력 될 정보는 사용자 보고 있는 문서의 요약 정보(Summarized Document)입니다. Summarized Document는 문서의 요약본으로, 맥락이 끊기거나 상세 내용이 부족할 수 있기에 원본 문서가 어떤 의도로 작성되었는지 추론 및 파악하여야 합니다.
Summarized Document를 기반으로, 문서에서 말하고자 하는 주제(대상)들을 추론하여, 해당 문서를 보고있는 사용자에 대한 comment와 파악한 문서의 주제들을 기반으로 하여 사용자가 관심있어 할만한 컨텐츠 recommend가 이루어져야 한다.
출력 포맷을 반드시 엄격히 지키세요.

2. Summary Guidelines
- 추천 콘텐츠(RECOMMEND)는 영상, 논문, 기사, 도구 등 주제와 관련된 다양한 플랫폼의 컨텐츠로 구성할 것
- 캐릭터는 사용자에게 직접 서비스하는 느낌으로 말할 것
- 출력 형식은 항상 규칙을 엄격하게 준수할 것
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
- 출력 시 링크는 다음 형식으로 표기
- https://portal.withorb.com/view?token=ImNSdHZ2akpEZVltTGo1aVQi.Gj2kziogRmdvF_Mn4ONENvoaOPo
- 실제 URL로 접근 가능한, 보장된 링크를 제공해야함

6. 항목 타입별 정의
- `__COMMENT`
  사용자의 브라우저 행동에 기반한 캐릭터의 짧은 코멘트 (예: “Hmm... 이 기술에 관심이 있군요.”)
- `__RECOMMEND`
  형식: `__RECOMMEND|||Title|||추천 이유|||URL`
  1. 콘텐츠 제목은 `Title`로 출력
  2. 키워드는 해당 콘텐츠의 핵심 개념을 3개 제시, 앞에는 연관 이모지 하나 포함 (예: 🤖 Claude · AI모델 · 프로토콜)
  3. 추천 이유는 해당 콘텐츠에 대한 간결하고 정확한 추천 이유를 한 줄로 제시하며, 캐릭터 The Thinker의 말투로 작성
  4. 추천은 총 3개 제시할 것. 콘텐츠 유형은 주제를 크게 벗어나지 않는 선에서 최대한 다양하게 구성 (포스팅, 기사, 영상, 도구, 논문 등)

7. Output Format (예시)
__COMMENT|||Hmm… MCP에 대해 설명하는 문서인것 같군요. 요즘 뜨거운 주제인 만큼 생각해볼 가치가 있어 보여요.
__RECOMMEND|||[IEEE 논문] Multi Chip Package 설계|||🧩 반도체 · 패키징 · 설계|||칩 내부 구조를 진지하게 풀어낸 논문이에요.|||https://ieeexplore.ieee.org/...
__RECOMMEND|||[YouTube] MCP 쉽게 이해하기|||🎥 MCP · 직관적설명 · 입문자용|||쉽지만 본질을 짚어주는 영상이에요.|||https://www.youtube.com/wa...
__RECOMMEND|||[HuggingFace 블로그] MCP란?|||🧠 문맥처리 · AI구조 · 추론기반|||문맥 기반 AI 구조에 대해 생각하게 하죠.|||https://huggingface.co/blog/mcp...
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": True
    }

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


# gRPC 서비스 구현
class DocsSummaryService(docssummary_pb2_grpc.DocsSummaryServiceServicer):
    async def SummarizeStream(self, request_iterator, context):

        try:
            mini_summaries = []
            user_id = None

            # 1단계: MT5로 mini 요약 생성
            async for req in request_iterator:
                user_id = req.user_id
                try:
                    mini_summary = summarize_mt5(req.chunk)
                    print('mini_summary---', mini_summary)
                except Exception as e:
                    print(f"MT5 요약 중 오류 발생: {e}")

                mini_summaries.append(mini_summary)
                # mini 요약을 실시간으로 전송
                yield docssummary_pb2.DocsSummaryResponse(line=mini_summary)
            print('mini_summaries---', mini_summaries)

            # 2단계: WatsonX로 final summary 생성
            # if mini_summaries and user_id:
            #     try:
            #         # mini 요약들을 하나의 텍스트로 결합
            #         combined_text = " ".join(mini_summaries)
            #
            #         print(f"Final summary 생성 시작 - 사용자: {user_id}, 텍스트 길이: {len(combined_text)}")
            #         for summary_chunk in summarize_with_watsonx(combined_text):
            #             if summary_chunk.strip():
            #                 yield docssummary_pb2.DocsSummaryResponse(
            #                     line=f"FINAL_SUMMARY: {summary_chunk}"
            #                 )
            #         print(f"Final summary 완료 - 사용자: {user_id}")
            #     except Exception as e:
            #         print(f"WatsonX 요약 중 오류 발생: {e}")
            #         yield docssummary_pb2.DocsSummaryResponse(
            #             line=f"FINAL_SUMMARY_ERROR: {str(e)}"
            #         )
            if mini_summaries and user_id:
                combined_text = " ".join(mini_summaries)

                # 두 동기 제너레이터를 각각 비동기 제너레이터로 래핑
                watsonx_stream = wrap_sync_generator(summarize_with_watsonx, combined_text)
                sonar_stream = wrap_sync_generator(generate_recommendations, combined_text)

                # 두 스트림에서 도착하는 대로 gRPC로 전달
                async def push_to_queue(tag, stream, out_queue):
                    async for chunk in stream:
                        await out_queue.put((tag, chunk))
                    await out_queue.put((tag, None))  # 종료 신호

                output_queue = asyncio.Queue()

                # 두 LLM 스트림을 병렬 실행
                task2 = asyncio.create_task(push_to_queue("SONAR", sonar_stream, output_queue))
                task1 = asyncio.create_task(push_to_queue("FINAL_SUMMARY", watsonx_stream, output_queue))


                finished = set()
                while len(finished) < 2:
                    tag, chunk = await output_queue.get()
                    if chunk is None:
                        finished.add(tag)
                        continue
                    # 메시지 포맷에 따라 구분자 붙여서 yield
                    if tag == "FINAL_SUMMARY":
                        yield docssummary_pb2.DocsSummaryResponse(line=f"FINAL_SUMMARY: {chunk}")
                    elif tag == "SONAR":
                        yield docssummary_pb2.DocsSummaryResponse(line=f"SONAR: {chunk}")

                await asyncio.gather(task1, task2)

        except Exception as e:
            print(f"Final summary 생성 오류: {e}")
            yield docssummary_pb2.DocsSummaryResponse(
                line=f"FINAL_SUMMARY_ERROR: {str(e)}"
            )


async def serve():
    server = grpc.aio.server()
    docssummary_pb2_grpc.add_DocsSummaryServiceServicer_to_server(DocsSummaryService(), server)
    server.add_insecure_port('[::]:50053')
    await server.start()
    print("gRPC DocsSummaryService running on port 50053", flush=True)
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        print("gRPC server cancelled (shutting down cleanly)")


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("Server stopped by user")