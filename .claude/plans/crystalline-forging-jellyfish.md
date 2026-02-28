# P3-54 パーソナライゼーション機能 実装計画

## Context

P3-53（マルチチャネル）を別セッションで実施中に並行して実施可能なタスクとして、P3-54パーソナライゼーション機能を実装する。

**目的**: ユーザーごとの会話履歴蓄積、属性に基づくコンテキスト付加、過去の質問パターンからのFAQ先出しを実現し、ユーザー体験を向上させる。

**依存関係**: P3-48（マルチテナント完了済み）、P0-10（JWT認証完了済み）

---

## Architecture

```
HTTP Request → UserContextMiddleware → TenantMiddleware → API Handler
                      ↓
              JWTからuser_id抽出
              UserServiceでプロファイル取得
              ContextVarに設定

Agent実行時:
AgentState ← get_current_user_context() → prompts.py でパーソナライズ済みプロンプト生成
```

---

## Phase 1: ユーザーモデルとコンテキスト管理

### 新規ファイル
- `backend/app/models/user.py` - UserPlan, ConversationRecord, UserProfile, UserCreateRequest
- `backend/app/middleware/user_context.py` - ContextVar パターン（TenantMiddlewareと同じ）
- `backend/tests/test_user.py` - テストケース

### テストケース (RED → GREEN)
```
TestUserModel:
- test_user_create_valid
- test_user_with_plan
- test_user_immutability

TestUserContext:
- test_get_current_user_id_not_set
- test_set_and_get_current_user_context
- test_reset_user_context

TestUserContextMiddleware:
- test_middleware_extracts_user_from_jwt
- test_middleware_works_without_auth
```

---

## Phase 2: ユーザーサービス実装

### 新規ファイル
- `backend/app/services/user_service.py` - シングルトンパターン（TenantServiceと同じ）

### テストケース (RED → GREEN)
```
TestUserService:
- test_create_user
- test_get_user
- test_update_user_plan
- test_record_conversation
- test_get_conversation_history
- test_get_frequently_asked_topics
- test_singleton_pattern
- test_get_personalized_context
```

---

## Phase 3: JWT認証拡張とエージェント統合

### 修正ファイル
- `backend/app/auth/jwt_handler.py` - `verify_token_payload()` 追加
- `backend/app/agents/prompts.py` - `get_personalized_system_prompt()` 追加

### テストケース (RED → GREEN)
```
TestJWTWithUserContext:
- test_jwt_contains_user_id
- test_jwt_with_custom_claims

TestAgentWithUserContext:
- test_personalized_system_prompt
```

---

## Phase 4: FAQ先出し機能

### 修正ファイル
- `backend/app/services/faq_service.py` - `get_personalized_faqs()`, `get_recommended_faqs()` 追加

### テストケース (RED → GREEN)
```
TestFAQPersonalization:
- test_get_personalized_faqs_by_user
- test_faqs_based_on_history
- test_combined_page_and_user_faqs
```

---

## Phase 5: API統合

### 新規ファイル
- `backend/app/api/user.py` - GET /api/users/me, GET /api/users/me/history, PATCH /api/users/me/plan

### 修正ファイル
- `backend/app/main.py` - UserContextMiddleware追加、user_router追加

### テストケース (RED → GREEN)
```
TestUserAPI:
- test_get_user_profile_api
- test_get_conversation_history_api
- test_update_user_plan_api
```

---

## Critical Files

| ファイル | 種別 | 説明 |
|---------|------|------|
| `backend/app/models/user.py` | 新規 | UserProfile, UserPlan モデル（frozen=True） |
| `backend/app/middleware/user_context.py` | 新規 | ContextVar パターン踏襲 |
| `backend/app/services/user_service.py` | 新規 | シングルトンパターン踏襲 |
| `backend/app/agents/prompts.py` | 修正 | get_personalized_system_prompt() 追加 |
| `backend/app/services/faq_service.py` | 修正 | get_recommended_faqs() 追加 |
| `backend/app/api/user.py` | 新規 | /api/users/me エンドポイント |
| `backend/tests/test_user.py` | 新規 | 全テストケース |

---

## 受け入れ条件マッピング

| 条件 | 実装箇所 |
|------|---------|
| ユーザープロファイル管理（プラン、利用履歴） | UserService.create_user, update_user_plan |
| 個人別会話履歴の蓄積 | UserService.record_conversation, get_conversation_history |
| ユーザー属性に基づくコンテキスト付加 | prompts.py:get_personalized_system_prompt |
| 過去の質問パターンからのFAQ先出し | faq_service.py:get_recommended_faqs |

---

## Verification

```bash
cd agentic-rag-chatbot/backend

# 全テスト実行
pytest tests/test_user.py -v

# カバレッジ確認（80%+目標）
pytest tests/test_user.py --cov=app --cov-report=term-missing
```

---

## TDD Workflow

各フェーズで以下のサイクルを実行:
1. **RED** - テストを先に書いて失敗を確認
2. **GREEN** - 最小限の実装でテストを通す
3. **REFACTOR** - コードを整理しつつテスト維持
4. **COVERAGE** - 80%+を確認
