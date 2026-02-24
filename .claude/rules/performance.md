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

| Action | Leader Context Cost | Delegated Cost |
|--------|-------------------|----------------|
| Read 20 files | ~40% | 0% (Explore agent) |
| Write implementation | ~30% | 0% (Worker agent) |
| Run and debug tests | ~20% | 0% (Reviewer agent) |
| Detailed code review | ~15% | 0% (Reviewer agent) |

By delegating, leader context usage drops from ~100% to ~35% (planning + coordination + result review), leaving room for managing multi-phase projects without context exhaustion.

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix
