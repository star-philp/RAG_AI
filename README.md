# RAG_AI

LLM(멀티모달) + RAG 기반 PDF 분석 및 질의응답 시스템

## 프로젝트 개요

이 프로젝트는 대규모 언어 모델(LLM)과 검색 증강 생성(RAG) 기술을 활용하여 PDF 문서를 분석하고 질의응답을 제공하는 시스템입니다. 멀티모달 기능을 통해 텍스트뿐만 아니라 이미지, 표, 그래프 등을 포함한 문서를 효과적으로 처리합니다.

## 주요 기능

- PDF 문서 업로드 및 분석
- 문서 내용 기반 질의응답
- 멀티모달 콘텐츠 처리 (텍스트, 이미지, 표 등)
- 업무 자동화 및 프로세스 최적화

## 설치 및 실행 방법

### 로컬 환경에서 실행

```bash
# 가상환경 생성 및 활성화
python3 -m venv VocLangChain
source VocLangChain/bin/activate  # Windows: VocLangChain\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
streamlit run main2.py
```

### Docker를 사용한 실행

```bash
# Docker 이미지 빌드
docker build -t rag_ai .

# Docker 컨테이너 실행
docker run -p 8501:8501 rag_ai
```

## CI/CD 설정

이 프로젝트는 GitHub Actions를 사용하여 CI/CD를 구성합니다. 다음 단계를 따라 설정하세요:

1. GitHub 리포지토리에 다음 시크릿 값을 설정합니다:

   - `DOCKER_USERNAME`: Docker Hub 사용자 이름
   - `DOCKER_PASSWORD`: Docker Hub 패스워드

2. 배포 대상 서버(예: 라즈베리파이)에서 다음 명령을 실행하여 필요한 도구를 설치합니다:

   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

3. `deploy.sh` 스크립트를 실행하여 수동으로 배포합니다:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## 환경 변수

필요한 경우 다음 환경 변수를 설정합니다:

- `TESSDATA_PREFIX`: Tesseract OCR 데이터 경로 (기본값: `/usr/local/share/tessdata/`)
- `STREAMLIT_SERVER_PORT`: Streamlit 서버 포트 (기본값: 8501)

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.
