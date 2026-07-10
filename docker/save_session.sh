mkdir -p /app/alphafold/scripts
cat > /app/alphafold/scripts/save_session.sh << 'SCRIPT'
#!/bin/bash
set -e
REPO_DIR="/app/alphafold"
BRANCH="opencode-session"

cd "${REPO_DIR}"

# 세션 데이터만 임시 폴더에 모으기 (auth.json 제외)
rm -rf /tmp/session-backup
mkdir -p /tmp/session-backup
rsync -a --exclude 'auth.json' ~/.local/share/opencode/ /tmp/session-backup/

# 전용 브랜치로 전환 (없으면 orphan으로 새로 생성)
git fetch origin ${BRANCH} 2>/dev/null && git checkout ${BRANCH} || git checkout --orphan ${BRANCH}
git rm -rf . --quiet 2>/dev/null || true
cp -r /tmp/session-backup/. .

git add -A
git -c user.email="gcube@bot" -c user.name="gcube-bot" \
    commit -m "session backup $(date -u +%Y-%m-%dT%H:%M:%SZ)" --allow-empty
git push origin ${BRANCH} --force

git checkout main
echo "✅ 세션 백업 완료 (branch: ${BRANCH})"
SCRIPT
chmod +x /app/alphafold/scripts/save_session.sh