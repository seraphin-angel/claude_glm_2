---
name: pr-review-toolkit
description: Comprehensive PR review toolkit with 6 specialized agents for code quality analysis. Use when reviewing pull requests, checking test coverage, finding silent failures, validating comments/documentation, analyzing type design, simplifying code, or performing general code review. Triggers on requests like "review this PR", "check test coverage", "find error handling issues", "validate my comments", "review the types", or "simplify this code".
---

# PR Review Toolkit

A collection of 6 specialized review agents for comprehensive pull request analysis.

## Agent Selection

| Request Pattern | Agent |
|----------------|-------|
| "Review my code", "Check for bugs" | code-reviewer |
| "Check test coverage", "Are tests thorough?" | pr-test-analyzer |
| "Check error handling", "Find silent failures" | silent-failure-hunter |
| "Validate comments", "Is documentation accurate?" | comment-analyzer |
| "Review the types", "Check type design" | type-design-analyzer |
| "Simplify this code", "Reduce complexity" | code-simplifier |

## Agents Overview

### 1. code-reviewer

Reviews code against project standards (CLAUDE.md), detecting bugs, style violations, and quality issues.

**Scope**: Unstaged changes via `git diff` by default, or user-specified files.

**Confidence threshold**: Only report issues with 80+ confidence score.
- Critical (90-100): Explicit violations, serious bugs
- Important (80-89): Issues requiring attention

**Focus areas**: Import patterns, naming conventions, error handling, null safety, security vulnerabilities, test coverage gaps.

### 2. pr-test-analyzer

Evaluates test coverage quality, focusing on behavioral coverage over line coverage metrics.

**Analysis criteria** (criticality 1-10):
- 9-10: Critical paths causing data loss, security issues, system failures
- 7-8: Important business logic
- 5-6: Edge cases
- 1-4: Optional improvements

**Focus areas**: Critical paths, error handling paths, edge cases, negative test scenarios, test quality (behavioral vs implementation-focused).

### 3. silent-failure-hunter

Identifies silent failures and inadequate error handling.

**Core principles**:
- Zero tolerance for silent failures (errors without logging/user feedback = critical)
- User-centric error messages (clear and actionable)
- Explicit fallback justification required
- Specific catch blocks (avoid broad exception catching)
- No production mocks (test code only)

**Output**: Location, severity, description, hidden error types, user impact, recommendations, corrected code examples.

### 4. comment-analyzer

Reviews documentation for accuracy, completeness, and sustainability.

**Analysis dimensions**:
1. Factual verification - Cross-check against implementation
2. Completeness - Assumptions, side effects, error conditions documented
3. Long-term value - "Why" over "what" explanations
4. Misleading detection - Ambiguous language, outdated references
5. Targeted recommendations - Specific improvements

### 5. type-design-analyzer

Evaluates type designs with ratings (1-10) on four dimensions:

| Dimension | Description |
|-----------|-------------|
| Encapsulation | Internal details hidden, invariants protected |
| Invariant Expression | Constraints clear through structure |
| Invariant Usefulness | Prevents real bugs, aligns with business needs |
| Invariant Enforcement | Validation during construction/mutation |

**Philosophy**: Make illegal states unrepresentable through compile-time guarantees.

### 6. code-simplifier

Enhances clarity, consistency, and maintainability while preserving functionality.

**Principles**:
- Preservation first (never modify behavior)
- Clarity over brevity (explicit > compact)
- Avoid nested ternaries (use switch/if)
- Follow project standards

**Focus areas**: Reduce complexity/nesting, eliminate redundancy, improve naming, consolidate related logic, remove obvious comments.

## Recommended Workflow

1. **After implementing** → code-reviewer
2. **Fix issues** → silent-failure-hunter (if error handling changed)
3. **Add tests** → pr-test-analyzer
4. **Add docs** → comment-analyzer
5. **Final polish** → code-simplifier
6. **Create PR**

## Usage Tips

- Be specific: Target particular agents for focused reviews
- Run proactively: Before PR creation, not after
- Prioritize critical: Agents sort by severity
- Iterate: Re-run after fixes to verify
- Focus scope: Review changed code, not entire codebase
