# Agent Orchestration

## Available Agents

Located in `~/.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| tdd-guide | Test-driven development | New features, bug fixes |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits |
| build-error-resolver | Fix build errors | When build fails |
| e2e-runner | E2E testing | Critical user flows |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| doc-updater | Documentation | Updating docs |

## Immediate Agent Usage

No user prompt needed:
1. Complex feature requests - Use **planner** agent
2. Code just written/modified - Use **code-reviewer** agent
3. Bug fix or new feature - Use **tdd-guide** agent
4. Architectural decision - Use **architect** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth.ts
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utils.ts

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker

## Auto-Delegation Trigger

When a user request scores 2+ on the complexity quick-check (see CLAUDE.md):

### Score 2 — Lightweight Delegation
1. Announce: "サブエージェントに委譲します"
2. Spawn a single Task sub-agent (`general-purpose`, `model: "sonnet"`)
3. Wait for result, report to user

### Score 3-4 — Full Team Delegation
1. Announce: "チームを作成して対応します"
2. TeamCreate to establish the team
3. TaskCreate for all tasks with dependencies
4. Present task list for user approval
5. Execute via agent spawning (see `rules/delegation.md`)

### Score 5+ — Hierarchical Delegation
1. Announce: "大規模タスクのため、階層委譲（社長→部長→ワーカー）を行います"
2. TeamCreate to establish the team
3. Spawn ONE Director (`sequential-leader`, `model: "sonnet"`) with full project brief
4. Director autonomously manages all tasks and workers
5. CEO supervises only — answers clarifications, reports progress to user in Japanese
6. See `rules/delegation.md` for Director Handoff Protocol

The main session MUST NOT begin implementation work before completing these steps.

## Agent Selection Quick Reference

| Need | Agent Type | Model |
|------|-----------|-------|
| Investigate codebase | `Explore` | haiku |
| Implement feature | `general-purpose` | sonnet |
| Run tests & review | `code-reviewer` | sonnet |
| Security audit | `security-reviewer` | (own setting) |
| Architecture design | `architect` | (own setting) |
| Manage large team as Director | `sequential-leader` | sonnet |
