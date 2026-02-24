# Plan: リーダーの委譲強化 — コンテキスト消費を最小化する

## Context

チーム構成で大規模タスクを実行する際、リーダー（メインセッション）が自らコード読み・書き・テスト実行などを行い、コンテキストウィンドウを消費してしまう問題がある。`sequential-leader.md` エージェントは正しい委譲設計を持つが、**明示的に呼び出されたときのみ**有効。メインセッションに自動的な委譲行動を組み込む必要がある。

## 方針

**2層アプローチ**: CLAUDE.md に「プライムディレクティブ」（短く高インパクト）、`rules/delegation.md` に詳細ルールを配置。既存 rules ファイル3つにも関連セクションを追加。

## 変更ファイル一覧

| # | ファイル | 操作 | 内容 |
|---|---------|------|------|
| 1 | `/workspace/.claude/CLAUDE.md` | 修正（現在空） | プライムディレクティブ（複雑度チェック＋委譲原則） |
| 2 | `/workspace/.claude/rules/delegation.md` | 新規作成 | 詳細な委譲ルール、判断フロー、アンチパターン、エージェント選択パターン |
| 3 | `/workspace/.claude/rules/agent-teams.md` | 末尾に追加 | リーダー行動規範（MUSTとMUST NOT） |
| 4 | `/workspace/.claude/rules/agents.md` | 末尾に追加 | 自動委譲トリガーとエージェント選択リファレンス |
| 5 | `/workspace/.claude/rules/performance.md` | 末尾に追加 | 委譲によるコンテキスト節約の数値化 |

---

## Step 1: `/workspace/.claude/CLAUDE.md` を修正（現在空 → プライムディレクティブ）

全会話で最初に読み込まれるため、最もインパクトが高い。35行以内に抑えて注意重みを最大化する。

```markdown
# Leader Behavior: Delegate, Don't Implement

## Prime Directive

You are an ORCHESTRATOR, not an implementer. For any task involving 3+ files, 2+ features, or significant codebase exploration:

1. **DO NOT** read large codebases, write code, run tests, or do detailed reviews yourself
2. **DO** create a team (TeamCreate), break work into tasks (TaskCreate), and spawn sub-agents
3. **DO** limit your own actions to: planning, task creation, spawning agents, reviewing agent reports, reporting to user

## Complexity Quick-Check (MANDATORY for every user request)

Before acting on ANY implementation request, score it:
- Touches 3+ files? → +1
- Requires reading >5 files to understand context? → +1
- Involves writing/editing code? → +1
- Requires running tests or builds? → +1
- Multiple features or multi-step implementation? → +1

**Score 0-1:** Handle directly (simple fix, single-file edit, quick question)
**Score 2:** Lightweight delegation — spawn a single Task sub-agent (no TeamCreate). Leader provides task description, agent executes and reports back.
**Score 3+:** Full team delegation — TeamCreate + TaskCreate + multiple agents. Leader plans, agents execute.

## Allowed Leader Actions

- Read up to 5 files for initial planning orientation
- Create teams, tasks, and spawn agents
- Review agent reports (NOT re-review all code line-by-line)
- Communicate with user (progress, questions, final report)
- Run 1-2 final smoke-check commands max

See: `.claude/rules/delegation.md` for detailed rules
```

---

## Step 2: `/workspace/.claude/rules/delegation.md` を新規作成

包括的な委譲ルール、判断フロー、アンチパターン集。

### 主要セクション構成:

1. **リクエスト分類テーブル** — 質問/単ファイル修正は直接対応、マルチファイル実装/リファクタ/監査は委譲
2. **委譲プロトコル** — 軽量探索(5ファイル以内) → チーム作成 → タスク分割 → エージェント起動 → 追跡・報告
3. **アンチパターン5つ**:
   - Deep Code Reading（10+ファイル読み）→ Explore エージェントに委譲
   - Writing Code（Edit/Write使用）→ Worker エージェントに委譲
   - Running Test Suites → Worker/Reviewer に委譲
   - Detailed Code Review → code-reviewer に委譲
   - Iterative Debugging → Worker にエラーコンテキスト付きで委譲
4. **コンテキスト予算配分**:
   - 初期計画探索: 15%（5ファイル読みまで）
   - チーム/タスク管理: 20%
   - エージェント結果レビュー: 30%
   - ユーザーコミュニケーション: 20%
   - バッファ: 15%
