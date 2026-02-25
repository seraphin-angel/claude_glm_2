# Agent Teams Rules

## Language

All team members MUST communicate with the user in **Japanese (日本語)**.
This applies to:
- Questions and confirmations to the user
- Progress reports and summaries
- Error messages and warnings

Internal thinking and code comments may remain in English.

## Model Hierarchy

When creating Agent Teams, always assign models via the `model` parameter:

| Role | subagent_type | model | Rationale |
|------|--------------|-------|-----------|
| CEO (Team Lead) | Main session | **opus** | Deep reasoning for orchestration and decision-making |
| Director (Sub-Leader) | `sequential-leader` | **sonnet** | Mid-level orchestration for Tier 4; carries full implementation context |
| Implementation Worker | `general-purpose` | **sonnet** | Balanced capability and cost for coding tasks |
| Code Reviewer | `code-reviewer` | **sonnet** | Sufficient quality for review and testing |
| Researcher | `Explore` | **haiku** | Lightweight and cost-efficient for read-only tasks |

## Rules

1. **Never omit the `model` parameter** when spawning team members via the Task tool
2. **Use `general-purpose` + `model: "sonnet"`** for implementation tasks (coding, fixing, testing)
3. **Use `Explore` + `model: "haiku"`** for read-only exploration and investigation
4. **Use `code-reviewer` + `model: "sonnet"`** for post-implementation quality checks
5. **Existing specialized agents** (planner, architect, security-reviewer, etc.) retain their own model settings — do not override their models

## Prompt Template

When spawning team members, always include the language instruction in the prompt:

```
[タスクの具体的な指示]

ユーザーへの報告・質問・確認は必ず日本語で行うこと。
```

## Usage Examples

### Spawning a worker (implementation)
```
Task tool:
  subagent_type: "general-purpose"
  model: "sonnet"
  team_name: "my-team"
  prompt: "ユーザー認証機能を実装してください。...（タスク詳細）... ユーザーへの報告・質問・確認は必ず日本語で行うこと。"
```

### Spawning a researcher (read-only)
```
Task tool:
  subagent_type: "Explore"
  model: "haiku"
  team_name: "my-team"
  prompt: "認証関連のファイルを全て調査し、現在の構成を報告してください。ユーザーへの報告・質問・確認は必ず日本語で行うこと。"
```

### Spawning a reviewer
```
Task tool:
  subagent_type: "code-reviewer"
  model: "sonnet"
  team_name: "my-team"
  prompt: "認証機能の変更をレビューし、テストを実行してください。ユーザーへの報告・質問・確認は必ず日本語で行うこと。"
```

### Spawning a Director (Tier 4 hierarchical delegation)
````
Task tool:
  subagent_type: "sequential-leader"
  model: "sonnet"
  team_name: "my-team"
  prompt: |
    あなたはこのプロジェクトのDirector（部長）です。以下のプロジェクトを担当してください。

    ## プロジェクト目標
    [Full project description from CEO]

    ## チーム名
    my-team

    ## 技術スタック
    [Tech stack details]

    ## 制約事項
    [Constraints, deadlines, patterns to follow]

    ## あなたの責務
    - TaskCreate で全タスクを定義し、依存関係を設定する
    - Worker/Reviewerエージェントを必要に応じて生成する
    - 進捗をCEO（リーダー）に定期報告する
    - コンテキストが不足しそうな場合、即座にCEOへ DIRECTOR HANDOFF SUMMARY を送信して引き継ぎを要請する
    - DIRECTOR HANDOFF SUMMARYの形式は rules/delegation.md を参照すること

    ユーザーへの報告・質問・確認は必ず日本語で行うこと。
````

## Leader Behavior in Teams

When operating as the team leader (main session), these rules apply:

### The Leader MUST:
1. **Plan before spawning** — create a task breakdown before launching any agent
2. **Delegate ALL implementation** — never use Edit, Write, or file-creation tools
3. **Delegate exploration beyond 5 files** — spawn Explore agents (haiku) for deep investigation
4. **Delegate ALL testing** — include test execution in worker or reviewer agent tasks
5. **Track via TaskList** — check task status after each agent completes
6. **Report to user in Japanese** — progress updates after each phase completion

### The Leader MUST NOT:
1. Read more than 5 files for initial orientation
2. Write, edit, or create any code files
3. Run test suites, linters, or build commands (except 1-2 final smoke checks)
4. Review code line-by-line (delegate to code-reviewer agent)
5. Debug iteratively (delegate to worker agent with error context)
6. In Tier 4, spawn multiple Directors simultaneously (only one active Director at a time)
