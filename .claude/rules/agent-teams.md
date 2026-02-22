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
| Team Lead | Main session | **opus** | Deep reasoning for orchestration and decision-making |
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