5. **例外ケース** — 直接対応が許可される場合（スコア0-1、ユーザー明示指示、緊急ホットフィックス、質問応答）
6. **タスクタイプ別エージェント構成パターン**:
   - 機能実装: Explore(haiku) → Worker(sonnet) → Reviewer(sonnet)
   - バグ修正: Explore(haiku) → Worker(sonnet) → Reviewer(sonnet)
   - リファクタ: Explore(haiku) → Worker(sonnet, sequential per module) → Reviewer(sonnet)
   - セキュリティ監査: security-reviewer → Worker(sonnet) → security-reviewer

---

## Step 3: `/workspace/.claude/rules/agent-teams.md` に追加

既存内容の末尾に「Leader Behavior in Teams」セクションを追加:

- **リーダーMUST**: 計画してから起動、全実装を委譲、5ファイル超の探索を委譲、テストを委譲、TaskListで追跡、日本語で報告
- **リーダーMUST NOT**: 5ファイル超の読み込み、コード書き/編集、テストスイート実行、行単位コードレビュー、反復デバッグ

---

## Step 4: `/workspace/.claude/rules/agents.md` に追加

「Auto-Delegation Trigger」セクションを追加:

- 複雑度スコア2+で、ユーザーに「チームを作成して対応します」と宣言
- TeamCreate → TaskCreate → ユーザー承認 → エージェント起動 の手順を必須化
- 実装作業開始前にステップ1-4を完了する義務

---

## Step 5: `/workspace/.claude/rules/performance.md` に追加

「Delegation as Context-Saving Strategy」セクション:

- 具体的な数値でコンテキスト節約効果を示す:
  - 20ファイル読み: リーダーで約40%消費 → 委譲で0%
  - 実装コード書き: 約30%消費 → 委譲で0%
  - テスト実行/デバッグ: 約20%消費 → 委譲で0%
- 委譲により全体使用量 ~100% → ~35% に削減

---

## 3段階委譲モデル（軽量委譲を含む）

| スコア | 対応方式 | 具体的なアクション |
|-------|---------|-----------------|
| 0-1 | 直接対応 | リーダーが自分で実行（単ファイル修正、質問回答） |
| 2 | 軽量委譲 | TeamCreate なし。Task ツールで単一サブエージェント(sonnet)を起動。完了後結果を受け取るだけ |
| 3+ | フルチーム委譲 | TeamCreate → TaskCreate で全タスク登録 → ユーザー承認 → 複数エージェントで実行 |

### 軽量委譲の例（スコア2）
```
リーダー: 「この変更は2ファイルにまたがるので、サブエージェントに任せます」
→ Task tool で general-purpose (sonnet) を1つ起動
→ サブエージェントが実装・テスト・報告
→ リーダーは結果をユーザーに報告
```

### フルチーム委譲の例（スコア3+）
```
リーダー: 「この機能実装は複数ステップが必要です。チームを組みます」
→ TeamCreate でチーム作成
→ TaskCreate で全タスク登録（依存関係設定含む）
→ ユーザーに承認を求める
→ エージェント群で並列/逐次実行
→ リーダーは進捗報告と最終確認
```

---

## 設計上のトレードオフ

| 判断 | 理由 |
|------|------|
| CLAUDE.md を35行以内に制限 | 長すぎると注意重みが希薄化。詳細は rules/ に分離 |
| 3段階モデル（直接/軽量/フル） | スコア2のボーダーラインタスクにフルチームはオーバーヘッド過大。軽量委譲が最適 |
| リーダーに5ファイルの読み取りを許可 | 0だと盲目的な委譲になり、タスク記述の質が低下する |
| 既存3ファイルに分散追加 vs 1つの大ファイル | 各ファイルの関連コンテキスト内にルールを配置する方が効果的 |
| sequential-leader.md は変更なし | 既に正しい設計。問題はメインセッション側にある |

---

## 検証方法

実装後、以下のシナリオで動作確認:

1. **「REST APIと認証機能を作って」** → スコア4+、即座にチーム作成を提案するはず
2. **「settings.py のタイポを直して」** → スコア0-1、直接対応するはず
3. **「バックエンド全体をDI化して」** → スコア4+、委譲すべき
4. **「vector_store.py は何をしている？」** → 質問、直接回答すべき
5. リーダーが Edit/Write ツールを使わないことを確認
