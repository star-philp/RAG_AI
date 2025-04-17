from abc import ABC, abstractmethod
import fitz
from typing import Dict, Any

class BaseDocumentProcessor(ABC):
    @abstractmethod
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        pass

class GeneralDocumentProcessor(BaseDocumentProcessor):
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        """일반 문서 처리"""
        result = {
            "text_content": [],
            "structure": {"headings": [], "paragraphs": []}
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            result["text_content"].append(text)
            
            # 기본적인 구조 분석
            blocks = page.get_text("blocks")
            for block in blocks:
                if block[4].strip().endswith(":"):  # 제목으로 추정
                    result["structure"]["headings"].append(block[4])
                else:
                    result["structure"]["paragraphs"].append(block[4])
                    
        return result

class BusinessReportProcessor(BaseDocumentProcessor):
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        """보고서 형식 문서 처리"""
        result = {
            "summary": "",
            "key_points": [],
            "sections": []
        }
        
        # 보고서 특화 처리 로직
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # 요약 섹션 찾기
            if "요약" in text or "Summary" in text:
                result["summary"] = text.split("요약", 1)[1].split("\n\n")[0]
                
            # 주요 포인트 추출
            if "주요" in text or "Key Points" in text:
                points = text.split("•")[1:]
                result["key_points"].extend([p.strip() for p in points])
                
        return result 

class FirstSentenceProcessor(BaseDocumentProcessor):
    """첫 문장 추출을 위한 전문 프로세서"""
    
    def process(self, doc: fitz.Document) -> Dict[str, Any]:
        """첫 페이지의 첫 문장 추출"""
        result = {
            "first_sentence": "",
            "page_number": 1,
            "metadata": {}
        }
        
        try:
            # 첫 페이지 가져오기
            first_page = doc[0]
            text = first_page.get_text()
            
            # 텍스트 전처리
            text = text.replace('\n', ' ').strip()
            
            # 문장 구분자 정의
            sentence_endings = ['. ', '? ', '! ', '. \n', '? \n', '! \n']
            
            # 첫 문장 찾기
            first_sentence = text
            for ending in sentence_endings:
                pos = text.find(ending)
                if pos != -1:
                    first_sentence = text[:pos + 1].strip()
                    break
            
            result["first_sentence"] = first_sentence
            result["metadata"]["text_length"] = len(first_sentence)
            result["metadata"]["has_special_chars"] = any(char in first_sentence for char in ['[', ']', '(', ')'])
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            return result 