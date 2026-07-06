#!/bin/bash
set -o pipefail

LOG_FILE="/var/log/startup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

main() {
    set -e
    echo "=============================="
    echo "  gcube AlphaFold 초기화 시작"
    echo "=============================="

    REPO_DIR="/app/alphafold"
    PARAMS_DIR="/data/params"

    # ── 0. 환경변수를 SSH 세션용으로도 저장 ─────────────────
    echo "[0/5] 환경변수를 SSH 세션용으로 저장..."
    {
      echo "GITHUB_REPO=${GITHUB_REPO}"
      echo "GITHUB_TOKEN=${GITHUB_TOKEN}"
      echo "OPENCODE_AUTH_B64=${OPENCODE_AUTH_B64}"
    } >> /etc/environment

cat > /etc/profile.d/gcube_env.sh << EOF
export GITHUB_REPO="${GITHUB_REPO}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
export OPENCODE_AUTH_B64="${OPENCODE_AUTH_B64}"
export PATH="/opt/conda/bin:\$PATH"
export LD_LIBRARY_PATH="/opt/conda/lib:\$LD_LIBRARY_PATH"
EOF
    chmod +x /etc/profile.d/gcube_env.sh

    # ── 1. GitHub 코드 동기화 ────────────────────────────
    echo "[1/5] GitHub 코드 동기화..."
    cd /   # ★ REPO_DIR을 지우기 전에 cwd를 안전한 곳으로 이동
    if [ -d "${REPO_DIR}/.git" ]; then
        cd "${REPO_DIR}"
        git pull
    else
        echo "  → 최초 clone 실행"
        rm -rf "${REPO_DIR}"
        git clone "https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "${REPO_DIR}"
        cd "${REPO_DIR}"
    fi

    # ── 2. AlphaFold 가중치 확인/다운로드 ─────────────────
    echo "[2/5] AlphaFold 가중치 확인..."
    PARAMS_FILE="${PARAMS_DIR}/params_model_1.npz"
    if [ -f "${PARAMS_FILE}" ]; then
        echo "  → 가중치 이미 존재, 스킵"
    else
        echo "  → 가중치 다운로드 시작 (~3.5GB)"
        mkdir -p "${PARAMS_DIR}"
        wget -q -P "${PARAMS_DIR}" \
            https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar
        tar -xf "${PARAMS_DIR}/alphafold_params_2022-12-06.tar" -C "${PARAMS_DIR}"
        rm "${PARAMS_DIR}/alphafold_params_2022-12-06.tar"
        echo "  → 가중치 다운로드 완료"
    fi

    # ── 3. OpenCode 설정 파일 적용 ─────────────────────────
    echo "[3/5] OpenCode 설정 복사..."
    mkdir -p ~/.config/opencode
    if [ -d "${REPO_DIR}/opencode-config" ]; then
        cp -r "${REPO_DIR}/opencode-config/." ~/.config/opencode/
        cd ~/.config/opencode
        npm install --no-audit --no-fund
        NPM_PREFIX=$(npm prefix -g)
        sed -i "s#__NPM_PREFIX__#${NPM_PREFIX}#g" opencode.jsonc tui.json 2>/dev/null || true
        echo "  → 설정 파일 경로 치환 완료 (${NPM_PREFIX})"
    else
        echo "  ⚠ ${REPO_DIR}/opencode-config 폴더 없음 — OpenCode 설정 스킵"
    fi

    # ── 4. OpenCode 인증 복원 ──────────────────────────────
    echo "[4/5] OpenCode 인증 복원..."
    if [ -n "${OPENCODE_AUTH_B64}" ]; then
        mkdir -p ~/.local/share/opencode
        echo "${OPENCODE_AUTH_B64}" | base64 -d > ~/.local/share/opencode/auth.json
        echo "  → 인증 복원 완료"
    else
        echo "  ⚠ OPENCODE_AUTH_B64 환경변수 없음 — 인증 없이 시작됨"
    fi

    # ── 5. 마무리 ──────────────────────────────────────────
    echo "[5/5] GPU 라이브러리 경로 설정..."
    ldconfig

    echo ""
    echo "=============================="
    echo "  초기화 완료!"
    echo "=============================="
}

# main이 어디서 실패하든 컨테이너는 절대 죽지 않고 sleep infinity까지 도달
main || echo "⚠ 초기화 중 오류 발생 — 자세한 내용은 ${LOG_FILE} 확인"

echo "컨테이너 대기 상태로 전환합니다. (SSH 접속 가능)"
sleep infinity