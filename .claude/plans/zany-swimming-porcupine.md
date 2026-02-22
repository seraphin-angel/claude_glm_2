# Codex スキル セキュリティレビュー結果

## Context

ユーザーがインストール済みの `codex` スキル（`.claude/skills/codex/`）のセキュリティレビューを依頼。このスキルはOpenAIのCodex CLIを呼び出し、**プロジェクトのソースコードを外部（OpenAIサーバー）に送信する**という性質上、特に慎重なセキュリティ検証が必要。

### 対象ファイル
- `.claude/skills/codex/SKILL.md` — スキル定義・ドキュメント
- `.claude/skills/codex/scripts/safe-codex.sh` — 機密ファイル除外ラッパースクリプト

---

## CRITICAL（重大）

### 1. Copy-then-Delete アンチパターン（データ漏洩リスク）

**該当箇所**: `safe-codex.sh:136-147`

```bash
# まず全体をコピー ← 機密ファイルを含めて全コピー
cp -r "$PROJECT_DIR"/* "$SAFE_DIR/" 2>/dev/null || true
cp -r "$PROJECT_DIR"/.* "$SAFE_DIR/" 2>/dev/null || true

# 除外ファイルを削除 ← 後から削除を試みる
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    find "$SAFE_DIR" -name "$pattern" -type f -delete 2>/dev/null || true
done
```

**問題**: 全ファイル（機密ファイル含む）を一時ディレクトリにコピーした**後に**削除するパターン。

- `|| true` で削除エラーが無視されるため、削除に失敗しても処理が続行し、機密ファイルがOpenAIに送信される
- `set -e` は `|| true` が付いた行では機能しない
- スクリプトがコピー後・削除前にクラッシュした場合、一時ディレクトリに機密ファイルが残る

**修正**: 「安全なファイルのみコピー」パターン（allowlist方式）に変更すべき。`find` + `rsync --exclude` 等を使って、最初から除外対象をコピーしない。

---

### 2. シンボリックリンク追跡による情報漏洩

**該当箇所**: `safe-codex.sh:136-137`

```bash
cp -r "$PROJECT_DIR"/* "$SAFE_DIR/" 2>/dev/null || true
```

**問題**: `cp -r` はデフォルトでシンボリックリンクを**追跡（follow）**する。プロジェクト内に以下のようなシンボリックリンクがあった場合：

```
project/config -> /etc/shadow
project/keys -> ~/.ssh/
project/data -> /var/lib/postgresql/data
```

**プロジェクト外の機密ファイルが一時ディレクトリにコピーされ、OpenAIに送信される。** 除外パターンはファイル名ベースなので、リンク先のファイル名が除外リストに一致しない限り検出されない。

**修正**: `cp -r --no-dereference` を使用するか、`rsync` でシンボリックリンクを無視すべき。

---

### 3. `CODEX_CMD` 環境変数経由のバイナリ置換

**該当箇所**: `safe-codex.sh:20`

```bash
CODEX_CMD="${CODEX_CMD:-/usr/local/share/npm-global/bin/codex}"
```

**問題**: `CODEX_CMD` 環境変数を設定することで、任意のバイナリを codex の代わりに実行可能。

- CI/CD環境でこの変数が汚染された場合、プロジェクト全体のコピーが攻撃者の制御するプログラムに渡される
- `.env` ファイルや `.bashrc` 等で気づかずに上書きされる可能性

**修正**: パスの検証（署名チェック、固定パスの使用）や、最低限 `which codex` の結果を表示して確認を求めるべき。

---

### 4. `--full-auto` モードのリスク

**該当箇所**: `safe-codex.sh:163`

```bash
"$CODEX_CMD" exec --full-auto --sandbox read-only --cd "$SAFE_DIR" "$FULL_REQUEST"
```

**問題**: `--full-auto` はCodexが**ユーザー確認なしに自動で操作を実行**するモード。`--sandbox read-only` でファイル書き込みは制限されるが、ネットワークアクセスやプロセス実行は可能。Codex側の脆弱性やプロンプトインジェクションにより、意図しない操作が行われる可能性がある。

---

## HIGH（高）

### 5. 除外パターンの不足

現在の除外リストでカバーされていない一般的な機密ファイル：

