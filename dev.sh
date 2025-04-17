#!/bin/bash

# 개발 모드 실행
if [ "$1" == "run" ]; then
    streamlit run main2.py

# 빠른 배포
elif [ "$1" == "deploy" ]; then
    git add .
    git commit -m "Update: $(date +%Y%m%d-%H%M)"
    git push
    ./deploy.sh

# 로그 확인
elif [ "$1" == "logs" ]; then
    ssh rainstar@192.168.219.107 'docker-compose logs -f'

# 상태 확인
elif [ "$1" == "status" ]; then
    ssh rainstar@192.168.219.107 'docker ps'
fi 