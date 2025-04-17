import re
import logging
from typing import List, Pattern, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class PageProcessor:
    """페이지별 텍스트 처리를 담당하는 클래스"""
    
    def __init__(self):
        # 메타데이터 패턴 강화
        self.metadata_patterns = {
            'email': r'[\w\.-]+@[\w\.-]+\.\w{2,}',
            'affiliation': r'(?:Univ(?:ersity)?|SK\s*Telecom|대학교?)',
            'author': r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\d*|[가-힣]{2,4}(?:[0-9*†]|\s*,\s*[가-힣]{2,4})*',
            'special_chars': r'[\x00-\x1F\x7F-\x9F]'  # 백슬래시 별도 처리
        }
        
        # 논문 구조 관련 패턴
        self.paper_sections = {
            'title': r'^[가-힣\s]+[A-Za-z\s]*[가-힣\s]+$',
            'authors': r'^[가-힣]{2,4}(?:[0-9*†]|\s*,\s*[가-힣]{2,4})*$',
            'abstract': r'^(?:ABSTRACT|초록|요약)$',
            'keywords': r'^(?:Keywords|중심어|주제어):'
        }
        
        # 섹션 식별을 위한 패턴
        self.section_patterns = {
            'section_number': r'^\d+\.',
            'section_title': r'^[1-9]\.\s*[가-힣\s]+',
            'subsection': r'^\d+\.\d+\.'
        }
        
        # 스킵할 패턴 정의
        self.skip_patterns = [
            r'^\s*$',
            r'[\w\.-]+@[\w\.-]+\.\w{2,}',
            r'.*(?:Univ(?:ersity)?|대학교?).*',
            r'^\[?(?:표|그림|Fig\.|Table)\s*\d+\]?',
            r'^\d+\s*fps',
            r'^(?:PSNR|SSIM|LPIPS|BRISQUE|R/E)'
        ]
        
        # 한글 문장 패턴 (개선)
        self.sentence_pattern = re.compile(
            r'[가-힣A-Za-z()\s]+(?:다|까|요|죠|니다|음|임)[.!?]'
        )
        
        # 한글 단어 패턴
        self.word_pattern = re.compile(r'[가-힣]+')
        
        # 특수 용어
        self.special_terms = {
            'NeRF': 'NeRF',
            'Neural Radiance Fields': 'Neural Radiance Fields',
            '3D': '3D'
        }
        
        # 조사 목록
        self.particles = [
            '은', '는', '이', '가', '을', '를', '의', '에', '에서', 
            '로', '으로', '과', '와', '이나', '나', '에게', '께', '도'
        ]
        
        # 접속 조사
        self.conjunctions = [
            '하고', '이고', '며', '거나', '든지'
        ]
    
    def clean_text(self, text: str) -> str:
        """특수 문자 및 메타데이터 제거"""
        if not isinstance(text, str):
            return ""
            
        # 백슬래시 패턴 먼저 제거    
        text = re.sub(r'\\[0-9]', '', text)
        text = re.sub(r'\\', '', text)  # 남은 백슬래시 제거
        
        # 특수 문자 제거
        text = re.sub(self.metadata_patterns['special_chars'], '', text)
        
        # 이메일 주소 제거
        text = re.sub(self.metadata_patterns['email'], '', text)
        
        # 소속기관 정보 제거
        text = re.sub(self.metadata_patterns['affiliation'], '', text)
        
        # 저자 이름 패턴 제거
        text = re.sub(self.metadata_patterns['author'], '', text)
        
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def normalize_text(self, text: str) -> str:
        """텍스트 정규화 처리"""
        if not isinstance(text, str):
            logger.warning(f"입력 텍스트가 올바르지 않습니다: {type(text)}")
            return ""
            
        # 기본 클리닝
        text = self.clean_text(text)
        
        # 메타데이터 패턴 제거 강화
        metadata_patterns = [
            r'[\w\.-]+@[\w\.-]+\.\w{2,}',  # 이메일
            r'(?:Univ(?:ersity)?|SK\s*Telecom|대학교?)\d*,?[*]?',  # 소속기관
            r'[A-Za-z]+\d+,\s*[A-Za-z]+\d+',  # 저자 ID
            r'\{[\w\.-]+\}',  # 중괄호로 묶인 정보
            r'[A-Z][a-z]+\s+[A-Z][a-z]+\d*'  # 영문 이름
        ]
        
        for pattern in metadata_patterns:
            text = re.sub(pattern, '', text)
        
        # 한글 조사 처리 개선
        for particle in self.particles:
            text = re.sub(f'([가-힣]){particle}(?=[^가-힣]|$)', r'\1 {particle}', text)
        
        # 한글 단어 사이 띄어쓰기 개선
        text = re.sub(r'([가-힣])([가-힣])', r'\1 \2', text)
        text = re.sub(r'\s+', ' ', text)  # 중복 공백 제거
        
        # 한글과 영문/숫자 사이 띄어쓰기
        text = re.sub(r'([가-힣])([A-Za-z0-9])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z0-9])([가-힣])', r'\1 \2', text)
        
        # 특수 용어 보존
        for term, replacement in self.special_terms.items():
            text = re.sub(rf'\b{re.escape(term)}\b', replacement, text, flags=re.IGNORECASE)
        
        # 최종 정리
        text = re.sub(r'\s+', ' ', text)  # 중복 공백 제거
        text = text.strip()
        
        return text

    def identify_paper_structure(self, page: Any) -> Dict[str, str]:
        """논문의 구조적 요소 식별"""
        structure = {
            'title': '',
            'authors': '',
            'abstract': '',
            'main_content': '',
            'sections': []
        }
        
        try:
            # 텍스트 블록 가져오기
            blocks = page.get_text("blocks")
            if not blocks:
                logger.warning("텍스트 블록을 찾을 수 없습니다.")
                return structure
                
            # 전체 페이지 텍스트 추출 (백업용)
            full_page_text = page.get_text()
            if full_page_text and len(full_page_text) > 100:
                structure['full_text'] = full_page_text
                
            # y좌표 기준 정렬 (위에서 아래로)
            sorted_blocks = []
            
            # 블록 처리 로직 개선
            for block in blocks:
                try:
                    # 블록이 튜플이나 리스트이고 최소 5개 요소가 있는지 확인
                    if isinstance(block, (tuple, list)) and len(block) >= 5:
                        x0, y0 = block[0], block[1]
                        # 텍스트 추출 및 공백 제거
                        text = str(block[4]).strip()
                        if text and len(text) >= 10:  # 최소 길이 제한 강화
                            # 표나 그림 설명 필터링 강화
                            if not any(re.match(pattern, text) for pattern in [
                                r'^\s*(?:표|그림|Fig\.|Table|Figure)\s*\d+', 
                                r'^\s*\d+\s*fps', 
                                r'^\s*(?:\.|,|;)', 
                                r'^\s*\[',
                                r'^\s*\d+\.\d+',
                                r'^\s*References',
                                r'^\s*참고문헌'
                            ]):
                                sorted_blocks.append((x0, y0, text))
                except Exception as e:
                    logger.error(f"블록 파싱 중 오류: {str(e)}")
                    continue
            
            # 블록이 없으면 빈 구조 반환
            if not sorted_blocks:
                logger.warning("유효한 텍스트 블록이 없습니다.")
                if 'full_text' in structure:
                    # 전체 텍스트에서 의미 있는 문장 추출 시도
                    sentences = re.split(r'(?<=[.!?])\s+', structure['full_text'])
                    for sentence in sentences:
                        if len(sentence) >= 30 and len(re.findall(r'[가-힣]+', sentence)) >= 3:
                            structure['main_content'] = sentence
                            break
                return structure
                
            # y좌표 기준으로 정렬 (위에서 아래로)
            sorted_blocks.sort(key=lambda block: (block[1], block[0]))
            
            # 제목 및 저자 추출 시도
            if len(sorted_blocks) >= 2:
                structure['title'] = sorted_blocks[0][2]
                structure['authors'] = sorted_blocks[1][2]
            
            current_section = None
            abstract_found = False
            
            for block_data in sorted_blocks:
                try:
                    # 블록 데이터 언패킹 (x, y, text)
                    _, _, text = block_data
                    
                    if not text:
                        continue
                    
                    # 메타데이터 건너뛰기 (스킵 패턴 체크 - 더 엄격하게)
                    if any(re.search(pattern, text) for pattern in self.skip_patterns):
                        continue
                    
                    # 이메일, URL 등 추가 필터링
                    if re.search(r'@|www\.|http:|https:', text):
                        continue
                        
                    # 짧은 텍스트 필터링 (30자 미만)
                    if len(text) < 30:
                        continue
                    
                    # 초록/요약 섹션 식별
                    if re.match(r'^(?:초록|요약|ABSTRACT)$', text, re.IGNORECASE):
                        abstract_found = True
                        current_section = 'abstract'
                        continue
                    
                    # 본문 시작 식별
                    if re.match(r'^(?:본\s*논문은|본\s*연구는|본\s*논문에서는|본\s*연구에서는|서론|INTRODUCTION).*', text, re.IGNORECASE):
                        structure['main_content'] = text
                        break
                    
                    # 의미 있는 문장 추가
                    if len(text) >= 50 and len(re.findall(r'[가-힣]+', text)) >= 5:
                        # 한글이 충분히 포함된 의미있는 문장
                        if '.' in text:
                            parts = text.split('.')
                            for part in parts:
                                if len(part) >= 30 and len(re.findall(r'[가-힣]+', part)) >= 3:
                                    # 깔끔한 문장 형태인 경우
                                    structure['main_content'] = part + '.'
                                    break
                        
                        if not structure['main_content']:
                            structure['main_content'] = text
                            
                    # 섹션에 따른 텍스트 저장
                    if current_section == 'abstract' and abstract_found:
                        if not re.match(r'^(?:키워드|Keywords|주제어):', text):
                            structure['abstract'] += text + ' '
                
                except Exception as e:
                    logger.error(f"블록 처리 중 오류 발생: {str(e)}")
                    continue
            
            # 초록이 없는 경우 첫 번째 의미 있는 텍스트를 본문으로 설정
            if not structure['abstract'] and not structure['main_content'] and sorted_blocks:
                for _, _, text in sorted_blocks:
                    if (len(text) > 50 and 
                        len(re.findall(r'[가-힣]+', text)) >= 5 and
                        not any(re.search(pattern, text) for pattern in self.skip_patterns)):
                        structure['main_content'] = text
                        break
            
            return structure
            
        except Exception as e:
            logger.error(f"논문 구조 식별 중 오류 발생: {str(e)}")
            return structure

    def get_first_meaningful_sentence(self, text: str, section: str = 'abstract') -> str:
        """섹션별 첫 의미 있는 문장 추출"""
        try:
            if not text or not isinstance(text, str):
                logger.warning(f"입력 텍스트가 올바르지 않습니다: {type(text)}")
                return ""
            
            # 메타데이터 제거
            text = self.clean_text(text)
            
            # 메타데이터 패턴 추가 제거
            metadata_patterns = [
                r'^.*(?:대학교|University|Univ|SK\s*Telecom).*$\n?',  # 소속기관
                r'^.*@.*$\n?',  # 이메일
                r'^.*\{.*\}.*$\n?',  # 중괄호 내용
                r'^[A-Z][a-z]+\s+[A-Z][a-z]+.*$\n?',  # 영문 이름
                r'^(?:Abstract|초록|요약)$\n?',  # 섹션 헤더
                r'^\s*(?:Keywords|중심어|주제어):.*$\n?',  # 키워드
                r'^\s*\d+\.\s*\w+.*$\n?',  # 섹션 번호
                r'^\s*(?:표|그림|Fig\.|Table)\s*\d+.*$\n?'  # 표/그림 설명
            ]
            
            for pattern in metadata_patterns:
                text = re.sub(pattern, '', text, flags=re.MULTILINE)
            
            # 본문 시작 식별
            main_content_patterns = [
                r'본\s*(?:논문|연구)(?:은|는|에서는|에서)',
                r'본\s*연구의\s*목적은',
                r'최근\s*(?:들어|에는|에)',
                r'서론'
            ]
            
            main_content_start = None
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                if any(re.search(pattern, line) for pattern in main_content_patterns):
                    main_content_start = i
                    break
            
            if main_content_start is not None:
                text = '\n'.join(lines[main_content_start:])
            
            # 문장 분리 및 필터링
            sentences = []
            for line in text.split('\n'):
                if not line.strip():
                    continue
                    
                # 문장 종결 패턴으로 분리
                parts = re.split(r'(?<=[다까요죠니음임])[.!?]\s+', line)
                for part in parts:
                    part = part.strip()
                    if part and len(part) >= 20:
                        # 한글 문장 패턴 확인
                        if re.search(r'[가-힣]+.*(?:다|까|요|죠|니다|음|임)[.!?]?$', part):
                            sentences.append(part)
            
            # 의미 있는 첫 문장 찾기
            for sentence in sentences:
                # 최소 길이 및 한글 단어 수 확인
                if len(sentence) >= 20 and len(re.findall(r'[가-힣]+', sentence)) >= 3:
                    # 메타데이터 패턴 체크
                    if not any(re.search(pattern, sentence) for pattern in metadata_patterns):
                        # 마침표 추가
                        if not sentence.endswith('.'):
                            sentence += '.'
                        return self.normalize_text(sentence)
            
            return ""
            
        except Exception as e:
            logger.error(f"문장 추출 중 오류 발생: {str(e)}")
            return ""

    def get_first_sentence(self, text: str, section_type: str = 'main') -> str:
        """섹션 타입에 따른 첫 문장 추출"""
        try:
            if not text or not isinstance(text, str):
                logger.warning("입력 텍스트가 올바르지 않습니다.")
                return ""
            
            # 섹션 타입에 따른 처리
            if section_type == 'abstract':
                # 초록에서는 "본 논문은" 또는 "본 연구는" 으로 시작하는 문장 우선
                abstract_patterns = [
                    r'본\s*(?:논문|연구)(?:은|는|에서는)[^.!?]+[.!?]',
                    r'[^.!?]+(?:제안한다|제시한다|기술한다|설명한다)[.!?]'
                ]
                for pattern in abstract_patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        sentence = match.group().strip()
                        if len(sentence) > 20:
                            return self.normalize_text(sentence)
            
            elif section_type == 'main':
                # 본문에서는 일반적인 문장 시작 패턴 검색
                main_patterns = [
                    r'[^.!?]+(?:한다|된다|있다)[.!?]',
                    r'[^.!?]+(?:이다|입니다)[.!?]'
                ]
                for pattern in main_patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        sentence = match.group().strip()
                        if (len(sentence) > 20 and 
                            not sentence.startswith('[') and 
                            not sentence.startswith('그림') and
                            len(re.findall(r'[가-힣]+', sentence)) >= 3):
                            return self.normalize_text(sentence)
            
            # 기본 문장 추출
            sentences = re.split(r'(?<=[다까요죠니음임])[.!?]\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) > 20 and 
                    not sentence.startswith('[') and 
                    not sentence.startswith('그림') and
                    len(re.findall(r'[가-힣]+', sentence)) >= 3):
                    return self.normalize_text(sentence)
            
            return ""
            
        except Exception as e:
            logger.error(f"첫 문장 추출 중 오류 발생: {str(e)}")
            return ""

    def process_page(self, page: Any, page_number: int = 0) -> Dict[str, Any]:
        """페이지 처리 메인 함수"""
        try:
            # 논문 구조 식별
            structure = self.identify_paper_structure(page)
            
            # 첫 문장 추출
            first_sentence = ""
            
            # 직접 페이지 텍스트 처리 시도
            try:
                # 전체 페이지 텍스트 가져오기
                page_text = page.get_text()
                if page_text and len(page_text) > 100:
                    lines = page_text.split('\n')
                    meaningful_lines = []
                    
                    # 의미 있는 라인만 필터링
                    for line in lines:
                        line = line.strip()
                        if (len(line) >= 30 and 
                            len(re.findall(r'[가-힣]+', line)) >= 3 and
                            not any(re.match(pattern, line) for pattern in [
                                r'^\s*(?:표|그림|Fig\.|Table|Figure)\s*\d+', 
                                r'^\s*\d+\s*fps', 
                                r'^\s*(?:\.|,|;)', 
                                r'^\s*\[',
                                r'^\s*\d+\.\d+',
                                r'^\s*References',
                                r'^\s*참고문헌'
                            ])):
                            meaningful_lines.append(line)
                    
                    # 가장 긴 의미 있는 라인 선택
                    if meaningful_lines:
                        longest_line = max(meaningful_lines, key=len)
                        first_sentence = self.normalize_text(longest_line)
                        logger.info(f"페이지 {page_number}: 전체 텍스트에서 직접 추출된 첫 문장 길이: {len(first_sentence)}")
            except Exception as e:
                logger.error(f"페이지 {page_number} 직접 텍스트 추출 중 오류: {str(e)}")
            
            # 직접 추출에 실패한 경우 구조 분석 결과 사용
            if not first_sentence:
                # 초록에서 첫 문장 추출 시도
                if structure['abstract']:
                    first_sentence = self.get_first_meaningful_sentence(structure['abstract'], 'abstract')
                    logger.info(f"페이지 {page_number}: 초록에서 추출된 첫 문장 길이: {len(first_sentence)}")
                
                # 초록에서 찾지 못한 경우 본문에서 시도
                if not first_sentence and structure['main_content']:
                    first_sentence = self.get_first_meaningful_sentence(structure['main_content'], 'main')
                    logger.info(f"페이지 {page_number}: 본문에서 추출된 첫 문장 길이: {len(first_sentence)}")
                
                # 최종 정규화
                if first_sentence:
                    first_sentence = self.normalize_text(first_sentence)
            
            # 마지막 시도: 전체 페이지 직접 처리
            if not first_sentence:
                try:
                    # 페이지 텍스트를 문장으로 분리
                    page_text = page.get_text()
                    if page_text and len(page_text) > 30:
                        # 문장 후보 추출
                        sentence_candidates = re.split(r'(?<=[.!?])\s+', page_text)
                        for candidate in sentence_candidates:
                            if (len(candidate) >= 30 and 
                                len(re.findall(r'[가-힣]+', candidate)) >= 3 and
                                not any(re.search(pattern, candidate) for pattern in [
                                    r'^(?:표|그림|Fig\.|Table)', 
                                    r'^\d+\s*fps',
                                    r'^\d+\.\d+'
                                ])):
                                first_sentence = self.normalize_text(candidate)
                                logger.info(f"페이지 {page_number}: 마지막 시도에서 추출된 첫 문장 길이: {len(first_sentence)}")
                                break
                except Exception as e:
                    logger.error(f"페이지 {page_number} 최종 텍스트 추출 중 오류: {str(e)}")
            
            return {
                'structure': structure,
                'first_sentence': first_sentence,
                'page_number': page_number,
                'text_length': len(first_sentence) if first_sentence else 0
            }
            
        except Exception as e:
            logger.error(f"페이지 {page_number} 처리 중 오류 발생: {str(e)}")
            return {
                'structure': {
                    'title': '',
                    'authors': '',
                    'abstract': '',
                    'main_content': '',
                    'sections': []
                },
                'first_sentence': '',
                'page_number': page_number,
                'text_length': 0
            } 