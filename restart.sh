#!/bin/bash

# Streamlit 캐시 삭제
rm -rf ~/.streamlit/cache

# 임시 파일 정리
find /tmp -name "*.pdf" -mtime +1 -delete

# 서비스 재시작
streamlit run main.py 