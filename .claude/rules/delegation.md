# Delegation Rules

## When to Delegate (Request Classification)

| Request Type | Examples | Action |
|-------------|----------|--------|
| Question / Explanation | "How does X work?", "Explain Y" | Handle directly |
| Single-file fix | "Fix the typo in settings.py" | Handle directly |
| Config change | "Update the port number" | Handle directly |
| Multi-file feature | "Add authentication", "Build API" | **DELEGATE** |
| Application build | "Build me an app", "Implement features" | **DELEGATE** |
| Codebase refactor | "Refactor the auth module" | **DELEGATE** |
| Comprehensive review | "Review the entire backend" | **DELEGATE** |

## 3-Tier Delegation Model

### Tier 1: Direct (Score 0-1)
Leader handles it. One-line fixes, config changes, answering questions.

### Tier 2: Lightweight Delegation (Score 2)
No TeamCreate. Spawn a single Task sub-agent (general-purpose, sonnet):
1. Leader reads up to 5 files for context
2. Leader spawns one sub-agent via Task tool with clear description
3. Sub-agent implements, tests, and reports back
4. Leader reports result to user

### Tier 3: Full Team Delegation (Score 3+)
Full orchestration with TeamCreate:
1. Leader reads up to 5 files for initial orientation
2. TeamCreate to establish the team
3. TaskCreate for all tasks with dependencies (blockedBy)
4. Present task list to user for approval
5. Spawn agents per task following model hierarchy (agent-teams.md)
6. Track via TaskList, report progress after each phase
7. Final verification (1-2 smoke-check commands max)

## Delegation Protocol (for Tier 3)

### Step 1: Lightweight Exploration (max 5 file reads, max 3 grep/glob searches)
- Understand project structure and tech stack
- Identify relevant existing patterns
- **STOP if you need more** — spawn an Explore agent (haiku) instead

### Step 2: Create Team and Tasks
- TeamCreate with descriptive team name
- TaskCreate: 1 task = 1 feature OR ~1 file OR 1 logical unit
- Set dependencies via TaskUpdate (blockedBy) as needed
- Present to user and wait for approval

### Step 3: Spawn Agents (following model hierarchy)
- Explore agents (haiku) for codebase investigation
- Worker agents (sonnet) for implementation
- Reviewer agents (sonnet) for quality checks

### Step 4: Track and Report
- Monitor via TaskList after each agent completes
- Report progress to user in Japanese after each phase
- Handle blockers by adjusting tasks or spawning additional agents

### Step 5: Final Verification
- Review agent reports only (NOT all code line-by-line)
- Run 1-2 smoke-check commands if needed
- Deliver final summary to user

## Anti-Patterns (NEVER DO as Leader)

### 1. Deep Code Reading
- BAD: Reading 10+ files to understand the full codebase
- GOOD: Spawn an Explore agent (haiku) to investigate and report

### 2. Writing Code
- BAD: Using Edit/Write tools to implement features
- GOOD: Spawn a worker agent (sonnet) with clear task description

### 3. Running Test Suites
- BAD: Running pytest, npm test, full test suites yourself
- GOOD: Include test execution in the worker or reviewer agent's task

### 4. Detailed Code Review
- BAD: Reading every changed file line-by-line
- GOOD: Spawn a code-reviewer agent (sonnet) to review and report

### 5. Iterative Debugging
- BAD: Read error → edit file → run again → repeat yourself
- GOOD: Spawn a worker agent with error context and let it iterate

## Context Window Budget

| Activity | Max Allocation |
|----------|---------------|
| Initial planning exploration | 15% (5 file reads max) |
| Team/task management overhead | 20% |
| Agent result reviews | 30% |
| User communication | 20% |
| Buffer for unexpected needs | 15% |

If you exceed the planning exploration budget, STOP and delegate to an Explore agent.

## Exceptions (Leader CAN Act Directly)

1. **Trivial changes** (score 0-1): One-line fixes, typo corrections, config values
2. **User explicitly requests direct action**: "Just fix this one line"
3. **Emergency hotfixes**: Production down, scope already well-defined
4. **Answering questions**: Reading 1-3 files to explain code/architecture

## Spawning Patterns by Task Type

### Feature Implementation
```
Explore (haiku) → Worker (sonnet) → Reviewer (sonnet)
```

### Bug Fix
```
Explore (haiku) → Worker (sonnet) → Reviewer (sonnet)
```

### Large-Scale Refactor
```
Explore (haiku) → Workers (sonnet, sequential per module) → Reviewer (sonnet)
```

### Security Audit
```
security-reviewer → Worker (sonnet) → security-reviewer
```
