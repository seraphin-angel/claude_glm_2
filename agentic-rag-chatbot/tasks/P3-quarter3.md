# P3 - 第3四半期以降（9件）

> プラットフォーム化。スケーラブルな SaaS 基盤と高度な機能拡張。
> 目標期間: 6〜12ヶ月

## 進捗サマリー

| 完了 | 進行中 | 未着手 | ブロック | 進捗率 |
|------|--------|--------|----------|--------|
| 8 | 0 | 1 | 0 | 89% |

---

## エンタープライズ対応（3件）

### 48. マルチテナント対応

| 項目 | 内容 |
|------|------|
| ID | P3-48 |
| カテゴリ | エンタープライズ |
| 難易度 | 高 |
| 対象ファイル | 全体アーキテクチャ, ChromaDB, 認証 |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** テナントごとの ChromaDB コレクション分離、API リクエストからのテナント ID 取得。

**受け入れ条件:**
- [x] テナント識別子の設計（サブドメイン / ヘッダー / パス）→ X-Tenant-ID ヘッダー方式
- [x] ChromaDB コレクションのテナント分離 → `{tenant_id}_{collection_name}` 形式
- [x] テナントごとの設定管理（LLMモデル、プロンプト等）→ TenantConfig モデル
- [x] テナント間のデータ隔離検証 → ContextVar + ミドルウェアで分離
- [x] テナント管理 API の実装 → `/api/tenants` CRUD エンドポイント

**依存:** P0-10（JWT認証）, P2-40（PostgresSaver）

**備考:**
```
テスト: 30件（全パス）
実装ファイル:
- backend/app/models/tenant.py（Tenant, TenantConfig モデル、frozen=True）
- backend/app/middleware/tenant.py（TenantMiddleware、ContextVar）
- backend/app/services/tenant_service.py（テナント CRUD）
- backend/app/api/tenant.py（/api/tenants エンドポイント）
- backend/tests/test_tenant.py
```

---

### 49. データ保持ポリシー（GDPR）

| 項目 | 内容 |
|------|------|
| ID | P3-49 |
| カテゴリ | エンタープライズ |
| 難易度 | 中 |
| 対象ファイル | データベース層, 新規: データ管理モジュール |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** テナントごとのデータ保持期間設定、GDPR「忘れられる権利」対応、自動削除ジョブ。

**受け入れ条件:**
- [x] データ保持期間の設定（30日/90日/365日）→ RetentionPolicy モデル
- [x] 期限切れデータの自動削除ジョブ → run_cleanup_job()
- [x] ユーザーデータ削除 API（「忘れられる権利」）→ DELETE /api/gdpr/data（Article 17）
- [x] 削除ログの監査証跡 → AuditLogEntry モデル + GET /api/gdpr/audit-logs

**依存:** P2-40（PostgresSaver）, P3-48（マルチテナント）

**備考:**
```
テスト: 22件（全パス）
実装ファイル:
- backend/app/models/retention.py（RetentionPolicy, DataDeletionRequest, AuditLogEntry）
- backend/app/services/retention_service.py（ポリシー管理、ユーザーデータ削除、監査ログ、クリーンアップジョブ）
- backend/app/api/gdpr.py（/api/gdpr エンドポイント）
- backend/tests/test_retention.py
```

---

### 50. CRM/チケットシステム連携

| 項目 | 内容 |
|------|------|
| ID | P3-50 |
| カテゴリ | エンタープライズ |
| 難易度 | 高 |
| 対象ファイル | 新規: 連携アダプターモジュール |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** Salesforce / Zendesk / Freshdesk 等の外部チケットシステムとの連携。

**受け入れ条件:**
- [x] チケットシステム連携のアダプターインターフェース設計 → BaseTicketAdapter 抽象基底クラス
- [x] 最低1つの外部システムとの統合（例: Zendesk）→ ZendeskAdapter 実装
- [x] エスカレーション時の自動チケット作成 → on_escalation() フック
- [x] チケットステータスの双方向同期 → update_ticket() / close_ticket()

**依存:** P2-45（エスカレーションツール）

**備考:**
```
テスト: 27件（全パス）
実装ファイル:
- backend/app/integrations/base.py（BaseTicketAdapter、TicketData、TicketPriority、TicketStatus）
- backend/app/integrations/mock_adapter.py（テスト・開発用モックアダプター）
- backend/app/integrations/zendesk.py（Zendesk Support API アダプター）
- backend/app/services/integration_service.py（アダプター管理、エスカレーション時自動チケット作成）
- backend/app/api/integrations.py（/api/integrations エンドポイント）
- backend/tests/test_crm_integration.py
```

---

## 製品戦略（5件）

### 51. 画像添付（Vision API）

