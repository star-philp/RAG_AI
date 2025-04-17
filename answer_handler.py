from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

class AnswerFormatter(ABC):
    """답변 형식을 정의하는 추상 클래스"""
    @abstractmethod
    def format_answer(self, answer: str, sources: List[dict]) -> str:
        pass

class SimpleQuestionFormatter(AnswerFormatter):
    """단순 질문(예: 첫 문장, 저자 등)에 대한 포맷터"""
    def format_answer(self, answer: str, sources: List[dict]) -> str:
        try:
            # 페이지 내용 정리
            page_contents = {}
            for source in sources:
                page_num = source.metadata.get('page', -1)
                if page_num not in page_contents:
                    page_contents[page_num] = source.page_content

            # 첫 문장 관련 질문 처리
            if '첫문장' in answer.lower() or '첫 문장' in answer:
                first_sentence = self._find_first_sentence(page_contents)
                return f"""
### 답변
{first_sentence}

### 출처
페이지 0의 첫 부분입니다.
"""
            return f"""
### 답변
{answer}

### 출처
{self._format_source(page_contents)}
"""
        except Exception as e:
            return f"""
### 답변
처리 중 오류가 발생했습니다: {str(e)}

### 출처
출처 정보를 가져올 수 없습니다.
"""

    def _find_first_sentence(self, page_contents: Dict[int, str]) -> str:
        """첫 페이지의 첫 문장 찾기"""
        if 0 not in page_contents:
            return "첫 페이지를 찾을 수 없습니다."
        
        text = page_contents[0]
        # 제목과 저자 정보 건너뛰기
        text_lines = text.split('\n')
        main_text = ''
        for line in text_lines:
            if len(line) > 50:  # 본문으로 추정되는 긴 텍스트
                main_text = line
                break
        
        if not main_text:
            return "본문을 찾을 수 없습니다."
        
        # 첫 문장 추출
        sentences = main_text.split('.')
        first_sentence = sentences[0].strip()
        
        return f"""첫 번째 문장은 다음과 같습니다:

「{first_sentence}」"""

    def _format_source(self, page_contents: Dict[int, str]) -> str:
        """출처 정보 형식화"""
        if 0 in page_contents:
            return f"페이지 0: {page_contents[0][:200]}..."
        return "관련 페이지를 찾을 수 없습니다."

class AnalysisQuestionFormatter(AnswerFormatter):
    """분석이 필요한 질문에 대한 포맷터"""
    def format_answer(self, answer: str, sources: List[dict]) -> str:
        try:
            return f"""
### 분석 결과
{answer}

### 주요 근거
{self._format_sources(sources)}

### 참고 자료
{self._format_references(sources)}
"""
        except Exception as e:
            return f"""
### 분석 결과
{answer}

### 참고
소스 정보를 처리하는 중 오류가 발생했습니다.
"""

    def _format_sources(self, sources: List[dict]) -> str:
        try:
            return "\n".join([f"- {source.page_content[:100]}..." for source in sources[:2]])
        except Exception as e:
            return "소스 정보를 가져올 수 없습니다."

    def _format_references(self, sources: List[dict]) -> str:
        try:
            return "\n".join([f"페이지 {source.metadata['page']}" for source in sources])
        except Exception as e:
            return "페이지 정보를 가져올 수 없습니다."

class QuestionClassifier:
    """질문 유형을 분류하는 클래스"""
    def __init__(self):
        self.simple_patterns = [
            "첫 번째", "첫문장", "저자", "제목",
            "페이지", "쪽", "그림", "표",
            "언제", "어디서", "누가"
        ]
    
    def classify_question(self, question: str) -> str:
        return "simple" if any(pattern in question for pattern in self.simple_patterns) else "analysis"

class AnswerHandler:
    """답변 처리를 관리하는 클래스"""
    def __init__(self):
        self.classifier = QuestionClassifier()
        self.formatters = {
            "simple": SimpleQuestionFormatter(),
            "analysis": AnalysisQuestionFormatter()
        }

    def process_answer(self, question: str, answer: str, sources: List[dict]) -> str:
        # 질문 유형 분류
        question_type = self.classifier.classify_question(question)
        
        # 적절한 포맷터 선택
        formatter = self.formatters.get(question_type)
        
        # 답변 형식화
        formatted_answer = formatter.format_answer(answer, sources)
        
        return formatted_answer

    def enhance_answer(self, answer: str) -> str:
        """답변 품질 향상을 위한 후처리"""
        # 중복 제거
        lines = list(dict.fromkeys(answer.split('\n')))
        
        # 빈 줄 정리
        lines = [line for line in lines if line.strip()]
        
        # 불필요한 참조 제거
        lines = [line for line in lines if not line.startswith("참고 출처:")]
        
        return "\n".join(lines) 