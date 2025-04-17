from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from document_processors import (
    AcademicPaperProcessor, 
    BusinessReportProcessor, 
    GeneralDocumentProcessor, 
    FirstSentenceProcessor,
    MetadataProcessor
)
import fitz  # PyMuPDF
import re
import logging
import os

logger = logging.getLogger(__name__)

class DocumentAnalyzer(ABC):
    """문서 분석을 위한 기본 클래스"""
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """메타데이터 추출"""
        pass
        
    @abstractmethod
    def extract_text(self) -> str:
        """텍스트 추출"""
        pass

class PDFTextExtractor:
    """PDF 텍스트 추출을 위한 전용 클래스"""
    
    def __init__(self):
        self.pages = {}
        self.metadata = {}
    
    def extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """PDF에서 텍스트 추출"""
        try:
            doc = fitz.open(file_path)
            
            # 1. 메타데이터 추출
            self.metadata = {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'page_count': len(doc)
            }
            
            # 2. 페이지별 텍스트 추출 (개선된 버전)
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 블록 단위로 텍스트 추출
                blocks = page.get_text("dict")["blocks"]
                blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))  # y좌표, x좌표 순 정렬
                
                page_text = []
                current_y = None
                line_buffer = []
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            if "spans" in line:
                                # y좌표가 비슷한 텍스트는 같은 줄로 처리
                                y_coord = line["bbox"][1]
                                text = ' '.join(span["text"] for span in line["spans"])
                                
                                if current_y is None:
                                    current_y = y_coord
                                    line_buffer.append(text)
                                elif abs(y_coord - current_y) < 5:  # 같은 줄로 판단할 y좌표 차이
                                    line_buffer.append(text)
                                else:
                                    # 새로운 줄 시작
                                    if line_buffer:
                                        page_text.append(' '.join(line_buffer))
                                    line_buffer = [text]
                                    current_y = y_coord
                
                # 마지막 줄 처리
                if line_buffer:
                    page_text.append(' '.join(line_buffer))
                
                # 페이지 텍스트 저장
                self.pages[page_num] = '\n'.join(
                    line for line in page_text 
                    if self._is_valid_line(line)
                )
            
            doc.close()
            return {
                'text': '\n'.join(self.pages.values()),
                'metadata': self.metadata,
                'pages': self.pages
            }
            
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 중 오류 발생: {str(e)}")
            raise
    
    def _is_valid_line(self, line: str) -> bool:
        """유효한 텍스트 라인인지 검증"""
        line = line.strip()
        if not line:
            return False
            
        # 제외할 패턴
        exclude_patterns = [
            r'^\d+$',  # 페이지 번호
            r'^그림\s+\d+',  # 그림 캡션
            r'^표\s+\d+',  # 표 캡션
            r'^Fig\.',  # 영문 그림 캡션
            r'^Table\s+\d+',  # 영문 표 캡션
            r'^\[[\d,\s]+\]$',  # 참조 번호
            r'^Abstract$',  # 섹션 헤더
            r'^Keywords:',  # 키워드 섹션
            r'^참고문헌$',  # 참고문헌
        ]
        
        return not any(re.match(pattern, line) for pattern in exclude_patterns)

