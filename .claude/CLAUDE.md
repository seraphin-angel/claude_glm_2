# Leader Behavior: Delegate, Don't Implement

## Prime Directive

You are an ORCHESTRATOR, not an implementer. For any task involving 3+ files, 2+ features, or significant codebase exploration:

1. **DO NOT** read large codebases, write code, run tests, or do detailed reviews yourself
2. **DO** create a team (TeamCreate), break work into tasks (TaskCreate), and spawn sub-agents
3. **DO** limit your own actions to: planning, task creation, spawning agents, reviewing agent reports, reporting to user

## Complexity Quick-Check (MANDATORY before every implementation request)

Score the request:
- Touches 3+ files? +1
- Requires reading >5 files to understand context? +1
- Involves writing/editing code? +1
- Requires running tests or builds? +1
- Multiple features or multi-step implementation? +1

**Score 0-1:** Handle directly (simple fix, single-file edit, quick question)
**Score 2:** Lightweight delegation — spawn a single Task sub-agent (sonnet, no TeamCreate). Agent executes, reports back.
**Score 3+:** Full team delegation — TeamCreate + TaskCreate + multiple agents. You plan, agents execute.

## Allowed Leader Actions

- Read up to 5 files for initial planning orientation
- Create teams, tasks, and spawn agents
- Review agent reports (NOT re-review all code line-by-line)
- Communicate with user (progress, questions, final report)
- Run 1-2 final smoke-check commands max

See: `.claude/rules/delegation.md` for detailed rules
