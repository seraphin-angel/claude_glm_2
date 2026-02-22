#!/bin/bash
#
# safe-codex.sh - 機密ファイルを除外してCodex CLIを安全に実行するラッパー
#
# 使用方法:
#   ./safe-codex.sh <project_directory> "<request>"
#
# 例:
#   ./safe-codex.sh ~/my-project "コードレビューして改善点を指摘してください"
#
# 環境変数:
#   CODEX_SKIP_CONFIRM=1  - 確認プロンプトをスキップ
#   CODEX_MAX_SIZE_MB=500 - 最大コピーサイズ（MB、デフォルト500）
#   CODEX_AUDIT_LOG=path  - 監査ログの出力先
#

set -euo pipefail

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
PROJECT_DIR="${1:-.}"
REQUEST="${2:-}"
SAFE_DIR=""
MAX_SIZE_MB="${CODEX_MAX_SIZE_MB:-500}"
AUDIT_LOG="${CODEX_AUDIT_LOG:-}"

# codexコマンドのパス（固定パスを優先し、環境変数での上書きを禁止）
find_codex_cmd() {
    local candidates=(
        "/usr/local/share/npm-global/bin/codex"
        "/usr/local/bin/codex"
        "/usr/bin/codex"
    )
    for candidate in "${candidates[@]}"; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    # PATHから検索（最終手段）
    if command -v codex &> /dev/null; then
        command -v codex
        return 0
    fi
    return 1
}

CODEX_CMD=""
if ! CODEX_CMD=$(find_codex_cmd); then
    echo "エラー: codexコマンドが見つかりません"
    echo "以下のパスにcodexをインストールしてください:"
    echo "  /usr/local/share/npm-global/bin/codex"
    echo "  /usr/local/bin/codex"
    exit 1
fi

# rsync の存在確認（セキュアなコピーに必須）
if ! command -v rsync &> /dev/null; then
    echo "エラー: rsyncがインストールされていません"
    echo "インストール: sudo apt-get install rsync (Debian/Ubuntu) または brew install rsync (macOS)"
    exit 1
fi

# ──────────────────────────────────────────────
# 除外パターン（機密ファイル）- rsync の --exclude 用
# ──────────────────────────────────────────────
EXCLUDE_PATTERNS=(
    # 環境変数・設定ファイル
    ".env"
    ".env.*"
    ".env.local"
    ".env.production"
    ".env.staging"

    # 秘密鍵・証明書
    "*.pem"
    "*.key"
    "*.p12"
    "*.pfx"
    "*.jks"
    "*.keystore"
    "*.crt"

    # 認証情報ファイル
    "credentials.*"
    "secrets.*"
    "*.secret"
    ".htpasswd"
    ".netrc"
    ".npmrc"
    ".pypirc"
    "wp-config.php"

    # SSH鍵
    "id_rsa*"
    "id_ed25519*"
    "id_ecdsa*"
    "id_dsa*"
    "known_hosts"
    "authorized_keys"

    # 暗号化関連
    "*.pgp"
    "*.gpg"
    "*.asc"

    # クラウドサービス認証
    "service-account*.json"
    "*.service-account.json"
    "firebase-*.json"
    "google-services.json"
    "token.json"
    "*_token.json"
    "kubeconfig"
    "terraform.tfstate"
    "terraform.tfstate.backup"

    # データベースファイル
    "*.sqlite"
    "*.sqlite3"
    "*.db"

    # Spring Boot 設定（DB認証情報を含む可能性）
    "application-*.yml"
    "application-*.yaml"
    "application-*.properties"

    # Docker認証
    "config.json"
)

# 除外ディレクトリ
EXCLUDE_DIRS=(
    ".secrets"
    "secrets"
    ".git"
    "node_modules"
    ".aws"
    ".ssh"
    ".docker"
    ".kube"
    ".gnupg"
    "__pycache__"
    ".terraform"
    "vendor"
    "dist"
    "build"
    ".next"
)

# ──────────────────────────────────────────────
# ヘルパー関数
# ──────────────────────────────────────────────
print_banner() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Safe Codex Wrapper - 機密ファイルを除外して実行            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
}

cleanup() {
    if [ -n "$SAFE_DIR" ] && [ -d "$SAFE_DIR" ]; then
        rm -rf "$SAFE_DIR"
    fi
}

trap cleanup EXIT

log_audit() {
    if [ -n "$AUDIT_LOG" ]; then
        echo "[$(date -Iseconds)] $1" >> "$AUDIT_LOG"
    fi
}

abort_with_error() {
    echo "エラー: $1" >&2
    log_audit "ABORT: $1"
    exit 1
}

# ──────────────────────────────────────────────
# 引数バリデーション
# ──────────────────────────────────────────────
if [ -z "$REQUEST" ]; then
    echo "エラー: リクエストが指定されていません"
    echo ""
    echo "使用方法: $0 <project_directory> \"<request>\""
    echo "例: $0 ~/my-project \"コードレビューして\""
    exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
    abort_with_error "ディレクトリが見つかりません: $PROJECT_DIR"
fi

# 絶対パスに変換（シンボリックリンクを解決しない）
PROJECT_DIR=$(cd -P "$PROJECT_DIR" && pwd)

print_banner

echo ""
echo "📂 プロジェクト: $PROJECT_DIR"
echo "🤖 Codex: $CODEX_CMD"
echo ""

# ──────────────────────────────────────────────
# プロジェクトサイズチェック
# ──────────────────────────────────────────────
echo "📏 プロジェクトサイズを確認中..."
PROJECT_SIZE_KB=$(du -sk "$PROJECT_DIR" 2>/dev/null | cut -f1)
PROJECT_SIZE_MB=$((PROJECT_SIZE_KB / 1024))

