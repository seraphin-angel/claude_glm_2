# Plan: Tier 4 Hierarchical Delegation (Score 5+)

## Context

現状のClaude Codeのチーム委譲（Tier 3）では、リーダーエージェント（CEO）が全サブエージェントと直接やり取りし、コンテキストウィンドウが線形に消費される。大規模・長時間タスクではCEOのコンテキストが枯渇し、後半で判断品質が低下するリスクがある。

**解決策**: CEO→Director（部長）→Workers（部下）の3層階層を導入。Directorが実装管理を一手に引き受け、CEOは監督のみに専念。Directorのコンテキストが溢れそうになったら、CEOがDirectorを入れ替える（ホットスワップ）。

## 変更対象ファイル（5ファイル）

1. `/workspace/.claude/CLAUDE.md` — スコアリング基準の拡張
2. `/workspace/.claude/rules/delegation.md` — Tier 4プロトコル定義（最大の変更）
3. `/workspace/.claude/rules/agents.md` — 自動委譲トリガー追加
4. `/workspace/.claude/rules/agent-teams.md` — モデル階層・Director生成例
5. `/workspace/.claude/rules/performance.md` — コンテキスト節約表の更新

---

## 変更内容

### 1. `/workspace/.claude/CLAUDE.md`

**Complexity Quick-Checkセクション** を更新:

- スコアリング項目に2つ追加:
  - `Multiple phases or milestones required? +1`（フェーズ分割が必要）
  - `10+ files likely affected? +1`（影響範囲が10ファイル以上）
- 最大スコアが5→7に拡張
- スコア範囲の再定義:
  - `Score 0-1`: Handle directly（変更なし）
  - `Score 2`: Lightweight delegation（変更なし）
  - `Score 3-4`: Full team delegation（旧`3+`から変更）
  - `Score 5+`: **Hierarchical delegation** — CEO spawns Director (sequential-leader) who manages the team（新規）

### 2. `/workspace/.claude/rules/delegation.md`（主要変更）

**変更点一覧:**

a. セクション見出し「3-Tier」→「4-Tier Delegation Model」に変更

b. Tier 3のスコア範囲を `Score 3+` → `Score 3-4` に変更

c. Tier 4セクション新設（Tier 3の直後に挿入）:
```
### Tier 4: Hierarchical Delegation (Score 5+)
CEO spawns a Director (sequential-leader) who takes full ownership:
1. CEO reads up to 5 files for orientation only
2. CEO creates team (TeamCreate)
3. CEO spawns ONE Director (sequential-leader, sonnet) with full project brief
4. Director creates all tasks, spawns all workers, tracks progress autonomously
5. CEO monitors via periodic Director status reports
6. Director context pressure detected → CEO executes Director Handoff Protocol
7. CEO delivers final summary to user
```

d. 「Delegation Protocol (for Tier 4)」セクション新設 — 5ステップ:
   - Step 1: CEO Orientation（5ファイル読み込み上限）
   - Step 2: Create Team and Spawn Director
   - Step 3: CEO Supervision Only（CEO不介入ルール）
   - Step 4: Director Handoff（ホットスワップ手順）
   - Step 5: Final Verification

e. **Director Handoff Summary Format** 定義（Directorが終了時に必ず出力する構造化サマリー）:
   - Project Goal / Completed Work / Current State / Remaining Tasks / Key Context / TaskList State

f. Request Classificationテーブルに新行追加:
   - `Full application build` → `HIERARCHICAL DELEGATE`

g. Context Window Budgetテーブルを Tier 3用/Tier 4用 に分離:
   - Tier 4: CEO context usage目標 ~40%以下（orientation 10% + Director brief 15% + supervision 30% + questions 15% + handoff 10% + buffer 20%）

h. Spawning Patternsセクションに「Full Application Build / Massive Refactor (Tier 4)」パターン追加:
   - `CEO → Director (sequential-leader) → Explore/Workers/Reviewers`
   - ハンドオフサイクル図を含む

### 3. `/workspace/.claude/rules/agents.md`

a. Auto-Delegation Triggerセクション:
   - `Score 3+` → `Score 3-4` に変更
   - `Score 5+` ブロック新設:
     - アナウンス: 「大規模タスクのため、階層委譲（社長→部長→ワーカー）を行います」
     - Director生成 → 自律管理 → CEOは監督のみ

b. Agent Selection Quick Reference テーブルに行追加:
   - `Manage large team as Director | sequential-leader | sonnet`

### 4. `/workspace/.claude/rules/agent-teams.md`

a. Model Hierarchyテーブルに Director行追加:
   - `Director (Sub-Leader) | sequential-leader | sonnet | Mid-level orchestration for Tier 4`
   - 既存の `Team Lead` を `CEO (Team Lead)` に名称変更

b. Spawning Examples に「Spawning a Director」例を追加:
   - Directorへの初期プロンプトテンプレート（日本語）
   - Directorの責務定義（TaskCreate、Worker生成、進捗報告、ハンドオフサマリー生成）

c. Leader MUST NOTセクションにルール追加:
   - 「Tier 4では複数のDirectorを同時起動しない（常に1人のみ）」

### 5. `/workspace/.claude/rules/performance.md`

a. Delegation as Context-Saving表を拡張:
   - 3列目に「Tier 4 Delegated Cost」列を追加
   - 新行: `Task creation & tracking: ~10% (Tier 3 CEO creates) → 0% (Director creates)`
   - 新行: `Multi-phase coordination: ~20% (Tier 3 CEO tracks) → 0% (Director tracks)`
   - Tier 3結果: CEO ~35% / Tier 4結果: CEO ~15%

b. 「Director Handoff as Infinite Context」サブセクション新設:
   - ハンドオフサイクルごとのCEOコンテキストコスト: 約2-5%
   - 理論上無制限のプロジェクト規模に対応可能

---

## 設計上の注意事項

### Director Model: sonnet（opusではない理由）
- Directorの主務は「実装の詳細管理・タスク分割・Worker生成」= 実行系タスク → sonnet
- CEOの主務は「戦略判断・ユーザーコミュニケーション・ハンドオフ判断」= 推論系タスク → opus
- コスト効率: Directorは入れ替え前提のため、sonnetの方が経済的

### Score 5の判定猶予
- Score 5でも、CEOがTier 3で十分管理可能と判断した場合はTier 3を選択可能
- Scoreは最低閾値であり、強制ではない旨をCLAUDE.mdに注記

### Fallback: sequential-leaderが利用不可の場合
- `general-purpose` + sonnet に Director instructions を埋め込むことで代替可能
- delegation.mdにfallback注記を含める

---

## 実装順序

1. **CLAUDE.md** — 全ファイルが参照するスコア基準を最初に確定
2. **delegation.md** — Tier 4プロトコルの詳細定義（agents.md等が参照）
3. **agents.md** — 自動委譲トリガーテキスト追加
4. **agent-teams.md** — Director役割・生成例追加
5. **performance.md** — コスト表・理論的説明の更新

5ファイルは内容的には独立しているため、並列実装も可能。

---

## 検証方法

1. 各ファイルのクロスリファレンス整合性確認:
   - CLAUDE.mdのスコア範囲 ↔ delegation.mdのTier定義 ↔ agents.mdのトリガー
   - agent-teams.mdのModel Hierarchy ↔ delegation.mdのSpawning Pattern
2. Score 5+のシナリオを想定し、delegation.mdのプロトコルを手順通りにトレースできるか確認
3. Director Handoff Summary Formatが過不足なく定義されているか確認
4. 日本語ルール（agent-teams.md）がTier 4にも適用されているか確認
