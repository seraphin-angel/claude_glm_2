# P0 - 即時対応（10件）

> 基盤の安全性確保。セキュリティ脆弱性と致命的バグの修正。
> 目標期間: 即時〜1ヶ月

## 進捗サマリー

| 完了 | 進行中 | 未着手 | ブロック | 進捗率 |
|------|--------|--------|----------|--------|
| 10 | 0 | 0 | 0 | 100% |

---

## タスク一覧

### 1. `quality.py` フォールバック修正（`passed=False`）

| 項目 | 内容 |
|------|------|
| ID | P0-01 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/agents/tools/quality.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 1) |
| 関連PR | - |

**概要:** `check_quality` ツールの JSON パースエラー時に `passed=True`（合格）をデフォルト返却しており、品質チェックが実質的にバイパスされる。`passed=False` に変更する。

**受け入れ条件:**
- [x] `except (json.JSONDecodeError, IndexError)` ブロックで `passed=False` を返すように修正
- [x] `hallucination_score` を安全方向のデフォルト値に変更
- [x] ユニットテストでエラー時のフォールバック動作を検証

**備考:**
```
- except ブロックのフォールバック値を修正: passed=True→False, scores 0.7→0.0
- issues に "品質チェックのレスポンスが解析できませんでした" を追加
- tests/test_tools.py の TestCheckQuality アサーションを更新（6テスト全パス）
- Task 5 で StructuredOutput 導入時にも同じフォールバック方針を維持
```

---

### 2. レート制限の実装

| 項目 | 内容 |
|------|------|
| ID | P0-02 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/api/chat.py`, `backend/app/main.py`, `backend/app/rate_limit.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 6) |
| 関連PR | - |

**概要:** API エンドポイントにレート制限がなく、大量リクエストによる DoS 攻撃や OpenAI API コスト爆発のリスクがある。`slowapi` によるレート制限を実装する。

**受け入れ条件:**
- [x] `slowapi` をインストールし、Limiter を設定
- [x] チャット開始エンドポイントに `10/minute` のレート制限を設定
- [x] SSE ストリームエンドポイントにもレート制限を設定
- [x] レート制限超過時に適切な 429 レスポンスを返す
- [x] テストでレート制限動作を検証

**備考:**
```
- slowapi>=0.1.9 を pyproject.toml に追加
- 循環インポート回避のため backend/app/rate_limit.py を独立モジュールとして作成
- main.py に RateLimitExceeded ハンドラー登録（429 レスポンス）
- settings.py に rate_limit_chat / rate_limit_stream 設定を追加
- chat.py の全エンドポイントに @limiter.limit() デコレーターを適用
```

---

### 3. エラーメッセージの内部情報除去

| 項目 | 内容 |
|------|------|
| ID | P0-03 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/services/chat_service.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 2) |
| 関連PR | - |

**概要:** 例外のスタックトレースをそのまま SSE でユーザーに送信しており、API キー情報、ファイルパス、内部構造が漏洩するリスクがある。

**受け入れ条件:**
- [x] エラー詳細をサーバーログに記録（`logger.error` + `exc_info=True`）
- [x] ユーザー向けには汎用的なエラーメッセージのみ返す
- [x] 環境変数でデバッグモード切り替え可能にする（開発時はスタックトレース表示）
- [x] テストでエラー時のレスポンスに内部情報が含まれないことを検証

**備考:**
```
- _run_agent / _resume_agent の except ブロックで汎用メッセージに置換
- logger.error("Agent execution error", exc_info=True) でサーバーログに詳細記録
- settings.py に debug_mode 設定追加、DEBUG_MODE=true 時のみスタックトレース表示
- test_api.py にエラーレスポンスの内部情報非含有テスト追加
```

---

### 4. SSE キューのメモリリーク修正

| 項目 | 内容 |
|------|------|
| ID | P0-04 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/services/chat_service.py`, `backend/app/api/chat.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 2) |
| 関連PR | - |

**概要:** `ChatService._queues` と `_tasks` にサイズ制限がなく、`cleanup()` が API から呼ばれない。SSE 切断後もキューが残留し続け、メモリ枯渇のリスクがある。

**受け入れ条件:**
- [x] `_queues` の最大同時接続数を制限（例: 1000）
- [x] `Queue` の `maxsize` を設定（例: 100）
- [x] SSE 終了時に `finally` ブロックで `cleanup()` を確実に呼び出す
- [x] 古いキューの自動退去（eviction）メカニズムを実装
- [x] テストでクリーンアップ動作を検証

