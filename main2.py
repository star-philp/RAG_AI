import os
import streamlit as st
import concurrent.futures
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from r_examples import R_EXAMPLES
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import datetime
import plotly.io as pio
from answer_handler import AnswerHandler
from document_analyzer import DocumentAnalyzer
from document_processors import (
    GeneralDocumentProcessor, 
    BusinessReportProcessor, 
    MetadataProcessor,
    FirstSentenceProcessor
)
from first_sentence_extractor import FirstSentenceExtractor
import psutil
import fitz
import re
from langchain_community.chat_models import ChatOllama
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from abc import ABC, abstractmethod
import logging
from page_processor import PageProcessor  # 새로운 임포트 추가

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Streamlit 페이지 설정
st.set_page_config(page_title="PDF 분석기", page_icon=":book:")

class SentenceExtractionStrategy:
    """문장 추출 전략 클래스"""
    
    def __init__(self):
        self.strategies = {
            "academic": AcademicPaperStrategy(),
            "technical": TechnicalReportStrategy(),
            "general": GeneralDocumentStrategy()
        }
        
    def get_strategy(self, doc_type: str):
        return self.strategies.get(doc_type, self.strategies["general"])

class BaseExtractionStrategy(ABC):
    @abstractmethod
    def extract_first_sentence(self, text: str) -> str:
        pass
    
    @abstractmethod
    def validate_sentence(self, sentence: str) -> bool:
        pass

class AcademicPaperStrategy(BaseExtractionStrategy):
    """학술 논문용 추출 전략"""
    def __init__(self):
        self.skip_patterns = [
            r'Abstract', r'Keywords', r'.*@.*',
            r'.*University.*', r'.*대학.*'
        ]
        self.end_patterns = ['다.', '까?', '니다.']
        
    def extract_first_sentence(self, text: str) -> str:
        # 학술 논문 특화 로직
        pass

class TechnicalReportStrategy(BaseExtractionStrategy):
    """기술 보고서용 추출 전략"""
    def __init__(self):
        self.skip_patterns = [
            r'목차', r'Contents', r'Figure', r'Table'
        ]
        self.end_patterns = ['다.', '이다.', '한다.']
        
    def extract_first_sentence(self, text: str) -> str:
        # 기술 보고서 특화 로직
        pass

def process_pdf(file_path):
    if not os.path.exists(file_path):
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return None, None, None, None
    
    try:
        logger.info(f"PDF 파일 처리 시작: {file_path}")
        
        # PDF 파일 열기
        doc = fitz.open(file_path)
        if not doc or len(doc) == 0:
            logger.error(f"PDF 파일을 열 수 없거나 페이지가 없습니다: {file_path}")
            st.error("PDF 파일을 열 수 없거나 페이지가 없습니다.")
            return None, None, None, None
            
        logger.info(f"PDF 페이지 수: {len(doc)}")
        
        page_processor = PageProcessor()
        text_pages = []
        structures = []
        
        # 각 페이지 처리
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                result = page_processor.process_page(page, page_num)
                
                # 결과에서 필요한 정보 추출
                structure = result.get('structure', {})
                first_sentence = result.get('first_sentence', '')
                text_length = result.get('text_length', 0)
                
                logger.info(f"페이지 {page_num}: 추출된 텍스트 길이: {text_length}")
                
                if first_sentence:
                    # 문장 시작 부분에 특수 문자나 불필요한 마침표 제거
                    first_sentence = re.sub(r'^[\s\.,;:]+', '', first_sentence)
                    # 기본적인 텍스트 정리
                    first_sentence = re.sub(r'\s+', ' ', first_sentence).strip()
                    
                    # 정제된 문장이 유의미한지 확인
                    if len(first_sentence) >= 30 and len(re.findall(r'[가-힣]+', first_sentence)) >= 3:
                        text_pages.append(first_sentence)
                        structures.append(structure)
                        logger.info(f"페이지 {page_num}에서 유효한 문장 추출: {first_sentence[:50]}...")
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {str(e)}")
                continue
        
        # 추출된 텍스트가 없는 경우 대체 방법 시도
        if not text_pages:
            logger.warning("일반 처리로 텍스트를 추출하지 못했습니다. 대체 방법 시도...")
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    # 전체 페이지 텍스트 가져오기
                    page_text = page.get_text()
                    if page_text and len(page_text) > 50:
                        # 문장 추출 시도
                        sentences = re.split(r'(?<=[.!?])\s+', page_text)
                        for sentence in sentences:
                            sentence = sentence.strip()
                            # 의미 있는 문장 필터링
                            if (len(sentence) >= 30 and 
                                len(re.findall(r'[가-힣]+', sentence)) >= 3 and
                                not any(re.match(pattern, sentence) for pattern in [
                                    r'^\s*(?:표|그림|Fig\.|Table|Figure)\s*\d+', 
                                    r'^\s*\d+\s*fps', 
                                    r'^\s*(?:\.|,|;)', 
                                    r'^\s*\[',
                                    r'^\s*\d+\.\d+',
                                    r'^\s*References',
                                    r'^\s*참고문헌'
                                ])):
                                # 기본적인 텍스트 정리
                                sentence = re.sub(r'\s+', ' ', sentence).strip()
                                sentence = re.sub(r'^[\s\.,;:]+', '', sentence)
                                
                                if len(sentence) >= 30:
                                    text_pages.append(sentence)
                                    structures.append({})
                                    logger.info(f"대체 방법으로 페이지 {page_num}에서 문장 추출: {sentence[:50]}...")
                                    break
                except Exception as e:
                    logger.error(f"대체 방법 페이지 {page_num} 처리 중 오류: {str(e)}")
                    continue
        
        full_text = "\n".join(text_pages)
        st.session_state['full_text'] = full_text
        st.session_state['text_pages'] = text_pages
        st.session_state['structures'] = structures
        
        logger.info(f"PDF 처리 완료: {file_path}")
        logger.info(f"추출된 전체 텍스트 길이: {len(full_text)} 문자")
        logger.info(f"처리된 페이지 수: {len(text_pages)}")
        
        # 텍스트가 추출되지 않은 경우 사용자에게 알림
        if not full_text:
            st.warning("PDF에서 텍스트를 추출하지 못했습니다. 다른 PDF 파일을 시도해보세요.")
            return None, None, None, None
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            length_function=len
        )
        
        docs = []
        for i, page_text in enumerate(text_pages):
            if page_text.strip():
                doc = Document(
                    page_content=page_text,
                    metadata={"source": file_path, "page": i + 1}
                )
                docs.append(doc)
        
        split_docs = text_splitter.split_documents(docs)
        
        if st.session_state.get('debug_mode', False):
            st.info(f"분할된 청크 수: {len(split_docs)}")
        
        # 문서 메타데이터 설정
        if structures and structures[0]:
            metadata = {
                "제목": structures[0].get('title', ''),
                "작성자": structures[0].get('authors', ''),
                "페이지 수": len(text_pages)
            }
            st.session_state['metadata'] = metadata
        
        return split_docs, [], full_text, ""
        
    except Exception as e:
        logger.error(f"PDF 처리 중 오류 발생: {str(e)}")
        st.error(f"PDF 처리 중 오류가 발생했습니다: {str(e)}")
        return None, None, None, None

