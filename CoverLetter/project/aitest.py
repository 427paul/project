import io
import json
import re
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import fitz  # PyMuPDF
import pandas as pd

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest
from django.urls import reverse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer, util
from gradio_client import Client

# 로깅 설정
logger = logging.getLogger(__name__)

# =========================
# 직무 카테고리 (Colab 원본 그대로)
# =========================
JOB_CATEGORIES: Dict[str, List[str]] = {
    "기획·전략": ["경영·비즈니스기획", "웹기획", "마케팅기획", "PL·PM·PO", "컨설턴트", "CEO·COO·CTO", "AI기획자", "AI사업전략"],
    "법무·사무·총무": ["경영지원", "사무담당자", "총무", "사무보조", "법무담당자", "비서", "변호사", "법무사", "변리사", "노무사", "AI윤리전문가"],
    "인사·HR": ["인사담당자", "HRD·HRM", "노무관리자", "잡매니저", "헤드헌터", "직업상담사"],
    "회계·세무": ["회계담당자", "경리", "세무담당자", "재무담당자", "감사", "IR·공시", "회계사", "세무사", "관세사"],
    "마케팅·광고·MD": ["AE(광고기획자)", "브랜드마케터", "퍼포먼스마케터", "CRM마케터", "온라인마케터", "콘텐츠마케터", "홍보", "설문·리서치", "MD", "카피라이터", "크리에이티브디렉터", "채널관리자", "그로스해커"],
    "AI·개발·데이터": ["백엔드개발자", "프론트엔드개발자", "웹개발자", "앱개발자", "시스템엔지니어", "네트워크엔지니어", "DBA", "데이터엔지니어", "데이터사이언티스트", "보안엔지니어", "소프트웨어개발자", "게임개발자", "하드웨어개발자", "AI/ML엔지니어", "블록체인개발자", "클라우드엔지니어", "웹퍼블리셔", "IT컨설팅", "QA", "AI/ML연구원", "데이터분석가", "데이터라벨러", "프롬프트엔지니어", "AI보안전문가", "MLOps엔지니어", "AI서비스개발자"],
    "디자인": ["그래픽디자이너", "3D디자이너", "제품디자이너", "산업디자이너", "광고디자이너", "시각디자이너", "영상디자이너", "웹디자이너", "UI·UX디자이너", "패션디자이너", "편집디자이너", "실내디자이너", "공간디자이너", "캐릭터디자이너", "환경디자이너", "아트디렉터", "일러스트레이터"],
    "물류·무역": ["물류관리자", "구매관리자", "자재관리자", "유통관리자", "무역사무원"],
    "운전·운송·배송": ["납품·배송기사", "배달기사", "수행·운전기사", "화물·중장비기사", "버스기사", "택시기사", "조종·기관사"],
    "영업": ["제품영업", "서비스영업", "해외영업", "광고영업", "금융영업", "법인영업", "IT·기술영업", "영업관리", "영업지원"],
    "고객상담·TM": ["인바운드상담원", "아웃바운드상담원", "고객센터관리자"],
    "금융·보험": ["금융사무", "보험설계사", "손해사정사", "심사", "은행원·텔러", "계리사", "펀드매니저", "애널리스트"],
    "식·음료": ["요리사", "조리사", "제과제빵사", "바리스타", "셰프·주방장", "카페·레스토랑매니저", "홀서버", "주방보조", "소믈리에·바텐더", "영양사", "식품연구원", "푸드스타일리스트"],
    "고객서비스·리테일": ["설치·수리기사", "정비기사", "호텔종사자", "여행에이전트", "매장관리자", "뷰티·미용사", "애견미용·훈련", "안내데스크·리셉셔니스트", "경호·경비", "운영보조·매니저", "이벤트·웨딩플래너", "주차·주유원", "스타일리스트", "장례지도사", "가사도우미", "승무원", "플로리스트"],
    "엔지니어링·설계": ["전기·전자엔지니어", "기계엔지니어", "설계엔지니어", "설비엔지니어", "반도체엔지니어", "화학엔지니어", "공정엔지니어", "하드웨어엔지니어", "통신엔지니어", "RF엔지니어", "필드엔지니어", "R&D·연구원", "AI로봇엔지니어"],
    "제조·생산": ["생산직종사자", "생산·공정관리자", "품질관리자", "포장·가공담당자", "공장관리자", "용접사"],
    "교육": ["유치원·보육교사", "학교·특수학교교사", "대학교수·강사", "학원강사", "외국어강사", "기술·전문강사", "학습지·방문교사", "학원상담·운영", "교직원·조교", "교재개발·교수설계", "AI교육컨설턴트"],
    "건축·시설": ["건축가", "건축기사", "시공기사", "전기기사", "토목기사", "시설관리자", "현장관리자", "안전관리자", "공무", "소방설비", "현장보조", "감리원", "도시·조경설계", "환경기사", "비파괴검사원", "공인중개사", "감정평가사", "분양매니저"],
    "의료·바이오": ["의사", "한의사", "간호사", "간호조무사", "약사·한약사", "의료기사", "수의사", "수의테크니션", "병원코디네이터", "원무행정", "기타의료종사자", "의료·약무보조", "바이오·제약연구원", "임상연구원"],
    "미디어·문화·스포츠": ["PD·감독", "포토그래퍼", "영상편집자", "사운드엔지니어", "스태프", "출판·편집", "배급·제작자", "콘텐츠에디터", "크리에이터", "기자", "작가", "아나운서", "리포터·성우", "MC·쇼호스트", "모델", "연예인·매니저", "인플루언서", "통번역사", "큐레이터", "음반기획", "스포츠강사", "AI콘텐츠크리에이터"],
    "공공·복지": ["사회복지사", "요양보호사", "환경미화원", "보건관리자", "사서", "자원봉사자", "방역·방재기사"]
}


