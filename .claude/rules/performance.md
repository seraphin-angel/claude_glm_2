# Performance Optimization

## Model Selection Strategy

**Haiku 4.5** (90% of Sonnet capability, 3x cost savings):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet 4.5** (Best coding model):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus 4.5** (Deepest reasoning):
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Ultrathink + Plan Mode

For complex tasks requiring deep reasoning:
1. Use `ultrathink` for enhanced thinking
2. Enable **Plan Mode** for structured approach
3. "Rev the engine" with multiple critique rounds
4. Use split role sub-agents for diverse analysis

## Delegation as Context-Saving Strategy

The most effective way to conserve the leader's context window is delegation:

| Action | Leader Context Cost | Tier 3 Delegated | Tier 4 Delegated |
|--------|-------------------|-----------------|-----------------|
| Read 20 files | ~40% | 0% (Explore agent) | 0% (via Director) |
| Write implementation | ~30% | 0% (Worker agent) | 0% (via Director) |
| Run and debug tests | ~20% | 0% (Reviewer agent) | 0% (via Director) |
| Detailed code review | ~15% | 0% (Reviewer agent) | 0% (via Director) |
| Task creation & tracking | ~10% | 10% (CEO creates) | 0% (Director creates) |
| Multi-phase coordination | ~20% | 20% (CEO tracks) | 0% (Director tracks) |

**Tier 3 result**: CEO context usage ~35% (planning + coordination + result review).

**Tier 4 result**: CEO context usage ~15% (orientation + Director brief + supervision). The Director absorbs all implementation detail, and can be replaced via handoff when context fills. This enables projects spanning many tasks without ever exhausting the CEO's context.

### Director Handoff as Infinite Context

Each Director instance has a finite context window. When it approaches exhaustion:
- Outgoing Director: writes DIRECTOR HANDOFF SUMMARY, shuts down cleanly
- Incoming Director: starts fresh with the summary as its entire prior context
- CEO: accumulates only summaries (small), never raw implementation detail

This means Tier 4 projects have theoretically unlimited scale — the CEO's context cost per handoff cycle is approximately 2-5% (reading one handoff summary). See `rules/delegation.md` for the Director Handoff Summary Format.

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix
