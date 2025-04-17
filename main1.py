import os
import easyocr
import streamlit as st
import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from pdfminer.high_level import extract_text
import fitz  # PyMuPDF
from PIL import Image
import io

# 페이지 설정
st.set_page_config(page_title="PDF Processor and QA System", page_icon=":robot:")

# API 키 설정
# 환경 변수에서 API 키를 가져옵니다. 실행 전 OPENAI_API_KEY 환경 변수를 설정해야 합니다.
# os.environ['OPENAI_API_KEY'] = 'YOUR_API_KEY_HERE'

# PDF 로더 설정 및 데이터 처리
def process_pdf(file_path):
    loader = PyPDFLoader(file_path, extract_images=True)
    pages = loader.load_and_split()

    # 이미지 추출을 위해 PyMuPDF 사용
    doc = fitz.open(file_path)
    images = []
    for page_num in range(len(doc)):
        for img in doc.get_page_images(page_num):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert("RGB")  # 이미지를 RGB로 변환

            # 이미지 크기 및 모드 확인
            st.write(f"Processing image {page_num + 1}, Mode: {image.mode}, Size: {image.size}")
            
            # 이미지 크기 조정
            try:
                image = image.resize((1024, 1024), Image.LANCZOS)  # Image.LANCZOS 사용
            except Exception as e:
                st.write(f"Error resizing image: {e}")
                continue
            
            images.append(image)
    
    # 텍스트 추출을 위해 PDFMiner 사용
    text = extract_text(file_path)
    
    # EasyOCR을 사용하여 이미지에서 텍스트 추출
    reader = easyocr.Reader(['ko', 'en'])  # 한국어와 영어 지원
    ocr_text = ""
    for image in images:
        try:
            # PIL 이미지를 numpy 배열로 변환
            image_np = np.array(image)
            result = reader.readtext(image_np)
            ocr_text += " ".join([text[1] for text in result]) + "\n"
        except Exception as e:
            st.write(f"EasyOCR로 이미지 처리 중 오류 발생: {e}")
            continue
    
    return pages, images, text, ocr_text

# 벡터 데이터베이스 설정
def setup_vector_db(pages):
    embeddings = OpenAIEmbeddings()
    faiss_index = FAISS.from_documents(pages, embeddings)
    return faiss_index

# 질문에 답변하기
def answer_question(faiss_index, question):
    docs = faiss_index.similarity_search(question, k=2)
    results = []
    for doc in docs:
        results.append(f"Page {doc.metadata['page']}: {doc.page_content[:300]}")
    return results

# 파일 경로를 직접 사용
file_path = "/Users/rainstar/Paper/3DPOSE/mueller2022instant.pdf"

if file_path:
    # PDF 처리
    with st.spinner('Processing PDF...'):
        pages, images, text, ocr_text = process_pdf(file_path)
    
    # 벡터 데이터베이스 설정
    faiss_index = setup_vector_db(pages)
    
    # 질문 입력
    question = st.text_input("Ask a question about the PDF")
    
    if question:
        answers = answer_question(faiss_index, question)
        for answer in answers:
            st.write(answer)

    # 추가 정보 표시
    st.write("Extracted Text from PDF:")
    st.text(text[:500])  # 첫 500자만 표시
    
    st.write("OCR Text from Images:")
    st.text(ocr_text[:500])  # 첫 500자만 표시
    
    st.write("Extracted Images:")
    for img in images:
        st.image(img)

    st.write("Processed Pages:")
    st.write(pages[0].page_content)  # 첫 번째 페이지 내용 표시
