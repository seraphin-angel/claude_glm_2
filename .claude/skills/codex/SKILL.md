---
name: codex
description: |
  Codex CLI（OpenAI）を使用してコードや文言について相談・レビューを行う。
  トリガー: "codex", "codexと相談", "codexに聞いて"
  使用場面: (1) 文言・メッセージの検討、(2) コードレビュー、(3) 設計の相談、(4) バグ調査、(5) 解消困難な問題の調査
  注意: このスキルはプロジェクトのソースコードをOpenAIのサーバーに送信します。
---

# Codex

Codex CLIを使用してコードレビュー・分析を実行するスキル。

## ⚠️ セキュリティ警告

**このスキルはプロジェクト全体をOpenAIのサーバーに送信します。**

- 実行前に必ずユーザーに確認を求めます（`CODEX_SKIP_CONFIRM=1` で無効化可能）
- `safe-codex.sh` ラッパーにより機密ファイルを自動的に除外します
- シンボリックリンクは追跡しません（プロジェクト外のファイル漏洩を防止）
- `.gitignore` のルールも自動的に適用されます

### 自動除外されるファイル

以下のパターンは自動的に除外されます：

| カテゴリ | パターン |
|----------|----------|
| 環境変数 | `.env`, `.env.*`, `.env.local`, `.env.production`, `.env.staging` |
| 秘密鍵・証明書 | `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.crt` |
| 認証情報 | `credentials.*`, `secrets.*`, `*.secret`, `.htpasswd`, `.netrc`, `.npmrc`, `.pypirc`, `wp-config.php` |
| SSH鍵 | `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `id_dsa*`, `known_hosts`, `authorized_keys` |
| 暗号化 | `*.pgp`, `*.gpg`, `*.asc` |
| クラウド認証 | `service-account*.json`, `firebase-*.json`, `google-services.json`, `token.json`, `kubeconfig`, `terraform.tfstate` |
| データベース | `*.sqlite`, `*.sqlite3`, `*.db` |
| Spring Boot | `application-*.yml`, `application-*.yaml`, `application-*.properties` |
| Docker | `config.json` |

### 自動除外されるディレクトリ

`.secrets`, `secrets`, `.git`, `node_modules`, `.aws`, `.ssh`, `.docker`, `.kube`, `.gnupg`, `__pycache__`, `.terraform`, `vendor`, `dist`, `build`, `.next`

### 代替手段

機密情報を含むプロジェクトでは、Claude Code標準のエージェントを使用：

- **code-reviewer**: コードレビュー（外部送信なし）
- **security-reviewer**: セキュリティ監査（外部送信なし）

---

## 実行コマンド（推奨）

### safe-codex.sh を使用（デフォルト）

```bash
~/.claude/skills/codex/scripts/safe-codex.sh <project_directory> "<request>"
```

**特徴**:
- 機密ファイルを自動除外（rsyncベース、最初からコピーしない）
- シンボリックリンクを追跡しない
- `.gitignore` の除外ルールを自動適用
- 検出された機密ファイルを報告
- 送信前の最終セキュリティチェック
- ユーザー確認プロンプト
- プロジェクトサイズ制限（デフォルト500MB）
- 監査ログ対応
- 終了後に自動クリーンアップ

### 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `CODEX_SKIP_CONFIRM` | 未設定 | `1` に設定すると確認プロンプトをスキップ |
| `CODEX_MAX_SIZE_MB` | `500` | コピーするプロジェクトの最大サイズ（MB） |
| `CODEX_AUDIT_LOG` | 未設定 | 監査ログの出力先パス |

---

## プロンプトのルール

**重要**: codexに渡すリクエストには、以下の指示が自動的に追加されます：

> 「確認や質問は不要です。具体的な提案・修正案・コード例まで自主的に出力してください。」

---

## 使用例

### コードレビュー
```bash
~/.claude/skills/codex/scripts/safe-codex.sh /path/to/project "このプロジェクトのコードをレビューして、改善点を指摘してください。"
```

### バグ調査
```bash
~/.claude/skills/codex/scripts/safe-codex.sh /path/to/project "認証処理でエラーが発生する原因を調査してください。"
```

### アーキテクチャ分析
```bash
~/.claude/skills/codex/scripts/safe-codex.sh /path/to/project "このプロジェクトのアーキテクチャを分析して説明してください。"
```

### 監査ログ付きで実行
```bash
CODEX_AUDIT_LOG=~/codex-audit.log ~/.claude/skills/codex/scripts/safe-codex.sh /path/to/project "コードレビューしてください。"
```

---

## 実行手順

1. ユーザーから依頼内容を受け取る
2. 対象プロジェクトのディレクトリを特定する（現在のワーキングディレクトリまたはユーザー指定）
3. `safe-codex.sh` を実行
   - プロジェクトサイズを確認
   - 機密ファイルをスキャン・報告
   - ユーザーに送信確認を求める
   - rsync で除外パターンを適用しながらコピー
   - 最終セキュリティチェック
   - Codexを実行
   - クリーンアップ
4. 結果をユーザーに報告

---

## 除外パターンのカスタマイズ

`scripts/safe-codex.sh` の `EXCLUDE_PATTERNS` または `EXCLUDE_DIRS` 配列を編集して、除外するパターンを追加・削除できます：

```bash
EXCLUDE_PATTERNS=(
    ".env"
    ".env.*"
    # 追加のパターンをここに記述
    "*.mysecret"
)
```
