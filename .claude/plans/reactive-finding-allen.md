# P0 タスク実行計画 — Sequential-Leader パターン

## Context

`agentic-rag-chatbot` の P0（即時対応）タスク10件を、sequential-leader エージェントパターンで実行する。
品質チェックのバイパスバグ、メモリリーク、認証不在、プロンプトインジェクション脆弱性など、
セキュリティと安定性に関わる致命的な問題を修正する。

依存関係とファイル競合を考慮し、10タスクを **6バッチ** にグルーピングして逐次実行する。

## 実行アーキテクチャ

```
Leader (opus) — コードを書かない、オーケストレーションのみ
  ├─ Task 1: Worker (sonnet) → P0-01 → shutdown
  ├─ Task 2: Worker (sonnet) → P0-03 + P0-04 → shutdown
  ├─ Task 3: Worker (sonnet) → P0-05 → shutdown
  ├─ Task 4: Worker (sonnet) → P0-08 → shutdown
  ├─ Task 5: Worker (sonnet) → P0-06 + P0-07 + P0-09 → shutdown
  └─ Task 6: Worker (sonnet) → P0-02 + P0-10 → shutdown
```

## 実行順序と各タスクの詳細

---

### Task 1: P0-01 — quality.py フォールバック修正

**対象:** `backend/app/agents/tools/quality.py`
**変更内容:**
- L68-75: `except` ブロックの `passed=True` → `passed=False`
- `hallucination_score: 0.7` → `0.0`, `sufficiency_score: 0.7` → `0.0`
- `issues: []` → `["品質チェックのレスポンスが解析できませんでした"]`

**テスト:** `tests/test_tools.py` の `test_quality_json_parse_failure_default_values` のアサーションを修正
**実行:** `pytest tests/test_tools.py::TestCheckQuality -v`

---

### Task 2: P0-03 + P0-04 — エラー情報漏洩修正 + メモリリーク修正

**対象:** `backend/app/services/chat_service.py`, `backend/app/api/chat.py`

**P0-03 変更:**
- `_run_agent` L91-100, `_resume_agent` L153-162: `f"エラーが発生しました: {error_str}"` → 汎用メッセージに置換
- `import logging` 追加、`logger.error("Agent execution error", exc_info=True)` でサーバーログに記録
- 環境変数 `DEBUG_MODE` で開発時はスタックトレース表示を切り替え

**P0-04 変更:**
- `__init__`: `MAX_CONCURRENT_THREADS = 1000`, `QUEUE_MAXSIZE = 100` 定数追加
- `get_or_create_queue()`: `Queue(maxsize=QUEUE_MAXSIZE)` + LRU eviction ロジック
- `api/chat.py` L47-48: `finally: pass` → `finally: service.cleanup(thread_id)`

**テスト:** エラーレスポンスに内部情報が含まれないことを検証、Queue eviction テスト、cleanup 呼び出し検証
**実行:** `pytest tests/test_api.py -v`

---

### Task 3: P0-05 — thread_id UUID バリデーション

**対象:** `backend/app/models/chat.py`, `backend/app/api/chat.py`

**変更内容:**
- `ChatRequest.thread_id`: `str | None` → `UUID | None`
- `stream_chat(thread_id: str)` → `stream_chat(thread_id: UUID)` + 404 チェック
- `resume_chat` も同様に UUID 型に変更
- 内部では `str(thread_id)` で文字列に変換して使用

**テスト:** 不正形式 → 422、存在しないスレッド → 404、正常 UUID → 200 を検証
**実行:** `pytest tests/test_api.py -v && pytest tests/test_models.py -v`

---

### Task 4: P0-08 — エージェント反復回数制限

**対象:** `backend/app/services/chat_service.py`, `backend/app/agents/prompts.py`

**変更内容:**
- `_run_agent`: `MAX_STEPS = 10` のステップカウンター追加、`on_tool_end` でカウント
- 上限到達時に ERROR イベント送出 + break
- `_resume_agent` にも同様のカウンター追加
- `prompts.py`: ワークフロー欄に「`check_quality` 不合格時のリトライは最大2回。3回目以降は `ask_human` でエスカレーション」を追記

