from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
import fitz  # PyMuPDF
import re
import json
import pandas as pd
from gradio_client import Client
from sentence_transformers import SentenceTransformer, util
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import tempfile
import os
import logging
from typing import List, Dict, Any, Optional

# 로깅 설정
logger = logging.getLogger(__name__)

job_categories = {
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

def extract_text_from_pdf(file_path: str) -> str:
    """PDF에서 텍스트를 추출하는 함수"""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        logger.error(f"PDF 텍스트 추출 실패: {e}")
        return ""

def parse_resume_with_llm(pdf_text: str) -> List[Dict[str, str]]:
    """LLM을 사용하여 이력서 텍스트를 구조화하는 함수"""
    try:
        client = Client("amd/gpt-oss-120b-chatbot")
        
        prompt = f"""아래는 이력서 원본 텍스트입니다.
        내용별로 원본 내용을 최대한 유지한 상태로 분류해서 정리해 주세요.
        각 항목은 '항목명', '내용'으로 구성된 표 형식으로 작성해 주세요.
        결과는 파이썬 pandas DataFrame에 넣을 수 있도록 아래 형식처럼 JSON 형태의 리스트로 출력해 주세요:

        예시:
        ```json
        [
        {{ "항목": "이름", "내용": "홍길동" }},
        {{ "항목": "생년월일", "내용": "1990-01-01" }},
        ]
        ```

        === 이력서 원본 텍스트 ===
        {pdf_text}
        """

        output = client.predict(prompt)
        
        # JSON 코드블록 추출
        match = re.search(r"```json\s*(\[\s*{.*?}\s*\])\s*```", output, re.DOTALL)
        
        if match:
            json_text = match.group(1).strip()
            return json.loads(json_text)
        else:
            logger.error("JSON 코드블록을 찾지 못했습니다.")
            return []
            
    except Exception as e:
        logger.error(f"LLM 파싱 실패: {e}")
        return []

def extract_qa_pairs(user_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """사용자 데이터에서 질문-답변 쌍을 추출하는 함수"""
    user_qa = []
    
    for item in user_data:
        content = item.get('내용', '')
        if len(content) > 100:  # 긴 내용만 자소서 답변으로 간주
            user_qa.append({
                'question': item.get('항목', ''),
                'answer': content
            })
    
    return user_qa



def get_chrome_driver() -> webdriver.Chrome:
    """Chrome 드라이버를 설정하고 반환"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    
    service = Service(executable_path=os.environ.get("CHROMEDRIVER_BIN", "/usr/bin/chromedriver"))
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scrape_essay_urls(category_code: int, max_pages: int = 4) -> List[str]:
    """잡코리아에서 자소서 URL들을 스크래핑하는 함수"""
    essay_urls = []
    driver = None
    
    try:
        driver = get_chrome_driver()
        
        for page in range(1, max_pages + 1):
            try:
                url = f"https://www.jobkorea.co.kr/starter/PassAssay?FavorCo_Stat=0&Pass_An_Stat=0&OrderBy=0&EduType=0&WorkType=0&schPart={category_code}&isSaved=1&Page={page}"
                driver.get(url)
                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                ul = soup.find("ul", class_="selfLists")
                
                if not ul:
                    continue
                    
                li_list = ul.find_all("li")

                for li in li_list:
                    tag = li.find("a", class_="logo")
                    if tag and tag.get('href'):
                        essay_urls.append("https://www.jobkorea.co.kr" + tag['href'])
                        
            except Exception as e:
                logger.error(f"페이지 {page} 스크래핑 실패: {e}")
                continue
                
    except Exception as e:
        logger.error(f"스크래핑 전체 실패: {e}")
    finally:
        if driver:
            driver.quit()
    
    return essay_urls

def scrape_essay_content(essay_urls: List[str]) -> List[Dict[str, Any]]:
    """자소서 URL들에서 내용을 스크래핑하는 함수"""
    data = []
    driver = None
    
    try:
        driver = get_chrome_driver()
        
        for url in essay_urls:
            try:
                driver.get(url)
                time.sleep(2)
                
                # 자소서 정보 추출
                assay_info = driver.find_element(By.CSS_SELECTOR, 'div.selfTopBx').text
                lines = assay_info.splitlines()
                
                if len(lines) < 3:
                    continue
                
                company = lines[0]
                title = lines[2]
                title_words = title.split()
                
                if len(title_words) < 2:
                    continue
                    
                year = title_words[0]
                apply_for = title_words[-1]

                # 질문 추출
                question_elements = driver.find_elements(By.CSS_SELECTOR, "dt")
                question_list = []
                
                for elem in question_elements:
                    if elem.text.startswith('질문'):
                        question_text = elem.text[7:].rstrip('?').strip()
                        if question_text:
                            question_list.append(question_text)

                # 답변 추출 (JavaScript로 모든 dd에 class="show" 추가)
                script = """
                const dds = document.querySelectorAll("dd");
                dds.forEach(dd => dd.classList.add("show"));
                """
                driver.execute_script(script)
                time.sleep(0.5)
                
                answer_elements = driver.find_elements(By.CSS_SELECTOR, "div.tx")
                answer_list = [elem.text.strip() for elem in answer_elements]
                answer_list = answer_list[:len(question_list)]

                if question_list and answer_list and len(question_list) == len(answer_list):
                    data.append({
                        "회사": company,
                        "연도": year,
                        "직무": apply_for[:-5] if apply_for.endswith('합격자소서') else apply_for,
                        "질문": question_list,
                        "답변": answer_list,
                        "링크": url
                    })
                    
            except Exception as e:
                logger.error(f"자소서 내용 추출 실패 ({url}): {e}")
                continue
                
    except Exception as e:
        logger.error(f"자소서 내용 스크래핑 전체 실패: {e}")
    finally:
        if driver:
            driver.quit()
    
    return data

def find_similar_questions(user_qa: List[Dict[str, str]], pass_data: List[Dict[str, Any]], threshold: float = 0.5) -> pd.DataFrame:
    """유사한 질문들을 찾는 함수"""
    try:
        model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        
        user_questions = [qa['question'] for qa in user_qa]
        user_answers = [qa['answer'] for qa in user_qa]

        pass_questions = []
        pass_answers = []

        for d in pass_data:
            pass_questions.extend(d['질문'])
            pass_answers.extend(d['답변'])

        if not pass_questions:
            return pd.DataFrame()

        user_embeds = model.encode(user_questions, convert_to_tensor=True)
        pass_embeds = model.encode(pass_questions, convert_to_tensor=True)
        cos_sim = util.cos_sim(user_embeds, pass_embeds)
        
        matched_data = []

        for i, user_q in enumerate(user_questions):
            sims = cos_sim[i]
            matched_indices = [j for j, score in enumerate(sims) if score >= threshold]

            if not matched_indices:
                matched_data.append({
                    '사용자 질문': user_q,
                    '사용자 답변': user_answers[i],
                    '합격 질문': None,
                    '합격 답변': None,
                    '유사도': None
                })
            else:
                for idx in matched_indices:
                    matched_data.append({
                        '사용자 질문': user_q,
                        '사용자 답변': user_answers[i],
                        '합격 질문': pass_questions[idx],
                        '합격 답변': pass_answers[idx],
                        '유사도': sims[idx].item()
                    })

        return pd.DataFrame(matched_data)
        
    except Exception as e:
        logger.error(f"유사 질문 찾기 실패: {e}")
        return pd.DataFrame()

def generate_feedback(grouped_data: pd.DataFrame) -> List[Dict[str, str]]:
    """그룹화된 데이터를 기반으로 피드백을 생성하는 함수"""
    try:
        client = Client("amd/gpt-oss-120b-chatbot")
        final_feedbacks = []

        for idx in range(len(grouped_data)):
            user_question = grouped_data.iloc[idx]['사용자 질문']
            user_answer = grouped_data.iloc[idx]['사용자 답변']
            
            feedbacks = []
            pass_questions = grouped_data.iloc[idx]['합격 질문']
            pass_answers = grouped_data.iloc[idx]['합격 답변']
            
            if not pass_questions or not pass_answers:
                continue
                
            # 각 합격 자소서와 비교
            for pq_idx in range(min(len(pass_questions), len(pass_answers))):
                pass_question = pass_questions[pq_idx]
                pass_answer = pass_answers[pq_idx]

                prompt = f"""
                아래는 사용자 자소서 질문과 답변, 그리고 유사한 합격 자소서 질문과 답변입니다.
                당신은 합격 자소서 내용을 참고하여 사용자 자소서에 대해 구체적이고 건설적인 피드백을 작성해주세요.

                사용자 자소서 질문: {user_question}
                사용자 자소서 답변: {user_answer}

                합격 자소서 질문: {pass_question}
                합격 자소서 답변: {pass_answer}

                사용자 자소서를 더 잘 다듬을 수 있도록 도움말을 작성해 주세요.
                """

                try:
                    output = client.predict(prompt)
                    feedbacks.append(output)
                    time.sleep(1)  # API 요청 간격 조절
                except Exception as e:
                    logger.error(f"피드백 생성 실패: {e}")
                    continue

            if feedbacks:
                # 피드백들을 요약
                summary_prompt = f"""
                아래는 동일한 사용자 자소서 질문에 대해 여러 합격 자소서 내용을 참고해 생성한 피드백들입니다.
                이 피드백들에서 공통적으로 나타나는 핵심적인 조언과 내용을 요약해 주세요.
                요약문은 간결하고 명확하게 작성해 주세요.

                피드백들:
                {chr(10).join(feedbacks)}

                요약:
                """
                
                try:
                    summary_output = client.predict(summary_prompt)
                    final_feedbacks.append({
                        "질문": user_question,
                        "최종 피드백": summary_output
                    })
                except Exception as e:
                    logger.error(f"피드백 요약 실패: {e}")

        return final_feedbacks
        
    except Exception as e:
        logger.error(f"피드백 생성 전체 실패: {e}")
        return []

def index(request):
    categories = list(job_categories.keys())
    selected_category = request.POST.get('category') if request.method == 'POST' else None
    selected_job = request.POST.get('job') if request.method == 'POST' else None
    selected_jobs = []
    category_code = None
    feedbacks = []

    logger.info("index 함수 호출됨")

    if request.method == 'POST':
        logger.info(f"POST 요청 확인됨: category={selected_category}, job={selected_job}")

        # 카테고리 선택 시 직무 목록 업데이트
        if selected_category and selected_category in job_categories:
            selected_jobs = job_categories[selected_category]
            category_code = 10026 + categories.index(selected_category)
            logger.info(f"선택된 카테고리 코드: {category_code}")

        # PDF 파일과 직무가 모두 선택되었을 때 분석 수행
        uploaded_file = request.FILES.get('resume_pdf')
        logger.info(f"업로드 파일 존재 여부: {'있음' if uploaded_file else '없음'}")

        if uploaded_file and selected_category and selected_job:
            try:
                # 임시 파일로 PDF 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    for chunk in uploaded_file.chunks():
                        tmp_file.write(chunk)
                    file_path = tmp_file.name
                logger.info(f"PDF 임시 파일 생성 완료: {file_path}")

                try:
                    # PDF 텍스트 추출
                    pdf_text = extract_text_from_pdf(file_path)
                    logger.info(f"PDF 텍스트 길이: {len(pdf_text)}")
                    if not pdf_text:
                        messages.error(request, "PDF에서 텍스트를 추출할 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # LLM으로 이력서 구조화
                    user_data = parse_resume_with_llm(pdf_text)
                    logger.info(f"LLM 파싱 완료, 항목 수: {len(user_data)}")
                    if not user_data:
                        messages.error(request, "이력서 내용을 분석할 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # 질문-답변 쌍 추출
                    user_qa = extract_qa_pairs(user_data)
                    logger.info(f"질문-답변 쌍 수: {len(user_qa)}")
                    if not user_qa:
                        messages.error(request, "자소서 질문-답변을 찾을 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # 자소서 URL 스크래핑
                    essay_urls = scrape_essay_urls(category_code)
                    logger.info(f"스크래핑된 자소서 URL 수: {len(essay_urls)}")
                    if not essay_urls:
                        messages.error(request, "관련 자소서를 찾을 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # 자소서 내용 스크래핑
                    pass_data = scrape_essay_content(essay_urls)
                    logger.info(f"스크래핑된 자소서 데이터 수: {len(pass_data)}")

                    # 선택된 직무와 일치하는 데이터만 필터링
                    pass_data = [d for d in pass_data if d['직무'] == selected_job]
                    logger.info(f"선택된 직무에 맞는 데이터 수: {len(pass_data)}")
                    if not pass_data:
                        messages.warning(request, "선택한 직무와 일치하는 합격 자소서를 찾을 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # 유사한 질문 찾기
                    matched_df = find_similar_questions(user_qa, pass_data)
                    logger.info(f"유사 질문 DataFrame 크기: {matched_df.shape}")
                    if matched_df.empty:
                        messages.warning(request, "유사한 질문을 찾을 수 없습니다.")
                        return render(request, 'project/index.html', {
                            'categories': categories,
                            'selected_category': selected_category,
                            'jobs': selected_jobs,
                            'selected_job': selected_job,
                            'category_code': category_code,
                        })

                    # 그룹별 상위 3개 선택
                    grouped = (
                        matched_df
                        .sort_values('유사도', ascending=False)
                        .groupby(['사용자 질문', '사용자 답변'], group_keys=False)
                        .head(3)
                        .groupby(['사용자 질문', '사용자 답변'])
                        .agg({col: lambda x: list(x.dropna()) for col in ['합격 질문', '합격 답변', '유사도']})
                        .reset_index()
                    )
                    logger.info("그룹화 완료")

                    # 피드백 생성
                    feedbacks = generate_feedback(grouped)
                    logger.info(f"생성된 피드백 수: {len(feedbacks)}")
                    
                    messages.success(request, "자소서 분석이 완료되었습니다!")

                finally:
                    # 임시 파일 삭제
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.info(f"임시 파일 삭제: {file_path}")

            except Exception as e:
                logger.error(f"자소서 분석 실패: {e}")
                messages.error(request, "자소서 분석 중 오류가 발생했습니다.")

    context = {
        'categories': categories,
        'selected_category': selected_category,
        'jobs': selected_jobs,
        'selected_job': selected_job,
        'category_code': category_code,
        'feedbacks': feedbacks,
    }
    
    return render(request, 'project/index.html', context)

# def index(request):
#     categories = list(job_categories.keys())
#     selected_category = request.POST.get('category') if request.method == 'POST' else None
#     selected_job = request.POST.get('job') if request.method == 'POST' else None
#     selected_jobs = []
#     category_code = None
#     feedbacks = []

#     logger.info("index 함수 호출됨")
#     if request.method == 'POST':
#         # 카테고리 선택 시 직무 목록 업데이트
#         if selected_category and selected_category in job_categories:
#             selected_jobs = job_categories[selected_category]
#             category_code = 10026 + categories.index(selected_category)
#             logger.info(f"선택된 카테고리 코드 : {category_code}")

#         # PDF 파일과 직무가 모두 선택되었을 때 분석 수행
#         uploaded_file = request.FILES.get('resume_pdf')
#         logger.info(f"업로드 파일 존재 여부: {'있음' if uploaded_file else '없음'}")
#         if uploaded_file and selected_category and selected_job:
#             try:
#                 # 임시 파일로 PDF 저장
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#                     for chunk in uploaded_file.chunks():
#                         tmp_file.write(chunk)
#                     file_path = tmp_file.name
#                 logger.info(f"PDF 임시 파일 생성 완료: {file_path}")

#                 try:
#                     # PDF 텍스트 추출
#                     pdf_text = extract_text_from_pdf(file_path)
#                     logger.info(f"PDF 텍스트 길이: {len(pdf_text)}")
#                     if not pdf_text:
#                         messages.error(request, "PDF에서 텍스트를 추출할 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # LLM으로 이력서 구조화
#                     user_data = parse_resume_with_llm(pdf_text)
#                     if not user_data:
#                         messages.error(request, "이력서 내용을 분석할 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # 질문-답변 쌍 추출
#                     user_qa = extract_qa_pairs(user_data)
#                     if not user_qa:
#                         messages.error(request, "자소서 질문-답변을 찾을 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # 자소서 URL 스크래핑
#                     essay_urls = scrape_essay_urls(category_code)
#                     if not essay_urls:
#                         messages.error(request, "관련 자소서를 찾을 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # 자소서 내용 스크래핑
#                     pass_data = scrape_essay_content(essay_urls)
                    
#                     # 선택된 직무와 일치하는 데이터만 필터링
#                     pass_data = [d for d in pass_data if d['직무'] == selected_job]
                    
#                     if not pass_data:
#                         messages.warning(request, "선택한 직무와 일치하는 합격 자소서를 찾을 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # 유사한 질문 찾기
#                     matched_df = find_similar_questions(user_qa, pass_data)
#                     if matched_df.empty:
#                         messages.warning(request, "유사한 질문을 찾을 수 없습니다.")
#                         return render(request, 'project/index.html', {
#                             'categories': categories,
#                             'selected_category': selected_category,
#                             'jobs': selected_jobs,
#                             'selected_job': selected_job,
#                             'category_code': category_code,
#                         })

#                     # 그룹별 상위 3개 선택
#                     grouped = (
#                         matched_df
#                         .sort_values('유사도', ascending=False)
#                         .groupby(['사용자 질문', '사용자 답변'], group_keys=False)
#                         .head(3)
#                         .groupby(['사용자 질문', '사용자 답변'])
#                         .agg({col: lambda x: list(x.dropna()) for col in ['합격 질문', '합격 답변', '유사도']})
#                         .reset_index()
#                     )

#                     # 피드백 생성
#                     feedbacks = generate_feedback(grouped)
                    
#                     messages.success(request, "자소서 분석이 완료되었습니다!")

#                 finally:
#                     # 임시 파일 삭제
#                     if os.path.exists(file_path):
#                         os.unlink(file_path)

#             except Exception as e:
#                 logger.error(f"자소서 분석 실패: {e}")
#                 messages.error(request, "자소서 분석 중 오류가 발생했습니다.")

#     context = {
#         'categories': categories,
#         'selected_category': selected_category,
#         'jobs': selected_jobs,
#         'selected_job': selected_job,
#         'category_code': category_code,
#         'feedbacks': feedbacks,
#     }
    
#     return render(request, 'project/index.html', context)