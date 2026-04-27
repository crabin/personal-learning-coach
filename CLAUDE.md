# Personal Learning Coach — Claude Instructions

## Coding Standards

Follow **karpathy-guidelines** for all coding work:

1. **Think before coding** — state assumptions explicitly, surface ambiguity, ask when unclear.
2. **Simplicity first** — minimum code that solves the problem. No speculative features, no premature abstractions.
3. **Surgical changes** — touch only what the task requires. Don't improve adjacent code.
4. **Goal-driven execution** — define verifiable success criteria before starting. Loop until verified.

## Project Planning

Use **planning-with-files** for any multi-step task (3+ steps):

- Before starting: create `task_plan.md`, `findings.md`, `progress.md` in the project root.
- Re-read `task_plan.md` before major decisions.
- Update after each phase; log all errors.
- Apply the 2-action rule: after every 2 view/search operations, save key findings to file.
- Never repeat a failed action — mutate the approach.

Planning files live in the project root, NOT in skill directories.

## Code Style

- Files: 200–400 lines, 800 max. Split when larger.
- Functions: < 50 lines.
- Nesting: ≤ 4 levels.
- Type hints on all functions.
- Use `logger`, never `print()`.
- Constants in config, never hardcoded.
- Immutability: return new objects, don't mutate inputs.
- Imports: stdlib → third-party → local.

## Testing

- TDD: write test first (RED), then implementation (GREEN), then refactor.
- Minimum 80% coverage.
- Catch specific exceptions; never bare `except`.

## Security

- No hardcoded secrets. Use environment variables or `.env` (gitignored).
- Validate all external inputs at system boundaries.
- No `eval()`/`exec()` on user input.

## Git Commit Protocol

**Every phase completion requires a git commit.** This is mandatory, not optional.

### When to commit

| Event | Commit required |
|-------|----------------|
| Phase marked `done` in task_plan.md | Yes — immediately |
| Feature implementation complete | Yes |
| All tests passing for a feature | Yes |
| Bug fix verified | Yes |

### Commit message format

```
<type>(<scope>): <description>

Phase <N> complete: <phase name>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Workflow

```
1. Complete phase work
2. Run tests — all must pass
3. Update task_plan.md status → done
4. git add <relevant files>
5. git commit -m "<type>(<scope>): <description>"
6. Continue to next phase
```

Never batch multiple phases into one commit. One phase = one commit.

## Agent Usage

See `AGENTS.md` for the full agent catalog and trigger rules.
