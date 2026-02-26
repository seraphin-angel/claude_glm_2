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
| Full application build | "Build me a full-stack app", "Implement 5+ features across 15 files" | **HIERARCHICAL DELEGATE** |

## 4-Tier Delegation Model

### Tier 1: Direct (Score 0-1)
Leader handles it. One-line fixes, config changes, answering questions.

### Tier 2: Lightweight Delegation (Score 2)
No TeamCreate. Spawn a single Task sub-agent (general-purpose, sonnet):
1. Leader reads up to 5 files for context
2. Leader spawns one sub-agent via Task tool with clear description
3. Sub-agent implements, tests, and reports back
4. Leader reports result to user

### Tier 3: Full Team Delegation (Score 3-4)
Full orchestration with TeamCreate:
1. Leader reads up to 5 files for initial orientation
2. TeamCreate to establish the team
3. TaskCreate for all tasks with dependencies (blockedBy)
4. Present task list to user for approval
5. Spawn agents per task following model hierarchy (agent-teams.md)
6. Track via TaskList, report progress after each phase
7. Final verification (1-2 smoke-check commands max)

### Tier 4: Hierarchical Delegation (Score 5+)
CEO spawns a Director (sequential-leader) who takes full ownership of team orchestration:
1. CEO reads up to 5 files for initial orientation only
2. CEO creates the team (TeamCreate)
3. CEO spawns ONE Director agent (sequential-leader, sonnet) with full project brief
4. Director creates all tasks, spawns all workers, tracks progress autonomously
5. CEO monitors via periodic check-ins and Director status reports
6. When Director signals context pressure, CEO executes Director Handoff Protocol
7. CEO delivers final summary to user after Director reports completion

> Fallback: If `sequential-leader` is unavailable, use `general-purpose` + sonnet with Director instructions embedded in the prompt.

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

> **Plan Mode例外**: プランモードでは全エージェントに `model: "opus"` を使用。`rules/agent-teams.md` Plan Mode Override 参照。

### Step 4: Track and Report
- Monitor via TaskList after each agent completes
- Report progress to user in Japanese after each phase
- Handle blockers by adjusting tasks or spawning additional agents

### Step 5: Final Verification
- Review agent reports only (NOT all code line-by-line)
- Run 1-2 smoke-check commands if needed
- Deliver final summary to user

## Delegation Protocol (for Tier 4)

### Step 1: CEO Orientation (max 5 file reads)
- Understand project structure at a high level
- Identify the team name and git branch to use
- Draft the Director's initial mission brief

### Step 2: Create Team and Spawn Director
- TeamCreate with descriptive team name
- Spawn ONE Director agent using Task tool:
  - subagent_type: `sequential-leader`
  - model: `sonnet`
  - team_name: the team name from Step 1
  - Provide: full project goal, tech stack, constraints, and team name
- The Director takes over ALL task creation and agent spawning from this point

### Step 3: CEO Supervision Only
- CEO does NOT create tasks or spawn workers directly
- CEO monitors Director status messages (delivered automatically)
- CEO answers Director questions (clarifications, architectural decisions)
- CEO relays Director's progress updates to the user in Japanese

### Step 4: Director Handoff (when context pressure detected)
Trigger: Director reports context pressure, or CEO observes degraded coordination quality.
1. CEO sends `shutdown_request` to Director, requesting a DIRECTOR HANDOFF SUMMARY
2. Director produces handoff summary (see format below) and approves shutdown
3. CEO reads the handoff summary from the Director's final message
4. CEO spawns a replacement Director with identical mission brief PLUS the handoff summary prepended
5. Replacement Director resumes from the TaskList state described in the handoff

### Step 5: Final Verification
- Director reports completion to CEO
- CEO runs 1-2 smoke-check commands if needed
- CEO delivers final summary to user in Japanese

## Director Handoff Summary Format

The outgoing Director MUST include this structure in its final message to CEO before shutdown:

```
## DIRECTOR HANDOFF SUMMARY

### Project Goal
[One-paragraph description of the overall objective]

### Completed Work
- [Task description]: [what was done, key files affected]

### Current State
[What is implemented and confirmed working as of this handoff]

### Remaining Tasks (priority order)
1. [Task description]: [details, dependencies]
2. ...

### Key Context
- Team name: [team-name]
- Git branch: [branch-name]
- Critical files: [list of most important files]
- Known blockers or issues: [any problems discovered]

### TaskList State
[Paste or summarize current task statuses]
```

The CEO embeds this summary verbatim at the top of the replacement Director's initial prompt.

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

## Context Window Budget (Tier 3)

| Activity | Max Allocation |
|----------|---------------|
| Initial planning exploration | 15% (5 file reads max) |
| Team/task management overhead | 20% |
| Agent result reviews | 30% |
| User communication | 20% |
| Buffer for unexpected needs | 15% |

If you exceed the planning exploration budget, STOP and delegate to an Explore agent.

## Context Window Budget (Tier 4)

| Activity | Max Allocation |
|----------|---------------|
| Initial orientation (5 file reads) | 10% |
| Director mission brief + handoff embeds | 15% |
| Supervision and user communication | 30% |
| Director question responses | 15% |
| Director handoff cycles (per handoff) | 10% |
| Buffer | 20% |

Tier 4 target: CEO context usage stays under 40% even for long-running projects, because all implementation detail is carried by the Director's context, not the CEO's.

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

### Full Application Build / Massive Refactor (Tier 4)
```
CEO (opus):
  └─ Director (sequential-leader, sonnet)
       ├─ Explore agents (haiku) — parallel investigation
       ├─ Worker agents (sonnet) — sequential implementation per module
       └─ Reviewer agents (sonnet) — post-implementation checks

On Director context pressure:
  CEO: shutdown_request → Director: HANDOFF SUMMARY → CEO: spawn replacement Director
```