| 項目 | 内容 |
|------|------|
| ID | P3-51 |
| カテゴリ | 製品戦略 |
| 難易度 | 中 |
| 対象ファイル | `frontend/src/components/ChatInput.tsx`, `backend/app/tools/` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** スクリーンショット添付によるエラー画面の自動解析。GPT-4o Vision API を活用。

**受け入れ条件:**
- [x] フロントエンドに画像添付 UI（ドラッグ&ドロップ + ボタン）
- [x] 画像のアップロード API
- [x] `analyze_image` ツールの実装（Vision API 連携）
- [x] エラーコード・UI 要素の自動抽出
- [x] 画像サイズ/形式のバリデーション

**備考:**
```
テスト: 12件（全パス）
実装ファイル:
- backend/app/models/chat.py（ChatRequestにimage_data追加）
- backend/app/api/chat.py（画像エンドポイント）
- backend/app/agents/tools/image_analysis.py（Vision API ツール）
- backend/tests/test_image_api.py
- backend/tests/test_image_analysis.py
- frontend/src/components/chat/ChatInput.tsx（ドラッグ&ドロップ）
- frontend/src/lib/api.ts（uploadImage, sendMessage with imageData）
```

---

### 52. 多言語対応

| 項目 | 内容 |
|------|------|
| ID | P3-52 |
| カテゴリ | 製品戦略 |
| 難易度 | 中 |
| 対象ファイル | 全体（フロントエンド i18n, バックエンドプロンプト） |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** 言語自動検出、言語別システムプロンプト、ナレッジベースの `language` メタデータ、フロントエンド i18n。

**受け入れ条件:**
- [x] 入力テキストの言語自動検出
- [x] 言語別システムプロンプトの管理
- [x] ナレッジベースの `language` メタデータフィルタリング
- [x] フロントエンドの i18n 対応（最低: 日/英）
- [x] UI 言語切り替え機能

**備考:**
```
テスト: 10件（全パス）
実装ファイル:
- backend/app/services/language_service.py（langdetect統合）
- backend/app/services/prompt_service.py（多言語プロンプト対応）
- backend/tests/test_language_service.py
- frontend/src/i18n/index.ts（react-i18next設定）
- frontend/src/i18n/locales/ja.json, en.json（言語リソース）
- frontend/src/hooks/useLanguage.ts（言語切り替えフック）
- frontend/src/components/LanguageSwitcher.tsx
```

---

### 53. マルチチャネル（LINE/Slack/メール）

| 項目 | 内容 |
|------|------|
| ID | P3-53 |
| カテゴリ | 製品戦略 |
| 難易度 | 中〜高 |
| 対象ファイル | 新規: チャネルアダプター |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** `ChatRequest` に `channel` フィールドを追加し、LINE / Slack / メールの Webhook アダプターを構築。

**受け入れ条件:**
- [x] `ChatRequest` に `channel` フィールドを追加
- [x] チャネルアダプターのインターフェース設計
- [x] Slack Webhook アダプターの実装
- [x] LINE Messaging API アダプターの実装
- [x] メールアダプターの実装（受信: IMAP/Webhook, 送信: SMTP）
- [x] チャネル間の会話継続対応

**備考:**
```
テスト: 50件（全パス）
カバレッジ: 87%
実装ファイル:
- backend/app/channels/__init__.py（モジュール公開）
- backend/app/channels/models.py（ChannelType, ChannelMessage, ThreadMapping）
- backend/app/channels/base.py（BaseChannelAdapter 抽象基底クラス）
- backend/app/channels/mock_adapter.py（テスト用モックアダプター）
- backend/app/channels/slack_adapter.py（Slack Webhook アダプター）
- backend/app/channels/line_adapter.py（LINE Messaging API アダプター）
- backend/app/channels/email_adapter.py（メールアダプター）
- backend/app/services/channel_service.py（チャネル管理サービス、シングルトン）
- backend/app/api/channels.py（Webhook API エンドポイント）
- backend/tests/test_channels.py
変更ファイル:
- backend/app/models/chat.py（channel, channel_thread_id フィールド追加）
- backend/app/main.py（channels ルーター登録）
```

---

### 54. パーソナライゼーション

| 項目 | 内容 |
|------|------|
| ID | P3-54 |
| カテゴリ | 製品戦略 |
| 難易度 | 中 |
| 対象ファイル | エージェント, ユーザー管理 |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** `user_id` による会話履歴の個人別蓄積。ユーザーのプラン情報に基づくカスタマイズ回答。

**受け入れ条件:**
- [x] ユーザープロファイルの管理（プラン、利用履歴）
- [x] 個人別会話履歴の蓄積
- [x] ユーザー属性に基づくコンテキスト付加
- [x] 過去の質問パターンからの FAQ 先出し

