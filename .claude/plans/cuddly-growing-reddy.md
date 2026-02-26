# Plan: プランモード時のサブエージェントモデルをOpusに統一

## Context

プランモードでは計画立案・調査・設計が目的であり、実装は行わない。現在のルールではサブエージェントのモデル選択が「実装時のコスト効率」を前提に設計されている（Explore=haiku, Worker=sonnet等）。しかし、プランモード時の探索・設計では質が最優先であるため、すべてのサブエージェントをOpusモデルで起動すべき。

**変更方針**: 実装モード時のモデル階層はそのまま維持し、プランモード時のみOpusを使うルールを追加する。

## 変更対象ファイル（4ファイル）

### 1. `.claude/rules/agent-teams.md`
**変更箇所**: Model Hierarchy テーブルの直後に「Plan Mode Override」セクションを追加

追加内容:
```markdown
## Plan Mode Override

プランモード（計画立案フェーズ）が有効な場合、上記のモデル階層は適用されない。
プランモードでは**すべてのサブエージェントに `model: "opus"` を指定すること**。

| Role | subagent_type | model (Plan Mode) | Rationale |
|------|--------------|-------------------|-----------|
| Researcher | `Explore` | **opus** | 計画立案時は探索の質が最優先 |
| Planner | `Plan` | **opus** | 設計判断に最高品質の推論が必要 |
| その他全エージェント | any | **opus** | プランモードでは品質 > コスト |

> 実装モード（通常モード）に戻った場合は、通常のモデル階層に従うこと。
```

### 2. `.claude/rules/agents.md`
**変更箇所**: Agent Selection Quick Reference テーブルの直後に注意書きを追加

追加内容:
```markdown
> **Plan Mode**: プランモードが有効な場合、上記のモデル指定は無視し、すべてのサブエージェントに `model: "opus"` を使用すること。詳細は `rules/agent-teams.md` の Plan Mode Override を参照。
```

### 3. `.claude/rules/delegation.md`
**変更箇所**:
- Delegation Protocol (Tier 3) Step 3 の「following model hierarchy」の注釈を追加
- Anti-Patterns セクション内の Explore agent (haiku) 記述に注釈を追加

追加内容（Step 3 直後）:
```markdown
> **Plan Mode例外**: プランモードでは全エージェントに `model: "opus"` を使用。`rules/agent-teams.md` Plan Mode Override 参照。
```

### 4. `.claude/rules/performance.md`
**変更箇所**: Model Selection Strategy セクションに Plan Mode の項目を追加

追加内容:
```markdown
### Plan Mode Model Policy

プランモードでは上記のモデル選択戦略は適用されない。
計画立案フェーズでは探索・設計の質が最優先のため、**すべてのサブエージェントに `model: "opus"` を指定する**。
コスト効率は実装フェーズで考慮する。
```

## 変更しないファイル
- `CLAUDE.md` — モデル選択の詳細には言及していないため変更不要
- `rules/testing.md` — テスト実行は実装フェーズの話のため変更不要
- `rules/security.md` — セキュリティルールは変更不要
- `rules/coding-style.md` — コーディングスタイルは変更不要

## 検証方法
1. 各ファイルを変更後、プランモードでサブエージェントを起動するシナリオを想定して、ルール間の整合性を確認
2. 実装モード時のモデル階層が影響を受けていないことを確認（通常テーブルはそのまま残す）
3. grep で `haiku` や `sonnet` の記述が残っている箇所がプランモードのコンテキストで使われていないことを確認
