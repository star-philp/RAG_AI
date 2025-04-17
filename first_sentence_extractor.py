import fitz
import re
import streamlit as st
from typing import Dict, Any, List, Optional

class PDFDiagnostics:
    """PDF 문서 진단 클래스"""
    
    def __init__(self):
        self.diagnostics = {
            "문서_구조": None,
            "텍스트_추출": None,
            "첫문장_후보": [],
            "오류_로그": []
        }
    
    def diagnose_document(self, pdf_path: str) -> dict:
        """PDF 문서 진단 실행"""
        try:
            with fitz.open(pdf_path) as doc:
                # 1. 문서 구조 확인
                self._check_document_structure(doc)
                
                # 2. 첫 페이지 텍스트 추출 시도
                self._extract_first_page_text(doc)
                
                # 3. 첫 문장 후보 식별
                self._identify_sentence_candidates(doc)
                
                return self.get_diagnostic_report()
                
        except Exception as e:
            self.diagnostics["오류_로그"].append(f"진단 중 오류 발생: {str(e)}")
            return self.get_diagnostic_report()
    
    def _check_document_structure(self, doc):
        """문서 구조 확인"""
        try:
            first_page = doc[0]
            blocks = first_page.get_text("dict")["blocks"]
            
            self.diagnostics["문서_구조"] = {
                "총_블록_수": len(blocks),
                "텍스트_블록": sum(1 for b in blocks if "lines" in b),
                "이미지_블록": sum(1 for b in blocks if "image" in b),
                "블록_좌표": [(b["bbox"], len(b.get("lines", []))) for b in blocks[:3]]
            }
        except Exception as e:
            self.diagnostics["오류_로그"].append(f"문서 구조 확인 실패: {str(e)}")
    
    def _extract_first_page_text(self, doc):
        """첫 페이지 텍스트 추출 시도"""
        try:
            first_page = doc[0]
            text_dict = first_page.get_text("dict")
            
            self.diagnostics["텍스트_추출"] = {
                "추출_방식": ["dict", "blocks", "text"],
                "추출_결과": {
                    "dict": bool(text_dict),
                    "blocks": bool(first_page.get_text("blocks")),
                    "text": bool(first_page.get_text("text"))
                }
            }
        except Exception as e:
            self.diagnostics["오류_로그"].append(f"텍스트 추출 실패: {str(e)}")
    
    def _identify_sentence_candidates(self, doc):
        """첫 문장 후보 식별"""
        try:
            first_page = doc[0]
            blocks = first_page.get_text("blocks")
            
            for block in blocks[:5]:  # 처음 5개 블록만 확인
                text = block[4] if isinstance(block, tuple) else block["text"]
                text = text.strip()
                
                if len(text) >= 30:  # 의미있는 길이의 텍스트만 후보로 선정
                    self.diagnostics["첫문장_후보"].append({
                        "텍스트": text[:100] + "..." if len(text) > 100 else text,
                        "길이": len(text),
                        "위치": block[:4] if isinstance(block, tuple) else block["bbox"]
                    })
        except Exception as e:
            self.diagnostics["오류_로그"].append(f"문장 후보 식별 실패: {str(e)}")
    
    def get_diagnostic_report(self) -> dict:
        """진단 보고서 생성"""
        return {
            "진단_결과": {
                "문서_상태": "정상" if not self.diagnostics["오류_로그"] else "오류",
                "텍스트_추출_가능": bool(self.diagnostics["텍스트_추출"]),
                "첫문장_후보_수": len(self.diagnostics["첫문장_후보"])
            },
            "상세_정보": self.diagnostics,
            "권장_조치": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> list:
        """문제 해결을 위한 권장 조치 생성"""
        recommendations = []
        
        if not self.diagnostics["문서_구조"]:
            recommendations.append("문서 구조 분석 실패 - PDF 파일 형식 확인 필요")
        
        if not self.diagnostics["텍스트_추출"]:
            recommendations.append("텍스트 추출 실패 - 다른 추출 방식 시도 필요")
        
        if not self.diagnostics["첫문장_후보"]:
            recommendations.append("첫 문장 후보 없음 - 텍스트 블록 필터링 기준 조정 필요")
        
        return recommendations

class FirstSentenceExtractor:
    def __init__(self):
        # 메타데이터 패턴 정의
        self.metadata_patterns = [
            r'Abstract', r'초록', r'요약',
            r'Keywords?', r'키워드',
            r'.*@.*',  # 이메일
            r'.*University.*', r'.*대학.*', r'.*연구소.*',
            r'.*Institute.*', r'.*Center.*',
            r'.*[A-Z]+\s*[A-Z]+.*',  # 영문 약자
            r'.*\d{4}.*',  # 연도
            r'.*et\s+al.*',  # 저자 인용
            r'^\s*[A-Z][a-z]+\s+[A-Z][a-z]+',  # 영문 이름
            r'^\s*[가-힣]{2,4}\s*[,\s]',  # 한글 이름
            r'https?://\S+',  # URL
            r'.*Fellowship.*',  # 펠로우십 관련
            r'.*연구결과.*',  # 연구 결과 관련
            r'.*과제번호.*',  # 과제 번호
            r'.*지원.*',  # 지원 관련
            r'.*funded by.*'  # 펀딩 정보
        ]
        
        # 섹션 헤더 패턴
        self.section_patterns = [
            r'^Ⅰ\.', r'^Ⅱ\.', r'^Ⅲ\.', r'^Ⅳ\.', r'^Ⅴ\.',
            r'^\d+\.\s*\w+',
            r'^\d+\-\d+\.',
            r'^[A-Z]\.\s*\w+',
            r'^서론', r'^본론', r'^결론',
            r'^Introduction', r'^Conclusion',
            r'^ACKNOWLEDGMENT',
            r'^참고문헌', r'^References',
            r'^\[그림\s*\d+\]',
            r'^\[표\s*\d+\]'
        ]
        
        # 문장 종결 패턴 (공백 없는 버전 추가)
        self.end_patterns = [
            '다.', '까?', '까!', '다!', '다?', 
            '요.', '요?', '니다.', '습니다.',
            '이다.', '한다.', '였다.', '있다.',
            '된다.', '왔다.', '간다.', '온다.',
            '했다.', '였다.', '입니다.',
            '인다.', '운다.', '였다.',
            '이다', '한다', '있다', '된다',
            '왔다', '간다', '온다', '했다'
        ]
    
    def extract_first_sentence(self, pdf_path: str) -> str:
        """개선된 첫 문장 추출 함수"""
        try:
            with fitz.open(pdf_path) as doc:
                first_page = doc[0]
                blocks = first_page.get_text("blocks")
                
                # y좌표로 정렬
                blocks.sort(key=lambda b: (b[1], b[0]))
                
                # 디버그 정보
                if st.session_state.get('debug_mode', False):
                    st.info("블록 분석 시작...")
                
                # 메타데이터 영역 식별
                metadata_end_y = 0
                abstract_start_y = float('inf')
                
                # 첫 번째 패스: 메타데이터 영역 식별
                for block in blocks:
                    text = block[4].strip()
                    y_coord = block[1]
                    
                    # 메타데이터 확인
                    if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.metadata_patterns):
                        metadata_end_y = max(metadata_end_y, block[3])
                        if st.session_state.get('debug_mode', False):
                            st.text(f"메타데이터 발견 (y: {y_coord:.1f}):\n{text[:100]}")
                    
                    # 초록 시작 위치 확인
                    if any(text.startswith(marker) for marker in ['Abstract', '초록', '요약']):
                        abstract_start_y = min(abstract_start_y, y_coord)
                        if st.session_state.get('debug_mode', False):
                            st.text(f"초록 발견 (y: {y_coord:.1f})")
                
                # 본문 시작 위치 결정
                content_start_y = max(metadata_end_y, abstract_start_y)
                
                # 두 번째 패스: 본문 블록 처리
                for block in blocks:
                    # 메타데이터와 초록 영역 건너뛰기
                    if block[1] <= content_start_y:
                        continue
                    
                    text = block[4].strip()
                    
                    # 디버그 정보
                    if st.session_state.get('debug_mode', False):
                        st.text(f"본문 블록 분석 중 (y: {block[1]:.1f}):\n{text[:100]}")
                    
                    # 섹션 헤더 건너뛰기
                    if any(re.match(pattern, text) for pattern in self.section_patterns):
                        continue
                    
                    # 문장 분리 및 검증
                    sentences = self._split_into_sentences(text)
                    for sentence in sentences:
                        if self._is_valid_sentence(sentence):
                            if st.session_state.get('debug_mode', False):
                                st.success(f"유효한 첫 문장 발견:\n{sentence}")
                            return f"첫 번째 문장은 다음과 같습니다:\n\n「{sentence}」"
                
                return "문서에서 첫 문장을 찾을 수 없습니다."
                
        except Exception as e:
            if st.session_state.get('debug_mode', False):
                st.error(f"문장 추출 중 오류: {str(e)}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
            return "문장 추출 중 오류가 발생했습니다."
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장으로 분리"""
        sentences = []
        current_sentence = ""
        
        # 줄바꿈을 공백으로 변경
        text = text.replace('\n', ' ')
        text = ' '.join(text.split())
        
        # 문자 단위로 처리
        i = 0
        while i < len(text):
            current_sentence += text[i]
            
            # 현재 위치에서 모든 종결 패턴 확인
            found_end = False
            for end in self.end_patterns:
                if text[i-len(end)+1:i+1] == end:
                    # 다음 문자가 있고 공백이 아닌 경우는 건너뛰기
                    if i + 1 < len(text) and text[i+1] not in [' ', '\n']:
                        continue
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
                    found_end = True
                    break
            
            i += 1
        
        # 마지막 문장 처리
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _is_valid_sentence(self, sentence: str) -> bool:
        """문장 유효성 검증"""
        sentence = sentence.strip()
        
        # 기본 길이 검사
        if len(sentence) < 30:
            return False
        
        # 메타데이터 패턴 검사
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in self.metadata_patterns):
            return False
        
        # 섹션 헤더 검사
        if any(re.match(pattern, sentence) for pattern in self.section_patterns):
            return False
        
        # 특수 시작 패턴 검사
        invalid_starts = [
            '그림', '표', 'Fig', 'Table', 'Figure',
            'Abstract', '초록', '요약',
            'Keywords', '키워드',
            '참고문헌', 'References',
            '본 논문', '본 연구', '본고',
            '저자', '연구자',
            '[', '(', '※', '※※',
            '주)', '각주)', '참고)',
            '비고', '참조'
        ]
        if any(sentence.startswith(start) for start in invalid_starts):
            return False
        
        # 문장 종결 확인
        if not any(sentence.endswith(end) for end in self.end_patterns):
            return False
        
        return True 