| 未対応パターン | リスク |
|---|---|
| `.npmrc` | npm認証トークン |
| `.pypirc` | PyPI認証情報 |
| `*.jks`, `*.keystore` | Java キーストア |
| `.docker/config.json` | Dockerレジストリ認証 |
| `kubeconfig`, `.kube/config` | Kubernetes認証情報 |
| `terraform.tfstate` | Terraformステート（しばしばシークレットを含む） |
| `.aws/credentials`, `.aws/config` | AWSアクセスキー |
| `*.sqlite`, `*.db` | データベースファイル |
| `token.json`, `*_token.json` | OAuthトークン |
| `.htpasswd` | HTTP Basic認証 |
| `.netrc` | ネットワーク認証情報 |
| `wp-config.php` | WordPress DB認証情報 |
| `*.crt`（秘密鍵とセットの場合） | 証明書 |
| `application-*.yml`（Spring Boot） | DB接続情報等 |

### 6. ファイル内容ベースのスキャンが未実装

スクリプトは**ファイル名のみ**でフィルタリングしている。以下のようなケースは検出できない：

```javascript
// config.js - ファイル名は除外パターンに一致しない
const API_KEY = "sk-proj-xxxxxxxxxxxxx"
const DB_PASSWORD = "super_secret_password"
```

`trufflehog`、`gitleaks`、または単純な正規表現ベースのシークレットスキャンを追加すべき。

### 7. `.gitignore` の活用がない

多くのプロジェクトでは `.gitignore` に機密ファイルが既にリストされている。`rsync --filter=':- .gitignore'` や `git ls-files` を使えば、プロジェクト固有の除外設定も反映できる。

---

## MEDIUM（中）

### 8. エラー抑制パターン `|| true` の過剰使用

`safe-codex.sh` の複数箇所で `|| true` が使われており、以下のエラーが**すべて無視**される：
- 機密ファイルの削除失敗（パーミッション不足等）
- コピーの部分的失敗
- findコマンドのエラー

特に削除処理（行140-147）の `|| true` は、機密ファイルが残っても検出できないため危険。

### 9. ファイルサイズ・数量の制限がない

巨大なプロジェクト（数GBのモノレポ等）がそのままコピーされる。データベースダンプ、ビルド成果物、ログファイル等が含まれる可能性。

### 10. スキルトリガーの誤発動リスク

SKILL.md のトリガーに「コードレビュー」「レビューして」が含まれている。ユーザーが単にClaude Codeのローカルレビュー機能を使いたい場合にも、このスキルが誤って起動し、**意図せずプロジェクトがOpenAIに送信される**可能性がある。

---

## LOW（低）

### 11. 監査ログが存在しない

どのファイルがOpenAIに送信されたかの記録が残らない。事後的なセキュリティ監査が不可能。

### 12. 一時ディレクトリのパス漏洩

`SAFE_DIR` のフルパスがstdoutに出力される。CI/CDログに残った場合、ディレクトリ構造の情報漏洩につながる。

---

## 総合評価

| カテゴリ | 件数 |
|---|---|
| CRITICAL | 4件 |
| HIGH | 3件 |
| MEDIUM | 3件 |
| LOW | 2件 |

**結論: このスキルを本番環境のプロジェクトで使用することは推奨しません。**

特にCRITICALの問題 #1（copy-then-delete）と #2（シンボリックリンク追跡）は、意図せず機密情報がOpenAIに送信されるリスクが高く、スキルの目的である「安全な実行」を達成できていません。

---

## 推奨アクション

### 即座に実施すべき対応

1. **copy-then-deleteを排除** — `rsync --exclude` または `find` + `cpio` で「最初から除外してコピー」に変更
2. **シンボリックリンク対策** — `cp -r --no-dereference` または `rsync -a --no-links`
3. **`|| true` の削除**（少なくとも削除処理部分） — 削除失敗時は処理を中断すべき
4. **除外パターンの大幅追加** — 上記HIGH #5のリスト参照
5. **トリガーワードの変更** — 「コードレビュー」「レビューして」を除外し、明示的な「codex」のみに限定

### 中期的な改善

6. `.gitignore` との統合
7. ファイル内容ベースのシークレットスキャン追加
8. ファイルサイズ制限の導入
9. 送信前のユーザー確認プロンプト追加
10. 監査ログの記録

### 代替策の検討

SKILL.md にも記載されている通り、機密情報を含むプロジェクトでは **`code-reviewer`** や **`security-reviewer`** エージェントの使用を推奨。これらはローカルで動作し、データを外部に送信しない。