# ===============
# 유틸
# ===============
def get_category_code_from_selection(category_name: str) -> int:
    """
    Colab 로직: category_code = 10026 + arr1 - 1
    arr1은 1부터 시작하는 카테고리 인덱스. 여기서는 0-base로 변환해서 10026 + idx 사용.
    """
    categories = list(JOB_CATEGORIES.keys())
    idx = categories.index(category_name)  # 0-based
    return 10026 + idx  # arr1-1 == idx


def extract_text_from_pdf_django(file) -> str:
    """
    Django UploadedFile → PDF 텍스트 추출 (PyMuPDF)
    """
    # 파일을 메모리로 읽어와 stream으로 열기
    content = file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()  # 메모리 해제
    return text


# ===============
# 크롤링
# ===============
@dataclass
class PassResume:
    회사: str
    연도: str
    직무: str
    질문: List[str]
    답변: List[str]
    링크: str


def get_selenium_driver() -> webdriver.Chrome:
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("lang=ko_KR")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # 프로덕션에서는 chromedriver 경로 설정이 필요할 수 있음
    driver = webdriver.Chrome(options=options)
    return driver


def crawl_passassay_links(category_code: int, pages: int = 1) -> List[str]:
    """
    목록 페이지에서 합격자소서 상세 링크 수집 (Colab 로직 충실 반영).
    """
    base_url = "https://www.jobkorea.co.kr/starter/PassAssay"
    links: List[str] = []

    driver = None
    try:
        driver = get_selenium_driver()
        for page in range(1, pages + 1):
            url = f"{base_url}?FavorCo_Stat=0&Pass_An_Stat=0&OrderBy=0&EduType=0&WorkType=0&schPart={category_code}&isSaved=1&Page={page}"
            driver.get(url)
            time.sleep(3)  # JS 렌더링 대기

            soup = BeautifulSoup(driver.page_source, "html.parser")
            ul = soup.find("ul", class_="selfLists")
            if not ul:
                continue
            li_list = ul.find_all("li")
            for li in li_list:
                tag = li.find("a", class_="logo")
                if not tag:
                    continue
                href = tag.get("href", "")
                if href:
                    links.append("https://www.jobkorea.co.kr" + href)
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    return links


