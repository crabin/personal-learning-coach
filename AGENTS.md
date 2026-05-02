# Personal Learning Coach — Agent Instructions

All agents inherit the coding standards in `CLAUDE.md`.

## Agent Catalog

| Agent | Trigger |
|-------|---------|
| `dev-planner` | Complex feature, multi-step refactor — plan before coding |
| `architect` | Architectural decision, new module design |
| `tdd-guide` | Any new feature or bug fix — write tests first |
| `code-reviewer` | Immediately after writing or modifying code |
| `bug-analyzer` | Debugging complex issues across multiple files |
| `build-error-resolver` | Build or type errors |
| `refactor-cleaner` | Dead code removal, consolidation |
| `security-reviewer` | Before any commit touching auth, secrets, or user input |

## Automatic Invocation (no user prompt needed)

- Code written/modified → **code-reviewer**
- Build fails → **build-error-resolver**
- Complex feature requested → **dev-planner** then **architect**
- Bug reported → **bug-analyzer**
- New feature with tests → **tdd-guide**

## Parallel Execution

Run independent agents in parallel — never sequentially when tasks don't depend on each other.

```
# GOOD
Launch in parallel:
  Agent 1: code-reviewer on module A
  Agent 2: tdd-guide scaffolding tests for module B

# BAD
Run agent 1, wait, then run agent 2
```

## Planning Integration

Before delegating complex work, ensure `task_plan.md` exists (see `CLAUDE.md` → planning-with-files).
Agents should read the plan file at session start to restore context.


<claude-mem-context>
# Memory Context

# [personal-learning-coach] recent context, 2026-05-02 5:06pm GMT+9

No previous sessions found.
</claude-mem-context>