**備考:**
```
- MAX_CONCURRENT_THREADS=1000, QUEUE_MAXSIZE=100 をクラス定数として追加
- get_or_create_queue() に LRU eviction ロジック実装（dict 挿入順 + next(iter())）
- api/chat.py の stream_chat finally ブロックで service.cleanup(tid) を呼び出し
- test_api.py に Queue eviction テスト・cleanup 呼び出し検証テスト追加
```

---

### 5. thread_id UUID バリデーション

| 項目 | 内容 |
|------|------|
| ID | P0-05 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/models/chat.py`, `backend/app/api/chat.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 3) |
| 関連PR | - |

**概要:** `thread_id` にフォーマットバリデーションがなく、任意文字列が通過する。UUID 形式を強制する。

**受け入れ条件:**
- [x] `thread_id` パラメータに `UUID4` 型バリデーションを追加
- [x] 存在しない `thread_id` に対して 404 を返す
- [x] 不正形式の `thread_id` に対して 422 を返す
- [x] テストで各バリデーションケースを検証

**備考:**
```
- ChatRequest.thread_id を str | None → UUID | None に変更
- stream_chat / resume_chat のパスパラメータを UUID 型に変更
- 内部では str(thread_id) で文字列変換して使用
- TEST_THREAD_UUID 定数をテストファイルに追加
- 不正形式→422、正常UUID→200 の検証テスト追加
```

---

### 6. LLM インスタンスのシングルトン化

| 項目 | 内容 |
|------|------|
| ID | P0-06 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/agents/llm_factory.py`（新規）, `backend/app/agents/tools/` 各ツール, `backend/app/agents/agent.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 5) |
| 関連PR | - |

**概要:** 各ツール（`classify.py`, `rewrite.py`, `relevance.py`, `generate.py`, `quality.py`）が毎回 `ChatOpenAI` インスタンスを生成している。共通のファクトリ関数でシングルトン化する。

**受け入れ条件:**
- [x] `@lru_cache` を使用した LLM ファクトリ関数を作成（temperature 別に2種類）
- [x] 全ツールファイルを共通ファクトリ関数に移行
- [x] テストで同一インスタンスが返されることを検証

**備考:**
```
- backend/app/agents/llm_factory.py を新規作成
- @lru_cache(maxsize=8) で get_llm(temperature, streaming) を実装
- 全5ツール + agent.py の ChatOpenAI() 直接生成を get_llm() に置換
- tests/test_llm_factory.py で同一インスタンス返却を検証（3テスト）
```

---

### 7. StructuredOutput 導入

| 項目 | 内容 |
|------|------|
| ID | P0-07 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/agents/output_models.py`（新規）, `backend/app/agents/tools/classify.py`, `relevance.py`, `quality.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 5) |
| 関連PR | - |

**概要:** 全ツールが LLM レスポンスを手動で JSON パースしている。`with_structured_output()` と Pydantic モデルを導入して型安全性を向上させる。

**受け入れ条件:**
- [x] 各ツールの出力を Pydantic モデルとして定義
- [x] `llm.with_structured_output(Model)` に移行
- [x] 手動 JSON パース処理を削除
- [x] フォールバック処理を型安全なデフォルト値に変更
- [x] テストで型安全な出力を検証

**依存:** P0-06（LLM シングルトン化）と合わせて実装 → 同時実施完了

**備考:**
```
- backend/app/agents/output_models.py を新規作成
  - ClassifyOutput(category, confidence, reason)
  - RelevanceOutput(is_relevant, score, relevant_doc_indices, reason)
  - QualityOutput(hallucination_score, sufficiency_score, issues, suggestions)
- classify.py, relevance.py, quality.py で with_structured_output(Model) に移行
- generate.py, rewrite.py は文字列出力のため StructuredOutput 不要（ChatPromptTemplate のみ適用）
- tests/test_output_models.py で Pydantic バリデーション検証（7テスト）
```

---

### 8. エージェント反復回数制限

| 項目 | 内容 |
|------|------|
| ID | P0-08 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/services/chat_service.py`, `backend/app/agents/prompts.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 4) |
| 関連PR | - |

**概要:** `create_react_agent` に反復回数制限がなく、品質チェック失敗のループで無限に LLM を呼び出す可能性がある。