def setup_vector_db(pages):
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        faiss_index = FAISS.from_documents(pages, embeddings)
        return faiss_index
    except Exception as e:
        st.error(f"벡터 데이터베이스 설정 중 오류가 발생했습니다: {str(e)}")
        return None

def setup_qa_chain(faiss_index):
    try:
        # 프롬프트 템플릿 수정
        prompt_template = """
        당신은 PDF 문서를 분석하고 한국어로만 답변하는 AI입니다.
        
        분석할 문서:
        {context}
        
        질문: {question}
        
        답변 규칙:
        1. 반드시 한국어로만 답변하세요.
        2. 영어 사용은 절대 금지입니다.
        3. 첫 문장을 찾을 때는 다음을 제외하고 찾으세요:
           - 논문 제목
           - 저자 정보
           - 소속 기관
           - 초록/Abstract
           - 키워드/Keywords
        4. 답변은 반드시 다음 형식을 따르세요:
           첫 번째 문장은 다음과 같습니다: [찾은 문장]
        5. 문장을 찾지 못한 경우:
           문서에서 해당 내용을 찾을 수 없습니다.
        
        답변:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Ollama 설정
        llm = ChatOllama(
            model="llama3-instruct-8b",
            temperature=0,
            context_window=4096,
            num_ctx=4096,
            stop=["I", "I'm", "Here", "Let", "The", "This"],
            system="당신은 한국어로만 답변하는 AI입니다."
        )
        
        # QA 체인 설정
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=faiss_index.as_retriever(
                search_kwargs={"k": 3}
            ),
            chain_type_kwargs={
                "prompt": PROMPT,
                "verbose": True
            },
            return_source_documents=True
        )
        
        return qa_chain
    except Exception as e:
        st.error(f"QA 체인 설정 중 오류 발생: {str(e)}")
        return None

def extract_first_sentence(doc_path: str) -> str:
    """PDF에서 첫 문장을 추출하는 최적화된 함수"""
    try:
        with fitz.open(doc_path) as doc:
            # 첫 페이지만 처리
            first_page = doc[0]
            
            # 디버그 정보 초기화
            debug_info = {
                "blocks": [],
                "filtered_blocks": [],
                "selected_block": None,
                "final_sentence": None
            }
            
            # 블록 단위로 텍스트 추출 (y좌표로 정렬)
            blocks = first_page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))  # y좌표 우선, x좌표 다음
            
            # 디버그용 블록 정보 저장
            for i, block in enumerate(blocks):
                debug_info["blocks"].append({
                    "index": i,
                    "text": block[4][:100] + "..." if len(block[4]) > 100 else block[4],
                    "bbox": block[:4],
                    "y_coord": block[1]
                })
            
            # 본문 블록 찾기
            for block in blocks:
                text = block[4].strip()
                
                # 헤더 제외
                if any(pattern in text for pattern in [
                    '@', '†', '*', '‡', '§', 'Abstract', '초록',
                    'Keywords', '키워드', 'University', '대학교',
                    'Corresponding', '저자', 'Copyright'
                ]):
                    continue
                
                # 짧은 텍스트 제외
                if len(text) < 50:
                    continue
                
                # 디버그용 필터링된 블록 저장
                debug_info["filtered_blocks"].append({
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "length": len(text)
                })
                
                # 문장 분리
                text = text.replace('\n', ' ')
                text = ' '.join(text.split())
                
                # 문장 종결 찾기
                end_markers = [
                    '다. ', '까? ', '까! ', '다! ', '다? ', '죠. ', '죠? ',
                    '요. ', '요? ', '니다. ', '습니다. ', '입니다. ',
                    '. ', '? ', '! '
                ]
                min_pos = len(text)
                found_end = False
                
                for marker in end_markers:
                    pos = text.find(marker)
                    if pos != -1 and pos < min_pos:
                        min_pos = pos + len(marker)
                        found_end = True
                
                if found_end:
                    sentence = text[:min_pos].strip()
                    
                    # 유효성 검사
                    if (len(sentence) >= 50 and
                        not any(sentence.startswith(p) for p in [
                            '그림', '표', 'Fig.', 'Table', 'Figure',
                            'Abstract', '초록', '요약', 'Keywords', '키워드'
                        ])):
                        # 디버그용 선택된 블록 저장
                        debug_info["selected_block"] = {
                            "text": sentence,
                            "length": len(sentence),
                            "end_marker_found": True
                        }
                        debug_info["final_sentence"] = sentence
                        
                        if st.session_state.get('debug_mode', False):
                            st.info("첫 문장 추출 디버그 정보:")
                            st.json(debug_info)
                        
                        return sentence
            
            if st.session_state.get('debug_mode', False):
                st.warning("유효한 첫 문장을 찾지 못했습니다.")
                st.json(debug_info)
            
            return ""
            
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.error(f"첫 문장 추출 중 오류: {str(e)}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")
        return ""

def answer_first_sentence_question(question: str) -> str:
    """특정 페이지의 첫 문장을 찾는 함수"""
    try:
        # 페이지 번호 추출
        match = re.search(r'(\d+)페이지', question)
        if not match:
            return "페이지 번호를 찾을 수 없습니다. '몇 페이지의 첫 문장은?' 형식으로 질문해주세요."
        
        page_num = int(match.group(1)) - 1  # 0-based index로 변환
        
        # 저장된 페이지 텍스트 확인
        if 'text_pages' not in st.session_state:
            return "처리된 텍스트가 없습니다. PDF를 먼저 업로드해주세요."
        
        text_pages = st.session_state['text_pages']
        if not text_pages:
            return "추출된 텍스트가 없습니다. 다른 PDF 파일을 시도해보세요."
            
        if page_num >= len(text_pages):
            return f"{page_num + 1}페이지가 존재하지 않습니다. 현재 PDF는 {len(text_pages)}페이지까지 처리되었습니다."
        
        # 해당 페이지의 첫 문장 반환
        first_sentence = text_pages[page_num]
        if not first_sentence:
            # 페이지가 있지만 첫 문장이 추출되지 않은 경우 직접 추출 시도
            try:
                logger.info(f"페이지 {page_num + 1}의 첫 문장이 없어 직접 추출 시도")
                
                # 임시 PDF 파일 확인
                if not os.path.exists("temp.pdf"):
                    return f"{page_num + 1}페이지에서 의미 있는 문장을 찾을 수 없습니다. PDF를 다시 업로드해주세요."
                
                # PDF 파일 열기
                doc = fitz.open("temp.pdf")
                if page_num >= len(doc):
                    return f"{page_num + 1}페이지가 존재하지 않습니다. PDF에는 {len(doc)}페이지가 있습니다."
                
                # 페이지 가져오기
                page = doc[page_num]
                
                # 페이지 프로세서 생성
                page_processor = PageProcessor()
                
                # 페이지 처리
                result = page_processor.process_page(page, page_num)
                
                # 결과에서 첫 문장 추출
                first_sentence = result.get('first_sentence', '')
                
                if first_sentence:
                    # 세션 상태 업데이트
                    text_pages[page_num] = first_sentence
                    st.session_state['text_pages'] = text_pages
                    
                    # 전체 텍스트 업데이트
                    full_text = "\n".join(text_pages)
                    st.session_state['full_text'] = full_text
                    
                    logger.info(f"페이지 {page_num + 1}의 첫 문장 직접 추출 성공: {first_sentence}")
                else:
                    return f"{page_num + 1}페이지에서 의미 있는 문장을 찾을 수 없습니다."
            except Exception as e:
                logger.error(f"페이지 {page_num + 1} 직접 추출 중 오류: {str(e)}")
                return f"{page_num + 1}페이지에서 의미 있는 문장을 찾을 수 없습니다. 오류: {str(e)}"
            
        # 첫 문장 정제
        first_sentence = first_sentence.strip()
        
        # 마침표로 시작하는 경우 제거
        first_sentence = re.sub(r'^\.+\s*', '', first_sentence)
        
        # 숫자나 특수 문자로만 시작하는 경우 제거
        first_sentence = re.sub(r'^[0-9\s\.\,\:\;\-\(\)]+', '', first_sentence)
        
        # 공백 정리
        first_sentence = re.sub(r'\s+', ' ', first_sentence).strip()
        
        # 너무 짧은 문장이거나 의미 없는 문장인 경우
        if len(first_sentence) < 20 or len(re.findall(r'[가-힣]+', first_sentence)) < 3:
            return f"{page_num + 1}페이지에서 의미 있는 문장을 찾을 수 없습니다."
            
        logger.info(f"전체 텍스트 길이: {len(st.session_state.get('full_text', ''))}")
        logger.info(f"페이지 {page_num + 1}의 첫 문장: {first_sentence}")
        
        return f"페이지 {page_num + 1}의 첫 문장: {first_sentence}"
    except Exception as e:
        logger.error(f"첫 문장 추출 중 오류 발생: {str(e)}")
        return f"첫 문장 추출 중 오류 발생: {str(e)}"

def answer_question(question: str) -> str:
    try:
        with st.spinner('답변을 생성하는 중...'):
            result = st.session_state['qa_chain'].invoke({"query": question})
            
            if result and isinstance(result, dict) and "result" in result:
                st.markdown("### 답변")
                st.markdown(result["result"])
                return result["result"]
            elif isinstance(result, str):
                st.markdown("### 답변")
                st.markdown(result)
                return result
            else:
                st.error("답변을 생성할 수 없습니다.")
                return "답변을 생성할 수 없습니다."
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        if st.session_state.get('debug_mode', False):
            st.json(result)
        return f"오류가 발생했습니다: {str(e)}"

def analyze_csv(file_path):
    try:
        # 여러 인코딩 시도
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            st.error("CSV 파일을 읽을 수 없습니다. 지원되는 인코딩: UTF-8, CP949, EUC-KR")
            return None, None, None
        
        # 기본 통계 분석
        stats = {
            "행 수": len(df),
            "열 수": len(df.columns),
            "수치형 컬럼": df.select_dtypes(include=['int64', 'float64']).columns.tolist(),
            "범주형 컬럼": df.select_dtypes(include=['object']).columns.tolist()
        }
        
        # 시각화
        charts = {}
        
        # 수치형 데이터 분포
        for col in stats["수치형 컬럼"]:
            try:
                fig = px.histogram(df, x=col, title=f"{col} 분포")
                charts[f"{col}_hist"] = fig
                
                # 박스플롯
                fig = px.box(df, y=col, title=f"{col} 박스플롯")
                charts[f"{col}_box"] = fig
            except Exception as e:
                st.warning(f"{col} 컬럼 시각화 중 오류 발생: {str(e)}")
        
        # 범주형 데이터 분포
        for col in stats["범주형 컬럼"]:
            try:
                value_counts = df[col].value_counts()
                if len(value_counts) <= 30:  # 범주가 너무 많지 않은 경우만
                    fig = px.bar(value_counts, title=f"{col} 빈도")
                    charts[f"{col}_bar"] = fig
            except Exception as e:
                st.warning(f"{col} 컬럼 시각화 중 오류 발생: {str(e)}")
        
        # 상관관계 히트맵
        if len(stats["수치형 컬럼"]) > 1:
            try:
                corr_matrix = df[stats["수치형 컬럼"]].corr()
                fig = px.imshow(corr_matrix,
                              title="상관관계 히트맵",
                              labels=dict(color="상관계수"))
                charts["correlation"] = fig
            except Exception as e:
                st.warning(f"상관관계 분석 중 오류 발생: {str(e)}")
        
        return df, stats, charts
    except Exception as e:
        st.error(f"CSV 분석 중 오류가 발생했습니다: {str(e)}")
        return None, None, None

def create_analysis_report(df, stats, charts, file_name):
    try:
        # 한글 폰트 설정
        st.info("폰트 설정 시작...")
        font_path = setup_korean_font()
        if not font_path:
            st.error("폰트 설정 실패")
            return None
        st.success(f"폰트 설정 완료: {font_path}")
        
        # PDF 생성
        st.info("PDF 생성 시작...")
        pdf = FPDF()
        pdf.add_page()
        
        try:
            # 한글 폰트 추가
            pdf.add_font("NanumGothic", "", font_path, uni=True)
            st.success("폰트 추가 완료")
        except Exception as e:
            st.error(f"폰트 추가 실패: {str(e)}")
            return None
        
        # 제목
        pdf.set_font("NanumGothic", size=16)
        pdf.cell(0, 10, '데이터 분석 보고서', ln=True, align='C')
        pdf.ln(10)
        
        # 기본 정보
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '1. 기본 정보', ln=True)
        pdf.set_font("NanumGothic", size=10)
        pdf.cell(0, 10, f"분석 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.cell(0, 10, f"데이터 크기: {stats['행 수']}행 x {stats['열 수']}열", ln=True)
        
        # 컬럼 정보
        pdf.ln(5)
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '2. 컬럼 정보', ln=True)
        pdf.set_font("NanumGothic", size=10)
        
        pdf.cell(0, 10, '수치형 컬럼:', ln=True)
        for col in stats['수치형 컬럼']:
            pdf.cell(0, 10, f"- {col}", ln=True)
        
        pdf.cell(0, 10, '범주형 컬럼:', ln=True)
        for col in stats['범주형 컬럼']:
            pdf.cell(0, 10, f"- {col}", ln=True)
        
        # 기술 통계량
        pdf.ln(5)
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '3. 기술 통계량', ln=True)
        pdf.set_font("NanumGothic", size=10)
        
        desc_stats = df.describe()
        pdf.cell(0, 10, '수치형 변수 통계:', ln=True)
        for col in stats['수치형 컬럼']:
            pdf.cell(0, 10, f"{col}:", ln=True)
            for stat, value in desc_stats[col].items():
                pdf.cell(0, 10, f"  {stat}: {value:.2f}", ln=True)
            pdf.ln(5)
        
        # 시각화
        pdf.add_page()
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '4. 데이터 시각화', ln=True)
        
        # 차트 저장 및 추가
        for name, fig in charts.items():
            try:
                img_path = f"temp_{name}.png"
                pio.write_image(fig, img_path)
                pdf.image(img_path, x=10, y=None, w=190)
                pdf.ln(5)
                os.remove(img_path)
            except Exception as e:
                st.warning(f"{name} 차트 저장 중 오류 발생: {str(e)}")
        
        # 결측치 분석
        pdf.add_page()
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '5. 결측치 분석', ln=True)
        pdf.set_font("NanumGothic", size=10)
        
        missing_data = df.isnull().sum()
        for col, count in missing_data.items():
            pdf.cell(0, 10, f"{col}: {count}개 ({(count/len(df)*100):.2f}%)", ln=True)
        
        # 통찰력 분석 추가
        pdf.add_page()
        pdf.set_font("NanumGothic", size=12)
        pdf.cell(0, 10, '6. 데이터 분석 통찰', ln=True)
        pdf.set_font("NanumGothic", size=10)
        
        insights = generate_insights(df, stats, charts)
        for line in insights.split('\n'):
            if line.startswith('###'):
                pdf.ln(5)
                pdf.set_font("NanumGothic", size=12)
                pdf.cell(0, 10, line.replace('###', '').strip(), ln=True)
                pdf.set_font("NanumGothic", size=10)
            elif line.startswith('**'):
                pdf.ln(3)
                pdf.set_font("NanumGothic", size=11)
                pdf.cell(0, 10, line.replace('**', ''), ln=True)
                pdf.set_font("NanumGothic", size=10)
            else:
                pdf.cell(0, 10, line, ln=True)
        
        # PDF 저장
        st.info("PDF 저장 시작...")
        report_path = f"reports/{file_name}_분석리포트.pdf"
        os.makedirs('reports', exist_ok=True)
        pdf.output(report_path)
        st.success(f"PDF 저장 완료: {report_path}")
        
        return report_path
    
    except Exception as e:
        st.error(f"보고서 생성 중 오류가 발생했습니다: {str(e)}")
        import traceback
        st.error(f"상세 오류: {traceback.format_exc()}")
        return None

def setup_korean_font():
    try:
        # 폰트 파일 경로
        font_path = "fonts/NanumGothic.ttf"
        if not os.path.exists("fonts"):
            os.makedirs("fonts")
        
        if not os.path.exists(font_path):
            # 시스템 폰트 검색
            system_fonts = [
                # Windows
                "C:/Windows/Fonts/malgun.ttf",
                "C:/Windows/Fonts/gulim.ttc",
                # macOS
                "/Library/Fonts/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                # Linux
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
            ]
            
            # 시스템 폰트 찾기
            for system_font in system_fonts:
                if os.path.exists(system_font):
                    import shutil
                    try:
                        shutil.copy2(system_font, font_path)
                        st.success(f"시스템 폰트를 복사했습니다: {system_font}")
                        return font_path
                    except Exception as e:
                        st.warning(f"폰트 복사 중 오류: {str(e)}")
                        continue
            
            # 나눔고딕 폰트 다운로드
            try:
                import requests
                # 구글 웹폰트 CDN에서 다운로드
                font_url = "https://fonts.gstatic.com/ea/nanumgothic/v5/NanumGothic-Regular.ttf"
                response = requests.get(font_url)
                if response.status_code == 200:
                    with open(font_path, 'wb') as f:
                        f.write(response.content)
                    st.success("나눔고딕 폰트를 다운로드했습니다.")
                    return font_path
            except Exception as e:
                st.warning(f"나눔고딕 폰트 다운로드 실패: {str(e)}")
            
            # 대체 폰트 다운로드
            try:
                import requests
                # DejaVu Sans 폰트 다운로드
                dejavu_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
                response = requests.get(dejavu_url)
                if response.status_code == 200:
                    with open(font_path, 'wb') as f:
                        f.write(response.content)
                    st.warning("한글 폰트를 찾을 수 없어 DejaVu 폰트를 사용합니다.")
                    return font_path
            except Exception as e:
                st.error(f"대체 폰트 다운로드 실패: {str(e)}")
        
        # 이미 폰트 파일이 있는 경우
        if os.path.exists(font_path):
            return font_path
        
        st.error("사용 가능한 폰트를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        st.error(f"폰트 설정 중 오류가 발생했습니다: {str(e)}")
        return None

def generate_insights(df, stats, charts):
    """데이터 분석 결과에 대한 통찰력 생성"""
    insights = []
    
    try:
        # 기본 데이터 특성
        insights.append(f"### 1. 데이터 개요")
        insights.append(f"- 총 {stats['행 수']:,}개의 데이터와 {stats['열 수']}개의 특성이 있습니다.")
        insights.append(f"- 수치형 데이터 {len(stats['수치형 컬럼'])}개, 범주형 데이터 {len(stats['범주형 컬럼'])}개로 구성되어 있습니다.")
        
        # 수치형 데이터 분석
        insights.append(f"\n### 2. 주요 수치 분석")
        desc = df.describe()
        for col in stats['수치형 컬럼']:
            mean_val = desc[col]['mean']
            std_val = desc[col]['std']
            min_val = desc[col]['min']
            max_val = desc[col]['max']
            
            insights.append(f"\n**{col}** 분석:")
            insights.append(f"- 평균: {mean_val:.2f} (표준편차: {std_val:.2f})")
            insights.append(f"- 범위: {min_val:.2f} ~ {max_val:.2f}")
            
            # 이상치 확인
            q1 = desc[col]['25%']
            q3 = desc[col]['75%']
            iqr = q3 - q1
            outliers = df[(df[col] < q1 - 1.5*iqr) | (df[col] > q3 + 1.5*iqr)][col]
            if len(outliers) > 0:
                insights.append(f"- 이상치: {len(outliers)}개 발견 ({(len(outliers)/len(df)*100):.1f}%)")
        
        # 범주형 데이터 분석
        insights.append(f"\n### 3. 범주형 데이터 분석")
        for col in stats['범주형 컬럼']:
            value_counts = df[col].value_counts()
            insights.append(f"\n**{col}** 분포:")
            for val, count in value_counts.head(5).items():
                insights.append(f"- {val}: {count:,}개 ({(count/len(df)*100):.1f}%)")
            if len(value_counts) > 5:
                insights.append(f"- 기타: {len(value_counts)-5}개 범주 더 있음")
        
        # 상관관계 분석
        if len(stats['수치형 컬럼']) > 1:
            insights.append(f"\n### 4. 주요 상관관계")
            corr = df[stats['수치형 컬럼']].corr()
            for i in range(len(stats['수치형 컬럼'])):
                for j in range(i+1, len(stats['수치형 컬럼'])):
                    col1 = stats['수치형 컬럼'][i]
                    col2 = stats['수치형 컬럼'][j]
                    corr_val = corr.iloc[i,j]
                    if abs(corr_val) > 0.5:  # 강한 상관관계만 표시
                        insights.append(f"- {col1}와(과) {col2}: {corr_val:.2f} " + 
                                     f"({'강한 양의' if corr_val > 0 else '강한 음의'} 상관관계)")
        
        # 결측치 분석
        missing_data = df.isnull().sum()
        missing_cols = missing_data[missing_data > 0]
        if len(missing_cols) > 0:
            insights.append(f"\n### 5. 결측치 현황")
            for col, count in missing_cols.items():
                insights.append(f"- {col}: {count:,}개 ({(count/len(df)*100):.1f}%)")
        
        return "\n".join(insights)
    
    except Exception as e:
        return f"통찰력 생성 중 오류 발생: {str(e)}"

def initialize_analyzer():
    analyzer = DocumentAnalyzer()
    
    # 프로세서 등록
    analyzer.register_processor("metadata", MetadataProcessor())  # 메타데이터 프로세서 추가
    analyzer.register_processor("general", GeneralDocumentProcessor())
    analyzer.register_processor("report", BusinessReportProcessor())
    
    return analyzer

def main():
    st.title("PDF & CSV 분석기")
    
    # 디버그 모드 토글
    debug_mode = st.sidebar.checkbox("디버그 모드", value=False)
    st.session_state['debug_mode'] = debug_mode
    
    if debug_mode:
        st.sidebar.info("서버 상태:")
        st.sidebar.text(f"메모리 사용량: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB")
        st.sidebar.text(f"CPU 사용량: {psutil.cpu_percent()}%")
    
    # 파일 형식 선택
    file_type = st.radio(
        "파일 형식 선택",
        ["PDF", "CSV"],
        horizontal=True,
        help="분석할 파일의 형식을 선택하세요."
    )
    
    if file_type == "PDF":
        st.subheader("PDF 문서 분석")
        analyzer = initialize_analyzer()
        
        uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")
        
        if uploaded_file is not None:
            # 진행 상태 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 1단계: 파일 저장
                status_text.text("PDF 파일 처리 중...")
                with open("temp.pdf", "wb") as f:
                    f.write(uploaded_file.getvalue())
                progress_bar.progress(20)
                
                # 2단계: 문서 분석
                status_text.text("문서 구조 분석 중...")
                result = analyzer.analyze_document("temp.pdf")
                progress_bar.progress(40)
                
                # 3단계: 메타데이터 표시
                status_text.text("메타데이터 추출 중...")
                st.subheader("문서 메타데이터")
                
                if "metadata" in result:
                    metadata = result["metadata"]
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**제목:** {metadata.get('title', '제목 없음')}")
                        st.markdown(f"**작성자:** {metadata.get('author', '작성자 정보 없음')}")
                    with col2:
                        st.markdown(f"**페이지 수:** {metadata.get('page_count', '알 수 없음')}")
                progress_bar.progress(60)
                
                # 4단계: 문서 구조 표시
                status_text.text("문서 구조 분석 중...")
                st.subheader("문서 구조")
                if "structure" in result:
                    structure = result["structure"]
                    
                    if structure.get("title"):
                        st.markdown("**문서 제목:**")
                        st.markdown(f"- {structure['title']}")
                    
                    if structure.get("sections"):
                        st.markdown("**목차:**")
                        for section in structure["sections"]:
                            indent = "  " * (section.count('.') - 1)
                            st.markdown(f"{indent}- {section}")
                    else:
                        st.info("목차를 추출할 수 없습니다.")
                progress_bar.progress(80)
                
                # 5단계: PDF 처리 및 벡터 DB 설정
                status_text.text("질문-답변 시스템 준비 중...")
                pages, _, text, _ = process_pdf("temp.pdf")
                if pages:
                    faiss_index = setup_vector_db(pages)
                    if faiss_index:
                        qa_chain = setup_qa_chain(faiss_index)
                        st.session_state['qa_chain'] = qa_chain
                        progress_bar.progress(100)
                        status_text.text("분석이 완료되었습니다. 질문을 입력해주세요.")
                        
                        # 질문-답변 섹션
                        st.subheader("문서 질문하기")
                        st.info("문서의 내용에 대해 질문해 보세요.")
                        
                        # 질문 입력창
                        user_question = st.text_input("질문을 입력하세요")
                        
                        if user_question:
                            st.subheader("답변")
                            
                            # 첫 문장 질문 직접 처리
                            if '첫 문장' in user_question.lower() or '첫번째 문장' in user_question.lower() or '첫 번째 문장' in user_question.lower():
                                with st.spinner("첫 문장을 추출하는 중..."):
                                    if 'full_text' in st.session_state:
                                        # 로그 추가
                                        logger.info(f"첫 문장 질문 감지: {user_question}")
                                        logger.info(f"전체 텍스트 길이: {len(st.session_state['full_text'])}")
                                        
                                        answer = answer_first_sentence_question(user_question)
                                        st.markdown(answer)
                                        
                                        # 디버그 모드에서 추가 정보 표시
                                        if st.session_state.get('debug_mode', False):
                                            st.info("첫 문장 추출 직접 처리 완료")
                                    else:
                                        st.error("문서가 로드되지 않았습니다. 먼저 PDF를 업로드해주세요.")
                            else:
                                # 일반 질문 처리
                                with st.spinner("답변을 생성하는 중..."):
                                    if 'qa_chain' in st.session_state:
                                        with st.spinner("답변을 생성하는 중..."):
                                            try:
                                                result = st.session_state['qa_chain'].invoke({"query": user_question})
                                                
                                                st.write("### 답변")
                                                if isinstance(result, dict):
                                                    if "result" in result and result["result"]:
                                                        st.markdown(result["result"])
                                                    elif "answer" in result and result["answer"]:
                                                        st.markdown(result["answer"])
                                                    elif "source_documents" in result:
                                                        # 문서에서 직접 답변 추출 시도
                                                        for doc in result["source_documents"]:
                                                            if "본논문은" in doc.page_content:
                                                                st.markdown(f"이 논문에서는 {doc.page_content.split('본논문은')[1].strip()}")
                                                                break
                                                    else:
                                                        st.markdown("답변을 찾을 수 없습니다.")
                                                elif isinstance(result, str):
                                                    st.markdown(result)
                                                else:
                                                    st.error("답변을 생성할 수 없습니다.")
                                                
                                                # 디버그 모드에서 전체 결과 표시
                                                if st.session_state.get('debug_mode', False):
                                                    st.write("### 디버그 정보")
                                                    st.json(result)
                                                    
                                            except Exception as e:
                                                st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
                                                if st.session_state.get('debug_mode', False):
                                                    st.write("### 오류 상세 정보")
                                                    st.exception(e)
                                    else:
                                        st.error("QA 체인이 설정되지 않았습니다. 문서를 먼저 업로드해주세요.")
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("오류가 발생했습니다.")
                st.error(f"문서 처리 중 오류가 발생했습니다: {str(e)}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
    
    else:  # CSV 선택
        st.subheader("CSV 데이터 분석")
        uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type="csv")
        
        if uploaded_file is not None:
            # 임시 파일로 저장
            with open("temp.csv", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # CSV 분석
            df, stats, charts = analyze_csv("temp.csv")
            
            if df is not None:
                # 기본 정보 표시
                st.subheader("데이터 기본 정보")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"행 수: {stats['행 수']:,}")
                    st.write(f"열 수: {stats['열 수']}")
                with col2:
                    st.write(f"수치형 컬럼: {len(stats['수치형 컬럼'])}")
                    st.write(f"범주형 컬럼: {len(stats['범주형 컬럼'])}")
                
                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                st.dataframe(df.head())
                
                # 시각화
                st.subheader("데이터 시각화")
                for name, fig in charts.items():
                    st.plotly_chart(fig)
                
                # 분석 리포트 생성
                st.subheader("분석 리포트")
                if st.button("PDF 리포트 생성"):
                    with st.spinner("리포트 생성 중..."):
                        report_path = create_analysis_report(
                            df, stats, charts, 
                            uploaded_file.name.split('.')[0]
                        )
                        if report_path:
                            st.success(f"리포트가 생성되었습니다: {report_path}")
                            
if __name__ == "__main__":
    main()

class ExtractionLogger:
    """추출 과정 로깅 클래스"""
    
    def __init__(self):
        self.logs = {
            "metadata": [],
            "content": [],
            "errors": []
        }
        
    def log_metadata(self, info: dict):
        self.logs["metadata"].append(info)
        
    def log_content(self, info: dict):
        self.logs["content"].append(info)
        
    def log_error(self, error: str):
        self.logs["errors"].append(error)
        
    def get_summary(self) -> dict:
        return {
            "metadata_count": len(self.logs["metadata"]),
            "content_count": len(self.logs["content"]),
            "error_count": len(self.logs["errors"])
        }

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.metrics = {
            "extraction_time": [],
            "success_rate": [],
            "error_rate": []
        }
        
    def record_extraction(self, duration: float, success: bool):
        self.metrics["extraction_time"].append(duration)
        self.metrics["success_rate"].append(1 if success else 0)
        self.metrics["error_rate"].append(0 if success else 1)
        
    def get_statistics(self) -> dict:
        return {
            "avg_extraction_time": sum(self.metrics["extraction_time"]) / len(self.metrics["extraction_time"]),
            "success_rate": sum(self.metrics["success_rate"]) / len(self.metrics["success_rate"]),
            "error_rate": sum(self.metrics["error_rate"]) / len(self.metrics["error_rate"])
        }

class DocumentClassifier:
    """문서 유형 분류 클래스"""
    
    def __init__(self):
        self.patterns = {
            "academic": [
                r'Abstract', r'Keywords', r'References',
                r'서론', r'결론', r'참고문헌'
            ],
            "technical": [
                r'목차', r'Contents', r'Figure',
                r'시스템', r'구현', r'실험'
            ]
        }
        
    def classify(self, text: str) -> str:
        scores = {
            "academic": 0,
            "technical": 0,
            "general": 0
        }
        
        for doc_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    scores[doc_type] += 1
                    
        return max(scores.items(), key=lambda x: x[1])[0]
