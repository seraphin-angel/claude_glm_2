# README.md / spec.md P3完了反映 更新計画

## Context

IMPROVEMENT_IDEAS.md に記載された56件の改善項目がほぼ全件（P0〜P3）実装完了したが、README.md と spec.md は **P2完了時点**（v0.3.0, 2026-02-25）で止まっている。P3で実装された9つの機能群をドキュメントに反映する必要がある。

### P3 で実装された機能群
1. マルチテナント対応（P3-48）
2. GDPR/データ保持ポリシー（P3-49）
3. CRM/チケットシステム連携 — Zendesk（P3-50）
4. 画像添付 — Vision API（P3-51）
5. 多言語対応 — i18n（P3-52）
6. マルチチャネル — LINE/Slack/Email（P3-53）
7. パーソナライゼーション（P3-54）
8. A/Bテスト基盤（P3-55）
9. ガードレール/ジェイルブレイク対策（P3-56）
10. セキュリティ課題15件修正 + テストカバレッジギャップ解消

---

## 複雑度スコア: 5（Tier 4: 階層委譲）

- 2ファイル修正（README.md + spec.md） +1
- >5ファイル読み必要（実装確認） +1
- コード編集あり +1
- spec.md が1763行の大規模ファイル +1
- 多セクション・多フェーズ更新 +1

→ **Tier 3（フルチーム委譲）** で実施。Director不要（ドキュメント更新のみで実装コードの変更は軽微）。

---

## タスク分解

### Task 1: 実装状態の精密確認（Explore エージェント）

P3追加のAPIルーター登録、ミドルウェア構成、ツールリスト、設定項目を確認:
- `backend/app/main.py` — P3ルーター登録・ミドルウェア構成
- `backend/app/api/__init__.py` — 全APIルーターのエクスポート
- `backend/app/agents/agent.py` — ツールリスト（8つ or それ以上か）
- `backend/app/agents/tools/__init__.py` — エクスポートされているツール
- `backend/app/config/settings.py` — P3環境変数の有無・app_version
- `frontend/src/i18n/` — i18n構成
- `frontend/src/components/LanguageSwitcher.tsx` — 配置確認
- `frontend/package.json` — P3追加依存
- テスト数の確認: `pytest --co -q | tail -1`

### Task 2: README.md の更新（Worker エージェント）

Task 1 の結果を踏まえて更新:

**更新箇所:**
1. **冒頭**: バージョン情報の追加（v0.4.0, P3完了）
2. **機能セクション**（行7-14）: P3機能9項目を追加
3. **アーキテクチャ**（行16-27）: ツール数更新、追加技術スタック
4. **環境変数テーブル**（行62-81）: P3追加分があれば追記
5. **APIエンドポイントテーブル**（行83-98）: P3 API（GDPR, テナント, チャネル, 実験, ガードレール, ユーザー, インテグレーション, 画像）を追加
6. **テスト**（行100-105）: テスト数の更新

ファイル: `/workspace/agentic-rag-chatbot/README.md`

### Task 3: spec.md の更新（Worker エージェント）

Task 1 の結果を踏まえて更新:

**更新箇所:**
1. **ヘッダー**（行3-5）: バージョン 0.4.0、最終更新日 2026-02-28 (P3完了反映)
2. **セクション1 概要 — 主要機能テーブル**（行33-46）: P3機能9項目追加
3. **セクション1 概要 — 技術スタック**（行48-87）: P3追加ライブラリ（i18next, react-dropzone等）
4. **セクション2 — ディレクトリ構成**（行178-317）: P3追加ファイル/ディレクトリ
5. **セクション3.1 — APIエンドポイント一覧**（行326-354）: P3全APIエンドポイント
6. **セクション3.3 — ツール関連**（行796-808）: content_safety, image_analysis ツールの記載
7. **セクション6 — Settings/環境変数**（行1527-1599）: app_version更新、P3設定項目
8. **セクション7 — テスト戦略**（行1622-1674）: P3テストファイル追加、テスト数更新
9. **セクション9 — 制限事項**（行1710-1763）: 「P3で完了した項目」セクション追加、拡張ポイント更新

**追加セクション（セクション9の前に挿入）:**
- ミドルウェア仕様（TenantMiddleware, UserContextMiddleware, GuardrailsMiddleware）
- チャネルアダプター仕様（LINE/Slack/Email）
- インテグレーション仕様（Zendesk）
- ガードレール仕様（入出力安全性チェック、PII検出）
- 実験/A/Bテスト仕様
- GDPR/データ保持仕様
- 多言語対応（i18n）仕様

ファイル: `/workspace/agentic-rag-chatbot/spec.md`

### Task 4: settings.py の app_version 更新（Worker エージェント）

`app_version: str = "0.1.0"` → `"0.4.0"` に更新。

ファイル: `/workspace/agentic-rag-chatbot/backend/app/config/settings.py`

### Task 5: レビュー（Reviewer エージェント）

- README.md: 機能一覧の網羅性、APIエンドポイントの正確性
- spec.md: ディレクトリ構成の実態との一致、セクション間の整合性
- テスト実行: `cd backend && uv run pytest tests/ --co -q | tail -5`

---

## 依存関係

```
Task 1 → Task 2（並行可能）
Task 1 → Task 3（並行可能）
Task 1 → Task 4
Task 2, 3, 4 → Task 5
```

---

## 検証方法

1. `git diff` で変更箇所を確認
2. README.md の APIエンドポイント数が実際のルーター登録数と一致するか
3. spec.md のディレクトリ構成が `find` 結果と一致するか
4. `cd backend && uv run python -c "from app.config.settings import get_settings; print(get_settings().app_version)"` → `"0.4.0"` を確認
5. テスト数が spec.md の記載と一致するか