if [ "$PROJECT_SIZE_MB" -gt "$MAX_SIZE_MB" ]; then
    abort_with_error "プロジェクトサイズ（${PROJECT_SIZE_MB}MB）が上限（${MAX_SIZE_MB}MB）を超えています。CODEX_MAX_SIZE_MB環境変数で上限を変更できます。"
fi
echo "   サイズ: ${PROJECT_SIZE_MB}MB（上限: ${MAX_SIZE_MB}MB）"
echo ""

# ──────────────────────────────────────────────
# 検出された機密ファイルを報告
# ──────────────────────────────────────────────
echo "🔍 機密ファイルのスキャン中..."
FOUND_SECRETS=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    while IFS= read -r file; do
        [ -n "$file" ] && FOUND_SECRETS+=("$file")
    done < <(find "$PROJECT_DIR" -name "$pattern" -not -type d 2>/dev/null || true)
done

for dir in "${EXCLUDE_DIRS[@]}"; do
    while IFS= read -r d; do
        [ -n "$d" ] && FOUND_SECRETS+=("$d/")
    done < <(find "$PROJECT_DIR" -type d -name "$dir" 2>/dev/null || true)
done

if [ ${#FOUND_SECRETS[@]} -gt 0 ]; then
    echo "⚠️  以下の機密ファイル/ディレクトリが検出されました（除外されます）:"
    for file in "${FOUND_SECRETS[@]}"; do
        echo "   - ${file#"$PROJECT_DIR"/}"
    done
    echo ""
    log_audit "EXCLUDED files: ${FOUND_SECRETS[*]}"
else
    echo "✅ 機密ファイルは検出されませんでした"
    echo ""
fi

# ──────────────────────────────────────────────
# ユーザー確認
# ──────────────────────────────────────────────
if [ "${CODEX_SKIP_CONFIRM:-}" != "1" ]; then
    echo "⚠️  このプロジェクトのソースコードがOpenAIのサーバーに送信されます。"
    echo "   機密情報を含むプロジェクトでは、代わりに code-reviewer エージェントの使用を推奨します。"
    echo ""
    read -r -p "続行しますか？ (y/N): " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        echo "キャンセルしました。"
        log_audit "CANCELLED by user"
        exit 0
    fi
    echo ""
fi

# ──────────────────────────────────────────────
# 安全なディレクトリにコピー（除外パターンを最初から適用）
# ──────────────────────────────────────────────
echo "📋 ファイルをコピー中（機密ファイルを除外）..."

SAFE_DIR=$(mktemp -d)

# rsync の除外オプションを構築
RSYNC_EXCLUDES=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    RSYNC_EXCLUDES+=("--exclude=$pattern")
done
for dir in "${EXCLUDE_DIRS[@]}"; do
    RSYNC_EXCLUDES+=("--exclude=$dir/")
done

# .gitignore が存在する場合、その除外ルールも適用
if [ -f "$PROJECT_DIR/.gitignore" ]; then
    RSYNC_EXCLUDES+=("--filter=:- .gitignore")
    echo "   📄 .gitignore の除外ルールも適用します"
fi

# rsync でコピー（シンボリックリンクを追跡しない、除外パターン適用済み）
if ! rsync -a \
    --no-links \
    "${RSYNC_EXCLUDES[@]}" \
    "$PROJECT_DIR/" \
    "$SAFE_DIR/"; then
    abort_with_error "ファイルのコピーに失敗しました"
fi

COPIED_FILES=$(find "$SAFE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
COPIED_SIZE_KB=$(du -sk "$SAFE_DIR" 2>/dev/null | cut -f1)
COPIED_SIZE_MB=$((COPIED_SIZE_KB / 1024))

echo "✅ $COPIED_FILES ファイルをコピーしました（${COPIED_SIZE_MB}MB）"
echo ""

log_audit "SENT: $COPIED_FILES files (${COPIED_SIZE_MB}MB) from $PROJECT_DIR to OpenAI via Codex"

# ──────────────────────────────────────────────
# 送信前に機密ファイルが含まれていないか最終確認
# ──────────────────────────────────────────────
echo "🔒 最終セキュリティチェック..."
LEAKED_FILES=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    while IFS= read -r file; do
        [ -n "$file" ] && LEAKED_FILES+=("$file")
    done < <(find "$SAFE_DIR" -name "$pattern" -not -type d 2>/dev/null || true)
done

if [ ${#LEAKED_FILES[@]} -gt 0 ]; then
    echo "🚨 除外されるべきファイルが検出されました！処理を中断します:"
    for file in "${LEAKED_FILES[@]}"; do
        echo "   - ${file#"$SAFE_DIR"/}"
    done
    log_audit "ABORT: Leaked files detected: ${LEAKED_FILES[*]}"
    abort_with_error "機密ファイルの除外に失敗しました。処理を中断します。"
fi
echo "✅ 安全確認完了"
echo ""

# ──────────────────────────────────────────────
# プロンプトに指示を追加
# ──────────────────────────────────────────────
FULL_REQUEST="$REQUEST

確認や質問は不要です。具体的な提案・修正案・コード例まで自主的に出力してください。"

# ──────────────────────────────────────────────
# Codexを実行
# ──────────────────────────────────────────────
echo "🚀 Codexを実行中..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

"$CODEX_CMD" exec --full-auto --sandbox read-only --skip-git-repo-check --cd "$SAFE_DIR" "$FULL_REQUEST"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 完了"

log_audit "COMPLETED: Codex execution finished successfully"