**受け入れ条件:**
- [x] `astream_events` ラッパーでステップ数を監視（MAX_STEPS=10）
- [x] プロンプトに `check_quality` 不合格時の最大リトライ回数（2回）を明記
- [x] 3回目以降は `ask_human` でエスカレーション指示をプロンプトに追加
- [x] テストで反復制限超過時の動作を検証

**備考:**
```
- chat_service.py に MAX_STEPS=10 クラス定数追加
- _run_agent / _resume_agent に step_count カウンター実装（on_tool_end でインクリメント）
- MAX_STEPS 到達時に ERROR イベント送出 + break
- prompts.py に「check_quality 不合格時のリトライは最大2回、3回目以降は ask_human」ルール追記
- test_api.py に MAX_STEPS 超過テスト追加
```

---

### 9. プロンプトインジェクション対策

| 項目 | 内容 |
|------|------|
| ID | P0-09 |
| カテゴリ | セキュリティ |
| 難易度 | 中 |
| 対象ファイル | `backend/app/agents/tools/` 全ツール |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 5) |
| 関連PR | - |

**概要:** 全ツールがユーザー入力を f-string でプロンプトに直接展開しており、プロンプトインジェクション攻撃に脆弱。

**受け入れ条件:**
- [x] ユーザー入力を `HumanMessage` として構造化メッセージで渡すように変更
- [x] 基本的なインジェクションパターン検出関数を実装
- [x] 検出時にログ記録 + 安全な応答を返す
- [x] テストで代表的なインジェクションパターンをテスト

**備考:**
```
- 全5ツールを ChatPromptTemplate.from_messages() に移行
- システムプロンプトは SystemMessage、ユーザー入力は HumanMessage に分離
- f-string による直接展開を完全に排除
- StructuredOutput 導入（P0-07）と同時実施し、出力パースも型安全に
- テストでモックパターンを ChatPromptTemplate | llm チェーンに対応するよう更新
```

---

### 10. JWT 認証の実装

| 項目 | 内容 |
|------|------|
| ID | P0-10 |
| カテゴリ | セキュリティ |
| 難易度 | 中 |
| 対象ファイル | `backend/app/auth/__init__.py`（新規）, `backend/app/auth/jwt_handler.py`（新規）, `backend/app/api/chat.py`, `backend/app/config/settings.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | Claude Agent (Task 6) |
| 関連PR | - |

**概要:** 全 API エンドポイントに認証が一切なく、誰でもチャットを利用でき、OpenAI API コストを無制限に消費させることが可能。JWT ベースの認証を実装する。

**受け入れ条件:**
- [x] `HTTPBearer` + JWT トークン検証ミドルウェアを実装
- [x] 全エンドポイントに認証を適用（`Depends(verify_token)`）
- [x] SSE エンドポイントにもトークンベースの認証を適用
- [x] トークン発行 / 検証のユーティリティ関数を作成
- [x] 認証エラー時に適切な 401/403 レスポンスを返す
- [x] テストで認証あり/なしの動作を検証

**依存:** P0-02（レート制限）と組み合わせて実装 → 同時実施完了

**備考:**
```
- python-jose[cryptography]>=3.3.0 を pyproject.toml に追加
- backend/app/auth/ ディレクトリを新規作成
  - jwt_handler.py: create_access_token() / verify_token() (HTTPBearer + python-jose)
  - __init__.py: 公開関数をエクスポート
- settings.py に jwt_secret_key, jwt_algorithm, jwt_expire_minutes を追加
- chat.py の全エンドポイントに Depends(verify_token) を適用
- health.py は認証不要のまま維持
- conftest.py に auth_headers フィクスチャ追加、全テストに認証ヘッダー適用
- tests/test_auth.py を新規作成（JWT 生成・検証・期限切れ・不正トークン: 6テスト）
```

---

## 依存関係マップ

```
P0-06 (LLMシングルトン) ──→ P0-07 (StructuredOutput) ※合わせて実施 → ✅ 完了
P0-02 (レート制限)     ──→ P0-10 (JWT認証)          ※組み合わせ推奨 → ✅ 完了
P0-01 (品質フォールバック) → P0-07 (StructuredOutput) ※P0-07で根本解決 → ✅ 完了
```

## 最終検証結果

```
pytest tests/ -v --tb=short → 187 passed, 0 failed, 1 warning (8.77s)
```

実行日: 2026-02-23
