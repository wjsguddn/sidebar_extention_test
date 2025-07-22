import grpc
import asyncio
import docssummary_pb2
import docssummary_pb2_grpc

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
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

                **Output Format**
                Output ONLY in the following format without any additional titles or text:

                - Main Summary/Topic: (1-2 sentence summary of the document's main topic or purpose)
                - Key Points Summary:         
                    ◦ (Keyword1): (Brief explanation)  
                    ◦ (Keyword2): (Brief explanation)  
                    ◦ (Keyword3): (Brief explanation)    
                ||||
                <Document Start>
                {text}
                <Document End>
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

                **Output Format:**
                Main Summary/Topic:  
                (1–2 sentence summary of the document's main topic or purpose in Korean)
                Top 3 Key Points:  
                ◦ (Keyword1): (Brief explanation)  
                ◦ (Keyword2): (Brief explanation)  
                ◦ (Keyword3): (Brief explanation)
                Overall Content Summary:  
                (Summary of the whole document in Korean, using intro-body-conclusion format, max 300 characters)
                ||||
                <Document Start>
                {text}
                <Document End>
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
                ||||
                <Document Start>
                {text}
                <Document End>
                """

        # "max_new_tokens": 300은 약 1200~1500자 분량의 출력
        response_json = model.generate(
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


        try:
            # generated text
            summary = response_json["results"][0]["generated_text"]
            if "||||" in summary:
                summary = summary.split("||||")[0].strip()
            return summary

        except (KeyError, IndexError) as e:
            print("응답 파싱 실패:", str(e))
            return {
                "summary": "",
                "warnings": ["응답 형식이 예상과 다릅니다."]
            }

    except Exception as e:
        print(f"WatsonX 요약 중 오류 발생: {e}")
        return {"summary": f"WatsonX 요약 오류: {str(e)}"}


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
                print('mini_summaries---', mini_summaries)
                # mini 요약을 실시간으로 전송
                yield docssummary_pb2.DocsSummaryResponse(line=mini_summary)

            # 2단계: WatsonX로 final summary 생성
            if mini_summaries and user_id:
                try:
                    # mini 요약들을 하나의 텍스트로 결합
                    combined_text = " ".join(mini_summaries)
                    print(f"Final summary 생성 시작 - 사용자: {user_id}, 텍스트 길이: {len(combined_text)}")

                    # WatsonX로 final summary 생성
                    final_summary = summarize_with_watsonx(combined_text)
                    # final summary를 별도 응답으로 전송
                    yield docssummary_pb2.DocsSummaryResponse(
                        line=f"FINAL_SUMMARY: {final_summary}"
                    )
                    print('final_summary---', final_summary)
                    print(f"Final summary 완료 - 사용자: {user_id}")
                except Exception as e:
                    print(f"WatsonX 요약 중 오류 발생: {e}")
                    yield docssummary_pb2.DocsSummaryResponse(
                        line=f"FINAL_SUMMARY_ERROR: {str(e)}"
                    )
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