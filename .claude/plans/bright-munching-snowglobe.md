# P3-53 マルチチャネル対応 実装計画

## Context

ユーザーが `/ev:tdd` コマンドで P3-quarter3 の残タスク実装を依頼。優先タスクとして **P3-53 マルチチャネル（LINE/Slack/メール）** を選択。

**目的**: チャットボットを Slack、LINE、メールなどの複数チャネルで利用可能にし、チャネル間での会話継続を可能にする。

**依存関係**: なし（既存の BaseTicketAdapter パターンを再利用）

---

## 新規ファイル一覧

| ファイル | 説明 |
|---------|------|
| `backend/app/channels/__init__.py` | モジュール公開 |
| `backend/app/channels/models.py` | チャネル関連データモデル（不変） |
| `backend/app/channels/base.py` | BaseChannelAdapter 抽象基底クラス |
| `backend/app/channels/mock_adapter.py` | テスト用モックアダプター |
| `backend/app/channels/slack_adapter.py` | Slack Webhook アダプター |
| `backend/app/channels/line_adapter.py` | LINE Messaging API アダプター |
| `backend/app/channels/email_adapter.py` | メールアダプター（IMAP/SMTP） |
| `backend/app/services/channel_service.py` | チャネル管理サービス（シングルトン） |
| `backend/app/api/channels.py` | Webhook API エンドポイント |
| `backend/tests/test_channels.py` | テストスイート（TDD） |

## 既存ファイル変更

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/chat.py` | ChatRequest に `channel`, `channel_thread_id` フィールド追加 |
| `backend/app/main.py` | channels ルーター登録 |

---

## 実装フェーズ

### Phase 1: 基盤構築（モデル + インターフェース）

**TDD順序:**
1. `test_channel_type_enum` → ChannelType 列挙型実装
2. `test_channel_message_creation` → ChannelMessage モデル実装
3. `test_channel_message_immutability` → frozen=True 確認
4. `test_base_adapter_abstract` → BaseChannelAdapter 抽象クラス実装
5. `test_mock_adapter` → MockChannelAdapter 実装

**ファイル:**
- `backend/app/channels/models.py`
- `backend/app/channels/base.py`
- `backend/app/channels/mock_adapter.py`
- `backend/app/models/chat.py`（変更）

### Phase 2: チャネルアダプター実装

**Slack アダプター:**
- `test_slack_signature_verification` → HMAC-SHA256 検証
- `test_slack_send_message` → chat.postMessage API
- `test_slack_parse_event` → Events API パース

**LINE アダプター:**
- `test_line_signature_verification` → HMAC-SHA256 検証
- `test_line_send_message` → push/reply message API
- `test_line_parse_webhook` → Webhook パース

**メール アダプター:**
- `test_email_send` → SMTP 送信
- `test_email_parse` → MIME パース
- `test_email_thread_headers` → In-Reply-To/References

**ファイル:**
- `backend/app/channels/slack_adapter.py`
- `backend/app/channels/line_adapter.py`
- `backend/app/channels/email_adapter.py`

### Phase 3: サービス層

**テスト:**
- `test_channel_service_singleton`
- `test_register_adapter`
- `test_create_thread_mapping`
- `test_route_to_channel`
- `test_handle_incoming_with_signature`

**ファイル:**
- `backend/app/services/channel_service.py`

### Phase 4: API層

**テスト:**
- `test_slack_webhook_endpoint`
- `test_line_webhook_endpoint`
- `test_email_webhook_endpoint`
- `test_invalid_signature_rejection`
- `test_register_channel_admin`

**ファイル:**
- `backend/app/api/channels.py`
- `backend/app/main.py`（変更）

### Phase 5: 統合・検証

- E2Eテスト（Webhook受信→応答送信）
- カバレッジ確認（80%以上）
- タスクファイル更新

---

## 再利用する既存パターン

| パターン | 参照ファイル | 活用先 |
|---------|-------------|-------|
| BaseAdapter 抽象クラス | `integrations/base.py` | `channels/base.py` |
| 不変データモデル | `models/tenant.py` | `channels/models.py` |
| シングルトンサービス | `services/integration_service.py` | `services/channel_service.py` |
| httpx HTTPクライアント | `integrations/zendesk.py` | 各アダプター |
| Webhook署名検証 | Zendesk実装 | Slack/LINE署名 |

---

## Critical Files（実装前に必ず読む）

1. `/workspace/agentic-rag-chatbot/backend/app/models/chat.py` - ChatRequest 構造
2. `/workspace/agentic-rag-chatbot/backend/app/integrations/base.py` - アダプターパターン
3. `/workspace/agentic-rag-chatbot/backend/app/services/integration_service.py` - シングルトンパターン
4. `/workspace/agentic-rag-chatbot/backend/tests/test_crm_integration.py` - テストパターン

---

## 検証方法

```bash
# テスト実行
cd backend && pytest tests/test_channels.py -v

# カバレッジ確認
cd backend && pytest tests/test_channels.py --cov=app/channels --cov=app/services/channel_service --cov-report=term-missing

# 型チェック
cd backend && mypy app/channels/

# 統合テスト
cd backend && pytest tests/test_channels.py -v -k "integration"
```

---

## 受け入れ条件チェックリスト

- [ ] `ChatRequest` に `channel` フィールドを追加
- [ ] チャネルアダプターのインターフェース設計（BaseChannelAdapter）
- [ ] Slack Webhook アダプターの実装
- [ ] LINE Messaging API アダプターの実装
- [ ] メールアダプターの実装（受信: IMAP/Webhook, 送信: SMTP）
- [ ] チャネル間の会話継続対応（thread_id マッピング）
- [ ] テストカバレッジ 80%以上
