import streamlit as st
import tempfile
import logging

st.set_page_config(page_title="ChatGPT", page_icon=":robot:")
st.title("ChatGPT")

def handle_pdf_upload(uploaded_file):
    """PDF 파일 업로드 처리"""
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
            
        # 파일 검증
        if not is_valid_pdf(temp_path):
            raise ValueError("유효하지 않은 PDF 파일입니다.")
            
        return temp_path
        
    except Exception as e:
        logger.error(f"파일 업로드 중 오류 발생: {str(e)}")
        raise