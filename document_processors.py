from abc import ABC, abstractmethod
import fitz
from typing import Dict, Any, List, Optional
import re
import streamlit as st

class BaseDocumentProcessor(ABC):
    """문서 처리를 위한 기본 추상 클래스"""
    @abstractmethod
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        pass

class GeneralDocumentProcessor(BaseDocumentProcessor):
    """일반 문서 처리 클래스"""
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        result = {
            "text_content": [],
            "structure": {"headings": [], "paragraphs": []}
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            result["text_content"].append(text)
            
            blocks = page.get_text("blocks")
            for block in blocks:
                if block[4].strip().endswith(":"):  # 제목으로 추정
                    result["structure"]["headings"].append(block[4])
                else:
                    result["structure"]["paragraphs"].append(block[4])
                    
        return result

class BusinessReportProcessor(BaseDocumentProcessor):
    """비즈니스 보고서 처리 클래스"""
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        result = {
            "summary": "",
            "key_points": [],
            "sections": []
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if "요약" in text or "Summary" in text:
                result["summary"] = text.split("요약", 1)[1].split("\n\n")[0]
                
            if "주요" in text or "Key Points" in text:
                points = text.split("•")[1:]
                result["key_points"].extend([p.strip() for p in points])
                
        return result

class AcademicPaperProcessor(BaseDocumentProcessor):
    """학술 논문 처리 클래스"""
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        result = {
            "abstract": "",
            "keywords": [],
            "references": []
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if "Abstract" in text or "초록" in text:
                result["abstract"] = self._extract_section(text, ["Abstract", "초록"])
                
            if "Keywords" in text or "키워드" in text:
                result["keywords"] = self._extract_keywords(text)
                
        return result
    
    def _extract_section(self, text: str, markers: List[str]) -> str:
        for marker in markers:
            if marker in text:
                section = text.split(marker, 1)[1].split("\n\n")[0]
                return section.strip()
        return ""
    
    def _extract_keywords(self, text: str) -> List[str]:
        keywords = []
        for marker in ["Keywords:", "키워드:"]:
            if marker in text:
                keyword_section = text.split(marker, 1)[1].split("\n")[0]
                keywords = [k.strip() for k in keyword_section.split(",")]
                break
        return keywords

class FirstSentenceProcessor:
    """첫 문장 추출을 위한 전용 프로세서"""
    
    def __init__(self):
        self.section_headers = [
            'Abstract', '초록', '요약', 
            'Keywords', '키워드',
            'Introduction', '서론',
            '1.', 'Ⅰ.', 'I.'
        ]
        
        self.sentence_endings = [
            '다.', '까?', '요.', '임.', '함.',
            '됨.', '짐.', '움.', '늠.', '봄.',
            '다!', '죠.', '죠?', '네.', '네?',
            '니다.', '세요.', '어요.'
        ]
    
    def process(self, text: str) -> str:
        """첫 번째 의미 있는 문장 추출"""
        try:
            # 1. 텍스트 전처리
            lines = text.split('\n')
            content_started = False
            current_sentence = []
            
            # 2. 본문 시작 찾기 - "NeRF" 키워드 우선 검색
            for i, line in enumerate(lines):
                line = line.strip()
                
                # "NeRF" 키워드가 있는 라인 찾기
                if "NeRF" in line and not any(header in line for header in self.section_headers):
                    current_line = line
                    sentence_complete = False
                    
                    # 완전한 문장 구성
                    while i < len(lines) and not sentence_complete:
                        if current_line:
                            current_sentence.append(current_line)
                        full_sentence = ' '.join(current_sentence)
                        
                        # 문장 종결 확인
                        if self._is_complete_sentence(full_sentence):
                            if len(full_sentence) > 20:  # 최소 길이 검증
                                logger.info(f"첫 문장 추출 성공: {full_sentence}")
                                return f"""첫 번째 문장은 다음과 같습니다:

「{full_sentence}」"""
                            break
                        
                        i += 1
                        if i < len(lines):
                            current_line = lines[i].strip()
                            if any(header in current_line for header in self.section_headers):
                                break
                        else:
                            break
            
            # 3. "NeRF" 키워드를 찾지 못한 경우 일반적인 첫 문장 찾기
            current_sentence = []
            for i, line in enumerate(lines):
                line = line.strip()
                
                if not line or any(header in line for header in self.section_headers):
                    continue
                
                if self._is_valid_content_line(line):
                    current_line = line
                    sentence_complete = False
                    
                    while i < len(lines) and not sentence_complete:
                        if current_line:
                            current_sentence.append(current_line)
                        full_sentence = ' '.join(current_sentence)
                        
                        if self._is_complete_sentence(full_sentence):
                            if len(full_sentence) > 20:
                                return f"""첫 번째 문장은 다음과 같습니다:

「{full_sentence}」"""
                            break
                        
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
    
    def _is_valid_content_line(self, line: str) -> bool:
        """의미 있는 텍스트 라인인지 검증"""
        if not line or len(line) < 10:
            return False
            
        # 제외할 패턴
        exclude_patterns = [
            r'^\d+$',  # 페이지 번호
            r'^그림\s+\d+',  # 그림 캡션
            r'^표\s+\d+',  # 표 캡션
            r'^Fig\.',  # 영문 그림 캡션
            r'^Table\s+\d+',  # 영문 표 캡션
            r'^\[[\d,\s]+\]$',  # 참조 번호
            r'^[A-Z\s]+:',  # 영문 섹션 헤더
            r'^[가-힣\s]+:',  # 한글 섹션 헤더
            r'.*@.*',  # 이메일 주소
            r'.*대학교.*',  # 소속기관
            r'.*University.*',  # 영문 소속기관
            r'^\d+\.',  # 번호로 시작
            r'^[A-Z]\.',  # 알파벳+점으로 시작
        ]
        
        return not any(re.match(pattern, line) for pattern in exclude_patterns)
    
    def _is_complete_sentence(self, text: str) -> bool:
        """완전한 문장인지 확인"""
        text = text.strip()
        return any(text.endswith(end) for end in self.sentence_endings)

class MetadataProcessor(BaseDocumentProcessor):
    """PDF 문서의 메타데이터와 구조를 추출하는 프로세서"""
    
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        result = {
            "metadata": {
                "title": "",
                "author": "",
                "page_count": len(doc)
            },
            "structure": {
                "title": "",
                "sections": []
            }
        }
        
        try:
            first_page = doc[0]
            text = first_page.get_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # 제목 추출
            title_found = False
            for i, line in enumerate(lines):
                # 영문/한글 제목 패턴
                if (len(line) > 10 and 
                    not self._is_affiliation_line(line) and 
                    not self._is_author_line(line) and
                    not self._is_email_line(line) and
                    not self._is_special_line(line)):
                    
                    # 다음 줄이 저자나 소속 정보인 경우에만 제목으로 인정
                    if i + 1 < len(lines) and (
                        self._is_author_line(lines[i+1]) or 
                        self._is_affiliation_line(lines[i+1])):
                        result["metadata"]["title"] = line
                        result["structure"]["title"] = line
                        title_found = True
                        break
            
            # 제목을 찾지 못한 경우, 파일명에서 추출
            if not title_found and hasattr(doc, 'name'):
                filename = doc.name.split('/')[-1]
                if filename.endswith('.pdf'):
                    filename = filename[:-4]
                result["metadata"]["title"] = filename
                result["structure"]["title"] = filename
            
            # 저자 추출
            authors = []
            author_section_started = False
            
            for line in lines[1:6]:  # 제목 다음부터 최대 5줄까지 검사
                # 저자 섹션 시작 확인
                if not author_section_started and self._is_author_line(line):
                    author_section_started = True
                
                if author_section_started and not self._is_special_line(line):
                    names = self._extract_author_names(line)
                    if names:
                        authors.extend(names)
                    
                    # 소속이나 이메일이 나오면 저자 섹션 종료
                    if self._is_affiliation_line(line) or self._is_email_line(line):
                        break
            
            # 중복 제거 및 정렬
            authors = sorted(set(authors))
            result["metadata"]["author"] = ", ".join(authors) if authors else ""
            
            return result
            
        except Exception as e:
            print(f"메타데이터 처리 중 오류 발생: {str(e)}")
            return result
    
    def _is_affiliation_line(self, line: str) -> bool:
        """소속 정보를 포함하는 줄인지 확인"""
        patterns = [
            r'대학교\d*[,.]?[*†‡§]?',
            r'[A-Za-z\s]+Univ[.,]',
            r'[A-Za-z\s]+University',
            r'연구소\d*[,.]?',
            r'기업\d*[,.]?',
            r'회사\d*[,.]?',
            r'[A-Za-z\s]+Corporation',
            r'[A-Za-z\s]+Inc[.,]',
            r'[A-Za-z\s]+Lab[s.,]',
            r'SK\s+[A-Za-z]+',  # SK 관련 회사
            r'[A-Za-z]+\d+[,.*]'  # 소속 번호 표시
        ]
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
    
    def _is_author_line(self, line: str) -> bool:
        """저자 정보를 포함하는 줄인지 확인"""
        # 저자 패턴: 2-4자의 한글 이름
        author_pattern = r'[가-힣]{2,4}(?:[\s,]+[가-힣]{2,4})*'
        return (re.search(author_pattern, line) and 
                not self._is_affiliation_line(line) and
                not self._is_email_line(line) and
                not self._is_special_line(line))
    
    def _is_email_line(self, line: str) -> bool:
        """이메일 주소를 포함하는 줄인지 확인"""
        return '@' in line
    
    def _is_special_line(self, line: str) -> bool:
        """특수한 줄인지 확인 (초록, 키워드 등)"""
        patterns = [
            r'^Abstract',
            r'^요약',
            r'^Keywords?:?',
            r'^키워드:?',
            r'^목차',
            r'^Contents?',
            r'^Copyright',
            r'^\d+\.',
            r'^[A-Z]\.',
            r'^Fig\.',
            r'^Table'
        ]
        return any(re.match(pattern, line) for pattern in patterns)
    
    def _extract_author_names(self, line: str) -> List[str]:
        """줄에서 저자 이름만 추출"""
        names = []
        # 이름 추출 (2-4자의 한글)
        matches = re.finditer(r'[가-힣]{2,4}', line)
        for match in matches:
            name = match.group()
            if len(name) >= 2 and not self._is_affiliation_line(name):
                names.append(name)
        return names