def crawl_passassay_details(links: List[str]) -> List[PassResume]:
    """
    상세 페이지에서 회사/연도/직무/질문/답변 추출 (Colab 로직 충실 반영).
    """
    data: List[PassResume] = []
    driver = None
    try:
        driver = get_selenium_driver()
        for link in links:
            try:
                driver.get(link)
                time.sleep(2)

                # 상단 박스 텍스트
                try:
                    assay_info = driver.find_element(By.CSS_SELECTOR, "div.selfTopBx").text
                    lines = assay_info.splitlines()

                    # 회사 / 연도 / 직무
                    company = lines[0] if len(lines) > 0 else ""
                    title = lines[2] if len(lines) > 2 else ""  # 예: "2022년 하반기 신입 백엔드개발자합격자소서"
                    title_words = title.split()
                    year = title_words[0] if title_words else ""
                    apply_for = title_words[-1] if title_words else ""

                    # 질문
                    question_list: List[str] = []
                    question_elements = driver.find_elements(By.CSS_SELECTOR, "dt")
                    for elem in question_elements:
                        txt = elem.text
                        if txt.startswith("질문"):
                            # "질문 1." 같은 접두 제거 로직 유지
                            if len(txt) > 7:
                                question_list.append(txt[7:len(txt)-2] if txt.endswith("?") else txt[7:])

                    # 답변 - dd show 추가 후 div.tx 수집
                    script = """
                        const dds = document.querySelectorAll("dd");
                        dds.forEach(dd => dd.classList.add("show"));
                    """
                    driver.execute_script(script)
                    time.sleep(0.5)

                    answer_elements = driver.find_elements(By.CSS_SELECTOR, "div.tx")
                    answer_list = [elem.text.strip() for elem in answer_elements]
                    answer_list = answer_list[0:len(question_list)]

                    data.append(PassResume(
                        회사=company,
                        연도=year,
                        직무=apply_for[:-5] if apply_for and len(apply_for) > 5 else apply_for,  # "백엔드개발자합격자소서" → "백엔드개발자"
                        질문=question_list,
                        답변=answer_list,
                        링크=link
                    ))
                except Exception as e:
                    print(f"상세 페이지 파싱 중 오류: {e}")
                    continue
            except Exception as e:
                print(f"링크 {link} 처리 중 오류: {e}")
                continue
    except Exception as e:
        print(f"크롤링 중 전체 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    return data


# ===============
# 개선된 LLM: 항목 분류
# ===============

def create_robust_session() -> requests.Session:
    """
    타임아웃과 재시도 정책이 적용된 세션 생성
    """
    session = requests.Session()
    
    # 재시도 전략
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def _call_api_with_timeout(client, prompt: str, timeout: int = 180) -> str:
    """
    타임아웃이 적용된 API 호출
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("API 호출 타임아웃")
    
    # 시그널 설정 (Unix 계열에서만 동작)
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        result = client.predict(prompt)
        
        signal.alarm(0)  # 타임아웃 해제
        return result
        
    except AttributeError:
        # Windows 환경에서는 signal.SIGALRM이 없음
        # 단순히 호출하고 예외 처리에 의존
        return client.predict(prompt)

def _parse_llm_response(output: str) -> pd.DataFrame:
    """
    LLM 응답에서 JSON 추출 및 DataFrame 변환
    """
    try:
        # 다양한 JSON 코드블록 패턴 시도
        patterns = [
            r"```json\s*(\[\s*{.*?}\s*\])\s*```",  # 기본 패턴
            r"```\s*(\[\s*{.*?}\s*\])\s*```",      # json 키워드 없는 경우
            r"(\[\s*{.*?}\s*\])",                   # 코드블록 없는 경우
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL)
            if match:
                json_text = match.group(1).strip()
                try:
                    user_data = json.loads(json_text)
                    df = pd.DataFrame(user_data)
                    
                    # 컬럼명 정규화
                    if "항목" in df.columns and "내용" in df.columns:
                        return df
                    elif "category" in df.columns and "content" in df.columns:
                        df = df.rename(columns={"category": "항목", "content": "내용"})
                        return df
                    elif len(df.columns) >= 2:
                        # 첫 두 컬럼을 항목/내용으로 사용
                        df.columns = ["항목", "내용"] + list(df.columns[2:])
                        return df
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 파싱 실패 (패턴 {pattern}): {e}")
                    continue
        
        logger.warning("JSON 패턴을 찾을 수 없습니다.")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"LLM 응답 파싱 중 오류: {e}")
        return pd.DataFrame()

def _try_huggingface_classification(raw_text: str) -> pd.DataFrame:
    prompt = f"""다음 이력서 텍스트를 항목별로 분류하세요. 
각 항목은 '항목명'과 '내용'으로 구성하고, JSON 형태로 출력하세요.

텍스트:
{raw_text}

출력 형식:
```json
[
  {{"항목": "이름", "내용": "홍길동"}},
  {{"항목": "학력", "내용": "○○대학교 컴퓨터공학과 졸업"}},
  {{"항목": "경력", "내용": "△△회사에서 3년간 백엔드 개발 담당"}}
]
```"""
    try:
        client = Client("amd/gpt-oss-120b-chatbot")
        output = client.predict(prompt)
        logger.info(f"텍스트 항목별 분류 완료")
        #return output
    except Exception as e:
        logger.error(f"텍스트 항목별 분류 AI 호출 중 오류 발생: {e}")
        return str(e)
    try:
        return _parse_llm_response(output)
    except Exception as e:
        logger.error("분류된 텍스트 데이터화 실패")
#     """
#     Hugging Face Spaces API 호출 (타임아웃 및 재시도 로직 강화)
#     """
#     try:
#         logger.info("Hugging Face Spaces API 호출 시작...")
        
#         # 클라이언트 생성
#         client = Client("amd/gpt-oss-120b-chatbot")
        
#         # 더 간단하고 명확한 프롬프트
#         prompt = f"""다음 이력서 텍스트를 항목별로 분류하세요. 
# 각 항목은 '항목명'과 '내용'으로 구성하고, JSON 형태로 출력하세요.

# 텍스트:
# {raw_text}

# 출력 형식:
# ```json
# [
#   {{"항목": "이름", "내용": "홍길동"}},
#   {{"항목": "학력", "내용": "○○대학교 컴퓨터공학과 졸업"}},
#   {{"항목": "경력", "내용": "△△회사에서 3년간 백엔드 개발 담당"}}
# ]
# ```"""

#         # 타임아웃 적용하여 API 호출
#         start_time = time.time()
        
#         try:
#             output = _call_api_with_timeout(client, prompt, timeout=60)  # 60초 타임아웃
#         except TimeoutError:
#             logger.error("API 호출 타임아웃")
#             return pd.DataFrame()
        
#         elapsed = time.time() - start_time
#         logger.info(f"API 호출 완료 (소요시간: {elapsed:.2f}초)")

#         # JSON 추출 및 파싱
#         return _parse_llm_response(output)
        
#     except Exception as e:
#         logger.error(f"Hugging Face API 호출 실패: {e}")
#         return pd.DataFrame()

def _fallback_rule_based_classification(raw_text: str) -> pd.DataFrame:
    """
    규칙 기반 분류 (LLM 실패 시 대안)
    """
    try:
        logger.info("규칙 기반 분류 시작...")
        
        sections = []
        
        # 텍스트를 줄 단위로 분할
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        current_section = None
        current_content = []
        
        # 일반적인 이력서 섹션 키워드
        section_keywords = {
            "이름": ["이름", "성명", "name"],
            "연락처": ["연락처", "전화", "휴대폰", "phone", "mobile", "email", "이메일"],
            "주소": ["주소", "거주지", "address", "소재지"],
            "학력": ["학력", "대학교", "대학원", "졸업", "education", "학과", "전공"],
            "경력": ["경력", "근무", "회사", "career", "experience", "담당", "업무"],
            "자격증": ["자격증", "certificate", "certification", "면허", "토익", "토플"],
            "수상": ["수상", "상", "award", "achievement", "입상"],
            "프로젝트": ["프로젝트", "project", "개발", "참여"],
            "기술": ["기술", "skill", "언어", "프로그래밍", "framework"],
            "자기소개": ["자기소개", "소개", "introduction", "지원동기", "동기"],
            "성장과정": ["성장과정", "성장", "어린시절", "가정환경"],
            "성격의장단점": ["성격", "장점", "단점", "personality", "strength", "weakness"],
            "입사후포부": ["포부", "계획", "목표", "vision", "future", "앞으로"]
        }
        
        for line in lines:
            # 현재 라인이 새로운 섹션 시작인지 확인
            found_section = None
            for section_name, keywords in section_keywords.items():
                if any(keyword in line.lower() for keyword in keywords):
                    # 기존 섹션이 있다면 저장
                    if current_section and current_content:
                        content_text = ' '.join(current_content).strip()
                        if len(content_text) > 10:  # 너무 짧은 내용은 제외
                            sections.append({
                                "항목": current_section,
                                "내용": content_text
                            })
                    
                    found_section = section_name
                    current_section = section_name
                    current_content = [line]
                    break
            
            if not found_section and current_section:
                # 기존 섹션에 내용 추가
                current_content.append(line)
        
        # 마지막 섹션 저장
        if current_section and current_content:
            content_text = ' '.join(current_content).strip()
            if len(content_text) > 10:
                sections.append({
                    "항목": current_section,
                    "내용": content_text
                })
        
        # 섹션이 너무 적으면 전체를 하나로
        if len(sections) < 2:
            sections = [{"항목": "전체내용", "내용": raw_text}]
        
        logger.info(f"규칙 기반 분류 완료: {len(sections)}개 항목")
        return pd.DataFrame(sections)
        
    except Exception as e:
        logger.error(f"규칙 기반 분류 실패: {e}")
        return pd.DataFrame()

def _minimal_fallback_classification(raw_text: str) -> pd.DataFrame:
    """
    최소한의 분류 (모든 방법 실패 시)
    """
    try:
        logger.info("최소한의 분류 시작...")
        
        # 텍스트를 적절한 크기로 분할
        max_chunk_size = 1000
        chunks = []
        
        if len(raw_text) <= max_chunk_size:
            chunks = [{"항목": "전체내용", "내용": raw_text}]
        else:
            # 문단 단위로 분할 시도
            paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
            
            if len(paragraphs) > 1:
                for i, para in enumerate(paragraphs[:5]):  # 최대 5개 문단
                    if len(para) > 50:  # 충분히 긴 문단만
                        chunks.append({
                            "항목": f"섹션{i+1}",
                            "내용": para
                        })
            
            if not chunks:
                # 문단 분할 실패 시 길이로 분할
                chunk_size = len(raw_text) // 3
                chunks = [
                    {"항목": "전반부", "내용": raw_text[:chunk_size]},
                    {"항목": "중반부", "내용": raw_text[chunk_size:chunk_size*2]},
                    {"항목": "후반부", "내용": raw_text[chunk_size*2:]}
                ]
        
        logger.info(f"최소 분류 완료: {len(chunks)}개 항목")
        return pd.DataFrame(chunks)
        
    except Exception as e:
        logger.error(f"최소 분류도 실패: {e}")
        # 절대 실패하지 않는 최후의 수단
        return pd.DataFrame([{"항목": "전체", "내용": raw_text[:5000]}])

def classify_text_with_llm_to_dataframe(raw_text: str) -> pd.DataFrame:
    """
    개선된 LLM 항목 분류 함수 - 여러 fallback 옵션과 강화된 에러 처리
    """
    logger.info(f"텍스트 분류 시작 (길이: {len(raw_text)}자)")
    
    # 텍스트 길이 제한 (너무 길면 처리 시간 증가)
    if len(raw_text) > 10000:
        raw_text = raw_text[:10000] + "...(생략)"
        logger.info("텍스트가 너무 길어 10000자로 제한했습니다.")
    
    # 1차 시도: Hugging Face Spaces
    try:
        logger.info("Hugging Face Spaces API 호출 시작...")
        result_df = _try_huggingface_classification(raw_text)
        if not result_df.empty:
            logger.info("Hugging Face Spaces API 성공")
            return result_df
    except Exception as e:
        logger.warning(f"Hugging Face Spaces API 실패: {e}")
    
    # 2차 시도: 로컬 규칙 기반 분류
    try:
        logger.info("로컬 규칙 기반 분류 시도...")
        result_df = _fallback_rule_based_classification(raw_text)
        if not result_df.empty:
            logger.info("로컬 규칙 기반 분류 성공")
            return result_df
    except Exception as e:
        logger.warning(f"로컬 규칙 기반 분류 실패: {e}")
    
    # 3차 시도: 최소한의 분류
    logger.info("최소한의 분류로 fallback")
    return _minimal_fallback_classification(raw_text)


# ===============
# 유사도 매칭 & 피드백 생성 (순차 처리로 변경)
# ===============

def build_user_qa(df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Colab 로직: 내용 길이가 100자 초과인 항목만 질문/답변으로 간주.
    """
    user_qa = []
    for i in range(len(df)):
        content = str(df.iloc[i]["내용"])
        if len(content) > 100:
            user_qa.append({
                "question": str(df.iloc[i]["항목"]),
                "answer": content  # 철자 수정 (anwer -> answer)
            })
    return user_qa


def similarity_match_and_group(user_qa: List[Dict[str, str]], pass_data: List[PassResume], threshold: float = 0.5) -> pd.DataFrame:
    """
    - ko-sroberta로 사용자 질문 vs 합격자소서 질문 임베딩 후 코사인 유사도
    - threshold 이상 전부 매칭, 이후 그룹별 top3만 남김 (Colab 로직).
    """
    try:
        model = SentenceTransformer('jhgan/ko-sroberta-multitask')

        user_questions = [qa["question"] for qa in user_qa]
        user_answers = [qa["answer"] for qa in user_qa]

        pass_questions: List[str] = []
        pass_answers: List[str] = []
        for d in pass_data:
            pass_questions.extend(d.질문)
            pass_answers.extend(d.답변)

        if len(pass_questions) == 0:
            # 합격 자소서 질문이 없으면 빈 DF
            return pd.DataFrame(columns=["사용자 질문", "사용자 답변", "합격 질문", "합격 답변", "유사도"])

        user_embeds = model.encode(user_questions, convert_to_tensor=True)
        pass_embeds = model.encode(pass_questions, convert_to_tensor=True)
        cos_sim = util.cos_sim(user_embeds, pass_embeds)

        matched_data = []
        for i, user_q in enumerate(user_questions):
            sims = cos_sim[i]
            matched_indices = [j for j, score in enumerate(sims) if score >= threshold]

            if not matched_indices:
                matched_data.append({
                    "사용자 질문": user_q,
                    "사용자 답변": user_answers[i],
                    "합격 질문": None,
                    "합격 답변": None,
                    "유사도": None
                })
            else:
                for idx in matched_indices:
                    matched_data.append({
                        "사용자 질문": user_q,
                        "사용자 답변": user_answers[i],
                        "합격 질문": pass_questions[idx],
                        "합격 답변": pass_answers[idx],
                        "유사도": sims[idx].item()
                    })

        df_matched = pd.DataFrame(matched_data)

        if df_matched.empty or df_matched["유사도"].isna().all():
            return df_matched

        grouped = (
            df_matched
            .sort_values('유사도', ascending=False)
            .groupby(['사용자 질문', '사용자 답변'], group_keys=False)
            .apply(lambda g: g.nlargest(3, '유사도'))  # 각 그룹별 상위 3
            .groupby(['사용자 질문', '사용자 답변'])
            .agg({
                '합격 질문': lambda x: list(x.dropna()),
                '합격 답변': lambda x: list(x.dropna()),
                '유사도': lambda x: list(x.dropna())
            })
            .reset_index()
        )
        return grouped
    except Exception as e:
        print(f"유사도 매칭 중 오류: {e}")
        return pd.DataFrame(columns=["사용자 질문", "사용자 답변", "합격 질문", "합격 답변", "유사도"])


def generate_single_feedback_with_llm(user_question: str, user_answer: str, pass_questions: List[str], pass_answers: List[str]) -> str:
    """
    단일 질문에 대해 피드백을 생성하는 함수 (순차 처리용) - 개선된 버전
    """
    try:
        logger.info(f"피드백 생성 시작: {user_question}")
        
        client = Client("amd/gpt-oss-120b-chatbot")
        
        # 합격 자소서 여러 개를 하나의 참고 자료로 결합
        reference_examples = []
        for i, (pq, pa) in enumerate(zip(pass_questions, pass_answers)):
            reference_examples.append(f"[참고 예시 {i+1}]\n질문: {pq}\n답변: {pa}")
        
        references_text = "\n\n".join(reference_examples)
        
#         prompt = f"""다음은 사용자가 작성한 자기소개서의 한 항목과 합격한 자기소개서들의 유사한 항목들입니다.

# 【사용자 자기소개서】
# 질문: {user_question}
# 답변: {user_answer}

# 【합격 자기소개서 참고 예시들】
# {references_text}

# 위 합격 자기소개서들을 참고하여 사용자의 답변을 개선할 수 있는 구체적이고 실용적인 피드백을 작성해주세요. 
# 피드백은 다음과 같은 관점에서 작성해주세요:

# 1. 내용의 구체성과 명확성
# 2. 경험이나 성과의 수치화
# 3. 직무 관련성과 역량 어필
# 4. 문장 구성과 논리적 흐름
# 5. 차별화할 수 있는 요소

# 피드백:"""
        prompt = f"""
아래는 사용자 자소서 질문과 답변, 그리고 유사한 합격 자소서 질문과 답변입니다.
당신은 합격 자소서를 참고하여 사용자 자소서에 대해 구체적이고 건설적인 피드백을 작성해주세요.
사용자 답변과 합격 자소서 내용을 비교하고, 필요하면 목록 형태와 문장 단위를 혼합하여 작성해주세요.
전문적이고 교육적인 톤으로 작성해주세요.

사용자 자소서 질문: {user_question}
사용자 자소서 답변: {user_answer}

합격 자소서 질문: {pq}
합격 자소서 답변: {pa}

사용자 자소서를 더 잘 다듬을 수 있도록 도움말을 작성해 주세요.

        """
        try:
            #client = Client("amd/gpt-oss-120b-chatbot")
            output = client.predict(prompt)
            logger.info(f"단일 질문 피드백 생성 완료 : {user_question}")
            return output
        except Exception as e:
            logger.error(f"단일 질문 피드백 생성 실패: {e}")
            return f"'{user_question}' 항목의 피드백 생성 중 타임아웃이 발생했습니다."
        
            
        # try:
        #     response = _call_api_with_timeout(client, prompt, timeout=60)
        #     logger.info(f"피드백 생성 완료: {user_question}")
        #     return response
        # except TimeoutError:
        #     logger.error(f"피드백 생성 타임아웃: {user_question}")
        #     return f"'{user_question}' 항목의 피드백 생성 중 타임아웃이 발생했습니다. 경험을 더 구체적으로 서술하고 수치화된 성과를 포함해보세요."
        
    except Exception as e:
        logger.error(f"단일 피드백 생성 중 오류: {e}")
        return f"이 항목에 대한 피드백 생성 중 오류가 발생했습니다. 일반적인 개선 방향: 구체적인 경험 서술, 수치화된 성과, 직무 연관성 강화를 고려해보세요."


# def generate_feedbacks_with_llm_sequential(grouped_df: pd.DataFrame) -> List[Dict[str, str]]:
#     """
#     순차 처리로 피드백 생성 (타임아웃 방지) - 개선된 버전
#     """
#     final_feedbacks = []
    
#     for idx in range(len(grouped_df)):
#         user_question = grouped_df.iloc[idx]['사용자 질문']
#         user_answer = grouped_df.iloc[idx]['사용자 답변']
        
#         pass_qs = grouped_df.iloc[idx]['합격 질문'] if isinstance(grouped_df.iloc[idx]['합격 질문'], list) else []
#         pass_as = grouped_df.iloc[idx]['합격 답변'] if isinstance(grouped_df.iloc[idx]['합격 답변'], list) else []
        
#         logger.info(f"피드백 생성 중: {user_question} ({idx+1}/{len(grouped_df)})")
        
#         if pass_qs and pass_as:
#             # 최대 3개까지만 사용 (API 호출 시간 단축)
#             max_examples = min(3, len(pass_qs))
#             selected_pass_qs = pass_qs[:max_examples]
#             selected_pass_as = pass_as[:max_examples]
            
#             feedback = generate_single_feedback_with_llm(
#                 user_question, 
#                 user_answer, 
#                 selected_pass_qs, 
#                 selected_pass_as
#             )
#         else:
#             feedback = "유사한 합격 자소서를 찾지 못했습니다. 경험을 구체적인 수치로 표현하고, 해당 직무와 관련된 역량을 명확히 어필해보세요."
        
#         final_feedbacks.append({
#             "question": user_question,
#             "content": feedback
#         })
        
#         # API 호출 간격 (타임아웃 방지)
#         time.sleep(3)
    
#     return final_feedbacks


def generate_feedbacks_with_llm_sequential(grouped: pd.DataFrame, selected_category: str, selected_job: str):

    """
    순차 처리로 피드백 생성 (타임아웃 방지) - 개선된 버전
    """
    # Space 주소 (user/space_name)
    client = Client("amd/gpt-oss-120b-chatbot")

    final_feedbacks = []  # 각 사용자 질문에 대한 최종 피드백 저장

    # 전체 사용자 질문 반복
    for uq_idx in range(len(grouped['사용자 질문'])):
        user_question = grouped['사용자 질문'][uq_idx]
        user_answer = grouped['사용자 답변'][uq_idx]

        feedbacks = []  # 현재 질문에 대한 모든 피드백 저장

        # 해당 사용자 질문에 매칭된 모든 합격 자소서 질문/답변과 비교
        for pq_idx in range(len(grouped['합격 질문'][uq_idx])):
            pass_question = grouped['합격 질문'][uq_idx][pq_idx]
            pass_answer = grouped['합격 답변'][uq_idx][pq_idx]

            prompt = f"""
            아래는 사용자 자소서 질문과 답변, 그리고 유사한 합격 자소서 질문과 답변입니다.
            당신은 합격 자소서를 참고하여 사용자 자소서에 대해 구체적이고 건설적인 피드백을 작성해주세요.
            사용자 답변과 합격 자소서 내용을 비교하고, 필요하면 목록 형태와 문장 단위를 혼합하여 작성해주세요.
            전문적이고 교육적인 톤으로 작성해주세요.
            사용자는 {selected_category}의 {selected_job}에 지원했습니다.
            사용자 자소서 질문: {user_question}
            사용자 자소서 답변: {user_answer}

            합격 자소서 질문: {pass_question}
            합격 자소서 답변: {pass_answer}

            사용자 자소서를 더 잘 다듬을 수 있도록 도움말을 작성해 주세요.
            """

            output = client.predict(prompt)
            feedbacks.append(output)
            time.sleep(2)
        # 각 피드백을 요약
        summary_prompt = f"""
        아래는 동일한 사용자 자소서 질문에 대해 여러 합격 자소서 내용을 참고해 생성한 피드백들입니다.  
        이 피드백들을 바탕으로 **사용자가 실제로 바로 적용할 수 있도록**  
        ① 구체적 실행 지침 형태의 "핵심 개선 방향"과  
        ② 항목별로 정리된 "세부 보완 조언"을 작성해 주세요.  

        - "핵심 개선 방향"은 반드시 **예시 문장**을 포함해 요약적이지만 구체적인 가이드라인으로 작성합니다.  
        - "세부 보완 조언"은 표 대신 **bullet list**으로 정리하여 가독성을 높입니다.  
        - 각 bullet에서도 ** 표 사용 금지 **, 리스트 형태 혹은 bullet list를 사용하여 가독성을 해치지 않도록 합니다.
        - 표현은 전문적이고 교육적인 톤으로 작성합니다.  
        {chr(10).join(feedbacks)}
        """

        summary_output = client.predict(summary_prompt)

        # 최종 리스트에 저장
        final_feedbacks.append({
            "question": user_question,
            "content": summary_output
        })

    return final_feedbacks

# ===============
# 메인 뷰 (개선된 에러 처리 포함)
# ===============

def index(request: HttpRequest):
    context: Dict[str, Any] = {
        "job_categories": json.dumps(JOB_CATEGORIES, ensure_ascii=False),  # 템플릿에서 JavaScript로 사용
        "job_categories_dict": JOB_CATEGORIES,  # 템플릿에서 Python으로 사용
        "selected_category": None,
        "selected_job": None,
        "results_ready": False,
        "final_feedbacks": [],
        "crawl_count": 0,
        "detail_count": 0,
        "matched_count": 0,
        "notes": []
    }

    if request.method == "POST":
        selected_category = request.POST.get("category")
        selected_job = request.POST.get("job")
        pdf_file = request.FILES.get("resume")

        context["selected_category"] = selected_category
        context["selected_job"] = selected_job

        if not selected_category or not selected_job or not pdf_file:
            context["notes"].append("카테고리, 직무, PDF 파일을 모두 입력하세요.")
            return render(request, "index.html", context)

        try:
            # 1) category_code 계산
            category_code = get_category_code_from_selection(selected_category)
            context["notes"].append(f"선택된 카테고리 코드: {category_code}")

            # 2) 합격 자소서 목록 크롤링
            context["notes"].append("합격 자소서 목록을 수집하고 있습니다...")
            links = crawl_passassay_links(category_code=category_code, pages=1)
            context["crawl_count"] = len(links)
            
            if len(links) == 0:
                context["notes"].append("해당 카테고리에서 합격 자소서 목록을 찾지 못했습니다.")
                return render(request, "index.html", context)
            
            context["notes"].append(f"{len(links)}개의 합격 자소서 링크를 수집했습니다.")

            # 3) 상세 크롤링
            context["notes"].append("합격 자소서 상세 내용을 수집하고 있습니다...")
            pass_data_all = crawl_passassay_details(links)
            context["detail_count"] = len(pass_data_all)
            context["notes"].append(f"{len(pass_data_all)}개의 합격 자소서 상세 내용을 수집했습니다.")

            # 4) 직무 필터
            pass_data = [d for d in pass_data_all if d.직무 == selected_job]
            if len(pass_data) == 0:
                context["notes"].append("선택 직무와 정확히 일치하는 합격 자소서가 적어 전체 데이터를 사용합니다.")
                pass_data = pass_data_all

            # 5) 사용자 PDF 텍스트 추출
            context["notes"].append("PDF에서 텍스트를 추출하고 있습니다...")
            user_text = extract_text_from_pdf_django(pdf_file)
            context["notes"].append(f"텍스트 추출 완료 (길이: {len(user_text)}자)")

            # 6) LLM으로 항목 분류 (개선된 함수 사용)
            context["notes"].append("AI를 통해 자소서 내용을 분류하고 있습니다...")
            try:
                user_df = classify_text_with_llm_to_dataframe(user_text)
                context["notes"].append(f"{len(user_df)}개의 항목으로 분류했습니다.")
                
                # 분류 결과 로깅
                if not user_df.empty:
                    logger.info(f"분류된 항목들: {list(user_df['항목'])}")
                else:
                    logger.warning("분류 결과가 비어있습니다.")
                    
            except Exception as e:
                logger.error(f"텍스트 분류 중 치명적 오류: {e}")
                context["notes"].append(f"텍스트 분류 중 오류가 발생했습니다: {str(e)}")
                # 기본 분류로 대체
                user_df = pd.DataFrame([{"항목": "전체내용", "내용": user_text[:2000]}])
                context["notes"].append("기본 분류로 진행합니다.")

            # 7) 사용자 질문-답변만 추출(내용 길이>100)
            user_qa = build_user_qa(user_df)
            context["notes"].append(f"{len(user_qa)}개의 주요 항목을 추출했습니다.")

            if len(user_qa) == 0:
                context["notes"].append("자소서에서 충분히 긴 항목(>100자)을 찾지 못했습니다.")
                user_qa = [{"question": "전체 내용", "answer": user_text[:1000]}]

            # 8) 유사도 매칭 & 그룹화
            context["notes"].append("합격 자소서와 유사도를 분석하고 있습니다...")
            grouped_df = similarity_match_and_group(user_qa, pass_data, threshold=0.5)
            context["matched_count"] = len(grouped_df) if not grouped_df.empty else 0
            context["notes"].append(f"{context['matched_count']}개의 항목에서 유사한 합격 자소서를 찾았습니다.")

            # 9) 순차 처리로 피드백 생성
            context["notes"].append("AI를 통해 맞춤형 피드백을 순차적으로 생성하고 있습니다...")
            
            if grouped_df.empty or len(grouped_df) == 0:
                # 매칭 없으면 기본 피드백
                context["final_feedbacks"] = [{
                    "question": user_qa[0]["question"] if user_qa else "전체 내용",
                    "content": """합격 자소서와의 직접적 유사 항목이 적어 일반적인 개선 방향을 제안드립니다:

1. **구체적인 경험 서술**: 단순한 나열보다는 구체적인 상황, 행동, 결과(STAR 기법)를 활용하세요.

2. **수치화된 성과**: 가능한 모든 성과를 수치로 표현해보세요. (예: "매출 20% 증가", "효율성 30% 개선" 등)

3. **직무 연관성 강화**: 지원하는 직무와 관련된 역량과 경험을 명확히 연결지어 서술하세요.

4. **차별화 요소**: 다른 지원자와 구별되는 본인만의 독특한 경험이나 관점을 포함하세요.

5. **논리적 구성**: 각 문단이 명확한 주제를 가지고 논리적으로 연결되도록 구성하세요."""
                }]
            else:
                # 순차 처리로 피드백 생성
                try:
                    final_feedbacks = generate_feedbacks_with_llm_sequential(grouped_df, selected_category, selected_job)
                    context["final_feedbacks"] = final_feedbacks if final_feedbacks else [{
                        "question": "피드백 생성",
                        "content": "피드백 생성 중 오류가 발생했습니다. 다시 시도해주세요."
                    }]
                except Exception as e:
                    logger.error(f"피드백 생성 중 오류: {e}")
                    context["final_feedbacks"] = [{
                        "question": "피드백 생성 오류",
                        "content": f"피드백 생성 중 오류가 발생했습니다: {str(e)}. 일반적인 개선 방향을 참고해주세요."
                    }]

            context["results_ready"] = True
            context["notes"].append("분석이 완료되었습니다!")
            
        except Exception as e:
            logger.error(f"전체 처리 중 오류: {e}")
            context["notes"].append(f"처리 중 오류가 발생했습니다: {str(e)}")
            return render(request, "index.html", context)

        return render(request, "index.html", context)

    # GET 요청
    return render(request, "index.html", context)