**依存:** P0-10（JWT認証）, P3-48（マルチテナント）

**備考:**
```
テスト: 42件（全パス）
カバレッジ: モデル99%, サービス89%
実装ファイル:
- backend/app/models/user.py（UserPlan, ConversationRecord, UserProfile）
- backend/app/middleware/user_context.py（UserContextMiddleware、ContextVar）
- backend/app/services/user_service.py（UserService シングルトン）
- backend/app/api/user.py（/api/users/me エンドポイント）
- backend/tests/test_user.py
変更ファイル:
- backend/app/auth/jwt_handler.py（get_user_id_from_payload, verify_token_and_get_user_id）
- backend/app/agents/prompts.py（get_personalized_system_prompt）
- backend/app/services/faq_service.py（get_personalized_faqs, get_recommended_faqs）
- backend/app/main.py（UserContextMiddleware追加、user_router登録）
```

---

### 55. A/B テスト基盤

| 項目 | 内容 |
|------|------|
| ID | P3-55 |
| カテゴリ | 製品戦略 |
| 難易度 | 高 |
| 対象ファイル | 新規: A/B テストフレームワーク |
| ステータス | `[ ]` 未着手 |
| 着手日 | - |
| 完了日 | - |
| 担当 | - |
| 関連PR | - |

**概要:** プロンプト・検索戦略・UI の A/B テスト基盤。実験管理と結果分析。

**受け入れ条件:**
- [ ] 実験定義のデータモデル（バリアント、割り当て、指標）
- [ ] ユーザーのバリアント割り当てロジック
- [ ] 指標収集（回答品質、フィードバック、解決率）
- [ ] 実験結果の統計分析とレポート
- [ ] 管理 UI での実験作成・停止・結果確認

**備考:**
```
```

---

## セキュリティ（1件）

### 56. ガードレール/ジェイルブレイク対策

| 項目 | 内容 |
|------|------|
| ID | P3-56 |
| カテゴリ | セキュリティ |
| 難易度 | 高 |
| 対象ファイル | `backend/app/tools/`, エージェント設定 |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-26 |
| 完了日 | 2026-02-26 |
| 担当 | Claude Code |
| 関連PR | - |

**概要:** 高度なプロンプトインジェクション対策、トピック制限、有害コンテンツフィルタリング。

**受け入れ条件:**
- [x] 入力/出力のガードレール設計
- [x] トピックスコープ外の質問の検出と拒否
- [x] 有害コンテンツ（PII 漏洩、攻撃的表現）の検出
- [x] ジェイルブレイク攻撃パターンのテストスイート
- [x] 定期的なレッドチーミング実施手順

**依存:** P0-09（基本的なインジェクション対策）

**備考:**
```
テスト: 166件（全パス）
実装ファイル:
- backend/app/models/guardrails.py（RiskLevel, ViolationType, SafetyCheckResult）
- backend/app/agents/tools/content_safety.py（check_input_safety, check_output_safety）
- backend/app/services/guardrails_service.py（GuardrailsService）
- backend/app/middleware/guardrails.py（GuardrailsMiddleware）
- backend/app/api/guardrails.py（/api/v1/guardrails エンドポイント）
- backend/tests/test_guardrails_models.py（17テスト）
- backend/tests/test_content_safety.py（39テスト）
- backend/tests/test_guardrails_service.py（17テスト）
- backend/tests/test_guardrails_middleware.py（13テスト）
- backend/tests/test_guardrails_api.py（12テスト）
- backend/tests/test_guardrails.py（68テスト - 統合テストスイート）

検出パターン:
- プロンプトインジェクション: 10パターン
- ジェイルブレイク: 8パターン
- PII: SSN, クレジットカード, メール, 電話番号
- 攻撃的表現: 日本語/英語

レッドチーミング:
- 標準攻撃パターンリスト: 15パターン
- 検出率: 80%+ 目標
- 偽陽性率: 10%未満 目標
```

---

## 依存関係マップ

```
P0-10 (JWT認証)          ──→ P3-48 (マルチテナント)
P2-40 (PostgresSaver)    ──→ P3-48 (マルチテナント)
P2-40 (PostgresSaver)    ──→ P3-49 (データ保持ポリシー)
P3-48 (マルチテナント)    ──→ P3-49 (データ保持ポリシー)
P3-48 (マルチテナント)    ──→ P3-54 (パーソナライゼーション)
P2-45 (エスカレーション)  ──→ P3-50 (CRM連携)
P0-09 (インジェクション)  ──→ P3-56 (ガードレール)
P2-47 (プロンプト管理)    ──→ P3-55 (A/Bテスト)
```