**テスト:** MAX_STEPS 超過時のエラー送出を検証
**実行:** `pytest tests/test_api.py -v`

---

### Task 5: P0-06 + P0-07 + P0-09 — LLM シングルトン + StructuredOutput + インジェクション対策

**対象:** 全5ツールファイル + `agents/agent.py`
**新規作成:**
- `backend/app/agents/llm_factory.py` — `@lru_cache` LLM ファクトリ (`get_llm(temperature)`)
- `backend/app/agents/output_models.py` — `ClassifyOutput`, `RelevanceOutput`, `QualityOutput` Pydantic モデル

**変更内容:**
- 全ツール: `ChatOpenAI()` 直接生成 → `get_llm()` に置換
- `classify.py`, `relevance.py`, `quality.py`: 手動 JSON パース → `llm.with_structured_output(Model)` + Pydantic モデル
- 全ツール: f-string プロンプト → `ChatPromptTemplate.from_messages()` に移行（ユーザー入力は `HumanMessage` に隔離）
- `agents/agent.py` L29-34: `ChatOpenAI()` → `get_llm(temperature=0.1)`
- `quality.py` のフォールバック: Task 1 の修正を維持（`passed=False`, スコア `0.0`）

**テスト:**
- 新規 `tests/test_llm_factory.py`: 同一インスタンス返却を検証
- 新規 `tests/test_output_models.py`: Pydantic バリデーション検証
- `tests/test_tools.py`: モック対象を `ChatOpenAI` → `get_llm` に変更

**実行:** `pytest tests/ -v`

---

### Task 6: P0-02 + P0-10 — レート制限 + JWT 認証

**対象:** `backend/app/main.py`, `backend/app/api/chat.py`, `backend/app/config/settings.py`, `backend/pyproject.toml`
**新規作成:**
- `backend/app/auth/__init__.py`
- `backend/app/auth/jwt_handler.py` — `create_access_token()`, `verify_token()` (HTTPBearer + python-jose)

**変更内容:**
- `pyproject.toml`: `slowapi>=0.1.9`, `python-jose[cryptography]>=3.3.0` 追加
- `settings.py`: `jwt_secret_key`, `jwt_algorithm`, `rate_limit_chat`, `rate_limit_stream`, `debug_mode` 追加
- `main.py`: `slowapi.Limiter` 設定 + `RateLimitExceeded` ハンドラー登録
- `api/chat.py`: 全エンドポイントに `@limiter.limit()` + `Depends(verify_token)` 追加
- `api/health.py`: ヘルスチェックは認証不要のまま維持

**テスト:**
- 新規 `tests/test_auth.py`: JWT 生成・検証・期限切れ・不正トークンを検証
- `tests/test_api.py`: 全テストに `Authorization: Bearer <token>` ヘッダー追加、認証なし → 401/403 検証、429 検証

**実行:** `pytest tests/ -v`

---

## 依存関係とアーティファクト引き継ぎ

| Task | 前提 | 次タスクへの引き継ぎ |
|------|------|---------------------|
| 1 | なし | `quality.py` フォールバック修正済み |
| 2 | Task 1 完了 | `chat_service.py` にロガー追加、cleanup 自動呼び出し、Queue サイズ制限 |
| 3 | Task 2 完了 | `chat.py` の `thread_id` が UUID 型に変更済み |
| 4 | Task 3 完了 | `chat_service.py` にステップカウンター追加、`prompts.py` にリトライ制限 |
| 5 | Task 4 完了 | 全ツール書き換え済み、`llm_factory.py` と `output_models.py` 新規作成 |
| 6 | Task 5 完了 | 認証・レート制限追加、全テストに auth ヘッダー追加 |

## 検証方法

各タスク完了後にサブエージェントが `pytest` を実行。
全タスク完了後、リーダーが最終検証:

```bash
cd /workspace/agentic-rag-chatbot/backend
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

## 新規依存パッケージ

- `slowapi>=0.1.9` (Task 6)
- `python-jose[cryptography]>=3.3.0` (Task 6)
