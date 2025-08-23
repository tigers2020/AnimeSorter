#!/bin/bash
# AnimeSorter 코드 품질 검사 스크립트
# Bash 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 옵션 파싱
FULL_MODE=false
QUICK_MODE=false
FIX_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL_MODE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--full] [--quick] [--fix]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}🔍 AnimeSorter 코드 품질 검사 시작...${NC}"
echo -e "${GRAY}==================================================${NC}"

ERROR_COUNT=0
WARNING_COUNT=0

# 가상환경 활성화 확인
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  가상환경이 활성화되지 않았습니다.${NC}"
    echo -e "${YELLOW}   source venv/bin/activate를 실행해주세요.${NC}"
    ((WARNING_COUNT++))
fi

# 1. Ruff 린팅 검사
echo -e "\n${BLUE}1️⃣  Ruff 린팅 검사...${NC}"
if $FIX_MODE; then
    if ruff check src --fix; then
        echo -e "${GREEN}✅ Ruff 검사 통과${NC}"
    else
        echo -e "${RED}❌ Ruff 검사 실패${NC}"
        ((ERROR_COUNT++))
    fi
else
    if ruff check src; then
        echo -e "${GREEN}✅ Ruff 검사 통과${NC}"
    else
        echo -e "${RED}❌ Ruff 검사 실패${NC}"
        ((ERROR_COUNT++))
    fi
fi

# 2. MyPy 타입 검사
echo -e "\n${BLUE}2️⃣  MyPy 타입 검사...${NC}"
if mypy src --ignore-missing-imports; then
    echo -e "${GREEN}✅ MyPy 검사 통과${NC}"
else
    echo -e "${RED}❌ MyPy 검사 실패${NC}"
    ((ERROR_COUNT++))
fi

# 3. 복잡도 검사
echo -e "\n${BLUE}3️⃣  복잡도 검사...${NC}"
radon cc src -a --total-average
if xenon src --max-absolute B --max-modules A --max-average A; then
    echo -e "${GREEN}✅ 복잡도 검사 통과${NC}"
else
    echo -e "${RED}❌ 복잡도 검사 실패${NC}"
    ((ERROR_COUNT++))
fi

# 4. 보안 검사
echo -e "\n${BLUE}4️⃣  보안 검사...${NC}"
if pip-audit --desc; then
    echo -e "${GREEN}✅ 보안 검사 통과${NC}"
else
    echo -e "${RED}❌ 보안 검사 실패${NC}"
    ((ERROR_COUNT++))
fi

# 5. 의존성 검사
echo -e "\n${BLUE}5️⃣  의존성 검사...${NC}"
if deptry src; then
    echo -e "${GREEN}✅ 의존성 검사 통과${NC}"
else
    echo -e "${RED}❌ 의존성 검사 실패${NC}"
    ((ERROR_COUNT++))
fi

# 6. 미사용 코드 검사
echo -e "\n${BLUE}6️⃣  미사용 코드 검사...${NC}"
if vulture src --min-confidence 80; then
    echo -e "${GREEN}✅ 미사용 코드 검사 통과${NC}"
else
    echo -e "${RED}❌ 미사용 코드 발견${NC}"
    ((ERROR_COUNT++))
fi

# 7. 테스트 실행 (Quick 모드가 아닌 경우)
if ! $QUICK_MODE; then
    echo -e "\n${BLUE}7️⃣  테스트 실행...${NC}"

    # Qt 환경 설정
    export QT_QPA_PLATFORM=offscreen

    # 스모크 테스트
    echo -e "   ${CYAN}스모크 테스트...${NC}"
    if python -m pytest tests/smoke/ -v; then
        echo -e "${GREEN}✅ 스모크 테스트 통과${NC}"
    else
        echo -e "${RED}❌ 스모크 테스트 실패${NC}"
        ((ERROR_COUNT++))
    fi

    # 베이스 컴포넌트 테스트
    echo -e "   ${CYAN}베이스 컴포넌트 테스트...${NC}"
    if python -m pytest tests/test_base_components.py -v; then
        echo -e "${GREEN}✅ 베이스 컴포넌트 테스트 통과${NC}"
    else
        echo -e "${RED}❌ 베이스 컴포넌트 테스트 실패${NC}"
        ((ERROR_COUNT++))
    fi
fi

# 8. 커버리지 검사 (Full 모드인 경우)
if $FULL_MODE; then
    echo -e "\n${BLUE}8️⃣  커버리지 검사...${NC}"
    if python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html; then
        echo -e "${GREEN}✅ 커버리지 검사 완료 (htmlcov/index.html 확인)${NC}"
    else
        echo -e "${RED}❌ 커버리지 검사 실패${NC}"
        ((ERROR_COUNT++))
    fi
fi

# 결과 요약
echo -e "\n${GRAY}==================================================${NC}"
echo -e "${CYAN}📋 품질 검사 결과 요약${NC}"

if [[ $ERROR_COUNT -eq 0 && $WARNING_COUNT -eq 0 ]]; then
    echo -e "${GREEN}🎉 모든 품질 검사 통과!${NC}"
    echo -e "${GREEN}   코드가 릴리스 준비되었습니다.${NC}"
    exit 0
elif [[ $ERROR_COUNT -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  경고 ${WARNING_COUNT}개가 있지만 모든 필수 검사 통과${NC}"
    exit 0
else
    echo -e "${RED}❌ 오류 ${ERROR_COUNT}개, 경고 ${WARNING_COUNT}개${NC}"
    echo -e "${RED}   문제를 해결한 후 다시 실행해주세요.${NC}"
    exit 1
fi