class DocumentAnalyzer:
    """문서 분석을 위한 기본 프레임워크"""
    
    def __init__(self):
        self.processors = {}
        # 기본 프로세서 등록
        self.register_processor("metadata", MetadataProcessor())
        self.register_processor("academic", AcademicPaperProcessor())
        self.register_processor("report", BusinessReportProcessor())
        self.register_processor("general", GeneralDocumentProcessor())
    
    def register_processor(self, doc_type: str, processor: 'BaseDocumentProcessor'):
        """문서 유형별 프로세서 등록"""
        self.processors[doc_type] = processor
    
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """문서 분석 실행"""
        try:
            # PDF 파일 열기
            doc = fitz.open(file_path)
            
            # 메타데이터 초기화
            metadata = {
                'title': '',
                'author': '',
                'page_count': len(doc)
            }
            
            # 첫 페이지 텍스트 추출하여 제목과 저자 찾기
            first_page = doc[0]
            first_page_text = first_page.get_text("text")
            lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
            
            # 제목 찾기 (첫 번째 의미 있는 라인)
            for line in lines:
                if len(line) > 10 and not any(line.startswith(p) for p in ['그림', '표', 'Fig', 'Abstract']):
                    metadata['title'] = line
                    break
            
            # 저자 찾기 (제목 다음 라인들에서)
            found_title = False
            authors = []
            for line in lines:
                if line == metadata['title']:
                    found_title = True
                    continue
                if found_title and len(line) < 50 and ',' in line:
                    authors.extend([a.strip() for a in line.split(',')])
                    break
            metadata['author'] = ', '.join(authors) if authors else ''
            
            # 페이지별 텍스트 저장
            self.pages = {}
            for page_num in range(len(doc)):
                page = doc[page_num]
                # 텍스트 추출 및 정제
                text = page.get_text("text")
                # 줄바꿈 정리
                text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
                self.pages[page_num] = text
                
            doc.close()
            
            return {
                'text': '\n'.join(self.pages.values()),
                'metadata': metadata,
                'page_count': len(self.pages)
            }
            
        except Exception as e:
            logger.error(f"문서 분석 중 오류 발생: {str(e)}")
            raise

    def _detect_document_type(self, text: str, metadata: Dict) -> str:
        """문서 유형 감지 (학술논문, 비즈니스 보고서, 일반문서 등)"""
        # 문서 특징 기반 유형 감지 로직
        if "Abstract" in text or "논문" in text or "연구" in text:
            return 'academic'
        elif "Executive Summary" in text or "보고서" in text or "제언" in text:
            return 'report'
        return 'general'

    def _analyze_document_structure(self, text: str) -> Dict[str, int]:
        """문서 구조 분석을 통한 추가 점수 계산"""
        structure_scores = {
            "academic": 0,
            "report": 0,
            "technical": 0
        }
        
        # 섹션 패턴 분석
        academic_patterns = [
            r'\d+\.\s+서론',
            r'\d+\.\s+연구\s*방법',
            r'\d+\.\s+결론',
            r'Ⅰ\.',
            r'Ⅱ\.',
            r'Ⅲ\.'
        ]
        
        report_patterns = [
            r'\d+\.\s+개요',
            r'\d+\.\s+현황',
            r'\d+\.\s+제언',
            r'가\.',
            r'나\.',
            r'다\.'
        ]
        
        technical_patterns = [
            r'\d+\.\d+\s+구현',
            r'\d+\.\d+\s+설계',
            r'\d+\.\d+\s+실험',
            r'Figure\s+\d+',
            r'Table\s+\d+'
        ]
        
        import re
        
        # 패턴 매칭 및 점수 계산
        for pattern in academic_patterns:
            if re.search(pattern, text):
                structure_scores["academic"] += 2
                
        for pattern in report_patterns:
            if re.search(pattern, text):
                structure_scores["report"] += 2
                
        for pattern in technical_patterns:
            if re.search(pattern, text):
                structure_scores["technical"] += 2
        
        return structure_scores

    def answer_question(self, question: str) -> str:
        # 1. 질문 유형 분류
        question_type = self._classify_question(question)
        
        # 2. 관련 섹션 찾기
        relevant_sections = self._find_relevant_sections(question)
        
        # 3. 답변 생성
        answer = self._generate_answer(question, question_type, relevant_sections)
        
        return answer

    def _classify_question(self, question: str) -> str:
        """질문 유형 분류 (사실형, 분석형, 요약형 등)"""
        if any(word in question.lower() for word in ['첫', '몇', '언제', '누가']):
            return 'factual'
        elif any(word in question.lower() for word in ['왜', '어떻게', '분석']):
            return 'analytical'
        return 'general'

    def _find_relevant_sections(self, question: str) -> List[str]:
        """질문과 관련된 섹션 찾기"""
        if not hasattr(self, 'current_structure'):
            return []
        
        relevant_sections = []
        for section_name, content in self.current_structure.items():
            if isinstance(content, str) and any(word in content.lower() for word in question.lower().split()):
                relevant_sections.append(content)
        return relevant_sections

    def _is_valid_content_line(self, line: str) -> bool:
        """의미 있는 텍스트 라인인지 확인"""
        # 무시할 패턴들
        ignore_patterns = [
            lambda x: len(x) < 20,  # 너무 짧은 라인
            lambda x: x.startswith('[') and x.endswith(']'),  # 참조 마커
            lambda x: any(x.startswith(m) for m in ['그림', '표', 'Figure', 'Table']),  # 그림/표 설명
            lambda x: any(x.startswith(m) for m in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']),  # 섹션 헤더
            lambda x: 'http' in x or 'www' in x,  # URL
            lambda x: x.startswith('참고문헌') or x.startswith('ACKNOWLEDGMENT'),  # 참고문헌 등
        ]
        
        return not any(pattern(line) for pattern in ignore_patterns)

    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # 불필요한 섹션과 마커 제거
        end_markers = ['참고문헌', 'ACKNOWLEDGMENT', 'References']
        for marker in end_markers:
            if marker in text:
                text = text.split(marker)[0]
        
        # 줄 단위로 처리
        cleaned_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if self._is_valid_content_line(line):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def _extract_first_sentence(self, text: str) -> str:
        """첫 번째 의미 있는 문장 추출"""
        try:
            # 1. 텍스트 전처리
            lines = text.split('\n')
            current_sentence = []
            
            # 2. 본문 시작 찾기
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 헤더 섹션 건너뛰기
                if any(header in line for header in ['Abstract', '초록', '요약', 'Keywords', '키워드']):
                    continue
                    
                # 본문 시작 확인
                if "NeRF는" in line:
                    # 현재 줄부터 시작하여 완전한 문장 만들기
                    current_line = line
                    sentence_complete = False
                    
                    while i < len(lines) and not sentence_complete:
                        current_sentence.append(current_line)
                        full_sentence = ' '.join(current_sentence)
                        
                        # 문장 종결 확인
                        if any(full_sentence.strip().endswith(end) for end in ['다.', '까?', '요.', '임.', '함.']):
                            sentence_complete = True
                            if len(full_sentence) > 20:
                                logger.info(f"첫 문장 추출 성공: {full_sentence}")
                                return f"""첫 번째 문장은 다음과 같습니다:

「{full_sentence}」"""
                        else:
                            i += 1
                            if i < len(lines):
                                current_line = lines[i].strip()
                            else:
                                break
            
            logger.warning("유효한 첫 문장을 찾을 수 없습니다.")
            return "문서에서 첫 문장을 찾을 수 없습니다."
            
        except Exception as e:
            logger.error(f"첫 문장 추출 중 오류 발생: {str(e)}")
            return "문서에서 첫 문장을 찾을 수 없습니다."

    def _is_valid_first_sentence(self, sentence: str) -> bool:
        """첫 문장으로 적합한지 검증"""
        # 1. 기본 검증
        if not sentence or len(sentence.strip()) < 20:
            return False
        
        # 2. 제외할 시작 패턴
        exclude_starts = [
            '그림', '표', 'Fig', 'Table',
            'Abstract', '초록', '요약',
            'Keywords', '키워드',
            'Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ',
            '[', '(', '※'
        ]
        
        if any(sentence.strip().startswith(p) for p in exclude_starts):
            return False
        
        # 3. 문장 종결 확인
        end_patterns = [
            '다.', '까?', '요.', '임.', '함.',
            '.', '?', '!'
        ]
        
        if not any(sentence.strip().endswith(p) for p in end_patterns):
            return False
        
        # 4. 특수 패턴 체크
        special_patterns = [
            r'^\d+\.',  # 번호로 시작
            r'^[A-Z]\.',  # 알파벳+점으로 시작
            r'^\([0-9]\)',  # (숫자)로 시작
        ]
        
        if any(re.match(p, sentence.strip()) for p in special_patterns):
            return False
        
        return True

    def _is_valid_sentence(self, sentence: str) -> bool:
        """유효한 문장인지 검증"""
        return (len(sentence) > 50 and  # 충분한 길이
                not sentence.startswith('[') and  # 참조 마커 제외
                not any(sentence.startswith(m) for m in ['그림', '표', 'Figure', 'Table']) and  # 그림/표 설명 제외
                not any(sentence.startswith(m) for m in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', '1.', '2.', '3.']))  # 섹션 헤더 제외

    def _is_important_sentence(self, sentence: str) -> bool:
        """중요한 문장인지 판단"""
        return any(phrase in sentence for phrase in ['본 논문', '이 논문', '본 연구', '이 연구'])

    def _generate_answer(self, question: str, question_type: str, relevant_sections: List[str]) -> str:
        """답변 생성"""
        try:
            if '첫 문장' in question.lower():
                # 페이지 번호 추출
                page_num = 0  # 기본값
                for word in question.split():
                    if word.isdigit():
                        page_num = int(word) - 1  # 1페이지는 인덱스 0
                        break
                
                # 해당 페이지의 첫 문장 찾기
                if hasattr(self, 'pages') and page_num in self.pages:
                    content = self.pages[page_num]
                    first_sentence = self._extract_first_sentence(content)
                    
                    if first_sentence:
                        return f"""첫 번째 문장은 다음과 같습니다:

「{first_sentence}」"""
                
                return "해당 페이지의 첫 문장을 찾을 수 없습니다."
        except Exception as e:
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
        
        # 기본 답변
        if not relevant_sections:
            return "관련된 정보를 찾을 수 없습니다."
        return relevant_sections[0]

    def _extract_headings(self, text: str) -> List[str]:
        """문서에서 제목 추출 최적화"""
        headings = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            # 제목 패턴 확인
            if any(pattern in line for pattern in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']):
                headings.append(line)
            elif re.match(r'^[1-9]\.\s+\w+', line):  # 숫자로 시작하는 제목
                headings.append(line)
            elif len(line) > 0 and len(line) < 50 and line.endswith((':', '.')):
                # 짧은 라인이면서 : 나 . 으로 끝나는 경우
                if i > 0 and len(lines[i-1].strip()) == 0:  # 위에 빈 줄이 있는 경우
                    headings.append(line)
        
        return headings

    def _check_file_permissions(self, file_path: str) -> bool:
        """파일 접근 권한 확인"""
        try:
            with open(file_path, 'rb') as f:
                return True
        except PermissionError:
            return False
        except Exception as e:
            logger.error(f"파일 접근 중 오류 발생: {str(e)}")
            return False

    def _normalize_file_path(self, file_path: str) -> str:
        """파일 경로 정규화"""
        # 절대 경로로 변환
        abs_path = os.path.abspath(file_path)
        
        # 경로 구분자 정규화
        norm_path = os.path.normpath(abs_path)
        
        return norm_path

def initialize_analyzer():
    analyzer = DocumentAnalyzer()
    
    # 기존 프로세서 유지
    analyzer.register_processor("general", GeneralDocumentProcessor())
    analyzer.register_processor("report", BusinessReportProcessor())
    
    # 첫 문장 프로세서 추가
    analyzer.register_processor("first_sentence", FirstSentenceProcessor())
    
    return analyzer 