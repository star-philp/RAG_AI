def is_valid_pdf(file_path: str) -> bool:
    """PDF 파일 유효성 검사"""
    try:
        import fitz  # PyMuPDF
        
        # PDF 파일 열기 시도
        doc = fitz.open(file_path)
        doc.close()
        return True
        
    except Exception as e:
        logger.error(f"PDF 검증 실패: {str(e)}")
        return False 