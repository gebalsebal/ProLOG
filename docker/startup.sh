#!/bin/bash
set -e

echo "=============================="
echo "  gcube AlphaFold 초기화 시작"
echo "=============================="

REPO_DIR="/app/alphafold"
PARAMS_DIR="/data/params"

# ── 1. GitHub 코드 동기화 ────────────────────────────────
echo "[1/5] GitHub 코드 동기화..."
if [ -d "${REPO_DIR}/.git" ]; then
    cd ${REPO_DIR}
    git pull
else
    echo "  → 최초 clone 실행"
    rm -rf ${REPO_DIR}
    git clone https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git ${REPO_DIR}
    cd ${REPO_DIR}
fi

# ── 2. AlphaFold 가중치 확인/다운로드 ─────────────────────
echo "[2/5] AlphaFold 가중치 확인..."
PARAMS_FILE="${PARAMS_DIR}/params_model_1.npz"
if [ -f "${PARAMS_FILE}" ]; then
    echo "  → 가중치 이미 존재, 스킵"
else
    echo "  → 가중치 다운로드 시작 (~3.5GB)"
    mkdir -p ${PARAMS_DIR}
    wget -q --show-progress \
        https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar \
        -O ${PARAMS_DIR}/alphafold_params.tar
    tar -xf ${PARAMS_DIR}/alphafold_params.tar -C ${PARAMS_DIR}
    rm ${PARAMS_DIR}/alphafold_params.tar
    echo "  → 가중치 다운로드 완료"
fi

# ── 3. OpenCode 설정 파일 적용 ────────────────────────────
echo "[3/5] OpenCode 설정 복사..."
mkdir -p ~/.config/opencode
cp -r ${REPO_DIR}/opencode-config/* ~/.config/opencode/

cd ~/.config/opencode
npm install --no-audit --no-fund

NPM_PREFIX=$(npm prefix -g)
sed -i "s#__NPM_PREFIX__#${NPM_PREFIX}#g" opencode.jsonc tui.json
echo "  → 설정 파일 경로 치환 완료 (${NPM_PREFIX})"

# ── 4. OpenCode 인증 복원 (base64 → auth.json) ────────────
echo "[4/5] OpenCode 인증 복원..."
if [ -n "${OPENCODE_AUTH_B64}" ]; then
    mkdir -p ~/.local/share/opencode
    echo "${OPENCODE_AUTH_B64}" | base64 -d > ~/.local/share/opencode/auth.json
    echo "  → 인증 복원 완료"
else
    echo "  ⚠ OPENCODE_AUTH_B64 환경변수 없음 — 인증 없이 시작됨"
fi

# ── 5. 마무리 ──────────────────────────────────────────────
echo "[5/5] GPU 라이브러리 경로 설정..."
ldconfig

echo ""
echo "=============================="
echo "  초기화 완료!"
echo "  - 코드: ${REPO_DIR}"
echo "  - 가중치: ${PARAMS_DIR}"
echo "  - opencode 설정: ~/.config/opencode"
echo "=============================="

sleep infinity