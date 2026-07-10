#!/bin/bash
set -o pipefail

LOG_FILE="/var/log/startup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

REPO_DIR="/app/alphafold"
PARAMS_DIR="/data/params"

# ── 종료 시 자동 세션 저장 (핵심 추가) ──────────────────────
save_and_exit() {
    echo "🛑 종료 신호 감지 — 세션 자동 저장 중..."
    bash "${REPO_DIR}/scripts/save_session.sh" || echo "⚠ 세션 저장 실패 (무시하고 종료)"
    exit 0
}
trap save_and_exit TERM INT

main() {
    set -e
    echo "=============================="
    echo "  gcube AlphaFold 초기화 시작"
    echo "=============================="

    # ── 0. 환경변수/로케일을 ~/.bashrc에 직접 기록 ──────────
    echo "[0/5] 환경변수/로케일 설정..."
    if ! grep -q "gcube-env-fix" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << EOF
# gcube-env-fix
export GITHUB_REPO="${GITHUB_REPO}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PATH="/opt/conda/bin:/opt/conda/envs/colabfold/bin:/usr/sbin:/sbin:\$PATH"
EOF
    fi

    # ── 1. GitHub 코드 동기화 ────────────────────────────
    echo "[1/5] GitHub 코드 동기화..."
    cd /
    if [ -d "${REPO_DIR}/.git" ]; then
        cd "${REPO_DIR}"
        git pull
    else
        rm -rf "${REPO_DIR}"
        git clone "https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "${REPO_DIR}"
        cd "${REPO_DIR}"
    fi

    # ── 1.5. OpenCode 세션 데이터 복원 ───────────────────
    echo "[1.5/5] OpenCode 세션 데이터 복원..."
    mkdir -p ~/.local/share/opencode
    if git ls-remote --exit-code --heads origin opencode-session &>/dev/null; then
        git fetch origin opencode-session --quiet
        git archive origin/opencode-session | tar -x -C ~/.local/share/opencode/
        echo "  → 세션 데이터 복원 완료"
    else
        echo "  → 저장된 세션 없음 (최초 실행)"
    fi

    # ── 2. AlphaFold 가중치 확인/다운로드 ────────────────
    echo "[2/5] AlphaFold 가중치 확인..."
    PARAMS_FILE="${PARAMS_DIR}/params_model_1.npz"
    if [ -f "${PARAMS_FILE}" ]; then
        echo "  → 가중치 이미 존재, 스킵"
    else
        mkdir -p "${PARAMS_DIR}"
        wget -q -P "${PARAMS_DIR}" \
            https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar
        tar -xf "${PARAMS_DIR}/alphafold_params_2022-12-06.tar" -C "${PARAMS_DIR}"
        rm "${PARAMS_DIR}/alphafold_params_2022-12-06.tar"
    fi

    # ── 3. OpenCode 설정 파일 적용 ────────────────────────
    echo "[3/5] OpenCode 설정 복사..."
    mkdir -p ~/.config/opencode
    if [ -d "${REPO_DIR}/opencode-config" ]; then
        cp -r "${REPO_DIR}/opencode-config/." ~/.config/opencode/
        cd ~/.config/opencode
        npm install --no-audit --no-fund
        NPM_PREFIX=$(npm prefix -g)
        sed -i "s#__NPM_PREFIX__#${NPM_PREFIX}#g" opencode.jsonc tui.json 2>/dev/null || true
    fi

    # ── 4. OpenCode 인증 확인 ─────────────────────────────
    echo "[4/5] OpenCode 인증 확인..."
    if [ -f ~/.local/share/opencode/auth.json ]; then
        echo "  → 인증 정보 존재 (세션 백업에서 복원됨)"
    else
        echo "  ⚠ 인증 정보 없음 — SSH 접속 후 로그인 필요:"
        echo "     npx -y opencode-openai-device-auth@latest"
    fi

    # ── 5. 마무리 ──────────────────────────────────────────
    echo "[5/5] GPU 라이브러리 경로 설정..."
    ldconfig

    echo "=============================="
    echo "  초기화 완료!"
    echo "=============================="
}

main || echo "⚠ 초기화 중 오류 발생 — ${LOG_FILE} 확인"

echo "컨테이너 대기 상태로 전환합니다. (SSH 접속 가능)"
sleep infinity &
wait $!