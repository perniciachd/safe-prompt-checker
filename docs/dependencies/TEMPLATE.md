# Dependency Decision Template

Use this template every time you add a new significant dependency to the project.

**What counts as "significant":** Any package that is part of the production code path (not dev tooling). If unsure, document it. Over-documenting beats under-documenting.

**What does NOT need documentation:** Dev tools (pytest, ruff, mypy), transitive dependencies (things installed because something else needs them), trivial utilities (uuid is in stdlib, requests is well-understood).

## File naming

`docs/dependencies/{package-name}.md`

Examples:
- `docs/dependencies/tenacity.md`
- `docs/dependencies/structlog.md`
- `docs/dependencies/pydantic.md`

## Template

Copy this content into your new file:

```markdown
# {Package Name}

**Version:** {version pinned in requirements.txt}
**Added:** {Sprint N, Week N, Date}
**Used in:** {list of files that import it}

## What problem it solves

One paragraph. Plain English. What was the problem before this package, and what does this package give us?

## Why this package vs alternatives

A short comparison. Don't write a thesis — just the 2-3 alternatives you considered and why you picked this one. Be honest. "Most popular on GitHub" is a valid reason for some packages.

| Option | Pros | Cons | Why not chosen |
|--------|------|------|----------------|
| Option A (chosen) | ... | ... | — |
| Option B | ... | ... | ... |
| Option C | ... | ... | ... |

## How we use it

Concrete examples from THIS codebase. Don't paste the package's tutorial — show how WE use it. Reference specific files.

```python
# Example from src/llm_service.py
from tenacity import retry, stop_after_attempt
# ... actual usage ...
```

## Gotchas and lessons learned

Things that surprised you. Things that don't work the way you'd expect. Add to this section over time as you hit issues.

## When to revisit this choice

What would make us swap this out? Examples:
- "If we need to support synchronous AND async, would consider X"
- "If retries become more complex, may move to Y"

If you can't think of any conditions that would change the choice, that's worth noting too — it means the decision is stable.

## Resources

- Official docs: https://...
- Useful blog post / talk: ...
- Stack Overflow answer that helped: ...
```

## Discipline rules

1. **Write it BEFORE you commit the dependency.** Not "I'll do it later." Later never comes.

2. **Keep it short.** 1-2 pages max. If you're writing more, you're over-documenting.

3. **Update over time.** When you hit a gotcha, add it to that section. When you read a useful article, add it to resources.

4. **Be honest about reasoning.** "Most stars on GitHub" is sometimes the real reason. Write it. Pretending you did rigorous analysis when you didn't makes the doc less trustworthy over time.

5. **Document removals too.** If you remove a dependency, don't delete the file — add a "Removed in Sprint N because..." section. Future you will thank you when you wonder why something isn't there.