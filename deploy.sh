#!/bin/bash

# 라즈베리파이 정보
RASPBERRY_PI_IP="192.168.219.107"
RASPBERRY_PI_USER="rainstar"
PROJECT_PATH="/home/rainstar/VocLangChain"

# 소스 코드 동기화
rsync -avz --exclude 'venv' --exclude '__pycache__' \
    --exclude '.git' --exclude 'node_modules' \
    ./ $RASPBERRY_PI_USER@$RASPBERRY_PI_IP:$PROJECT_PATH/

# 원격 실행 (도커 재시작)
ssh $RASPBERRY_PI_USER@$RASPBERRY_PI_IP << EOF
    cd $PROJECT_PATH
    docker pull ${DOCKER_USERNAME:-your-dockerhub-username}/rag_ai:latest
    docker-compose down
    docker-compose up -d
EOF

echo "배포가 완료되었습니다." 