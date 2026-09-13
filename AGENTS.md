# Repository instructions

## Branch naming

Use a branch prefix that reflects the type of work:

- `feature/` for new functionality
- `fix/` for bug fixes
- `hotfix/` for urgent production fixes
- `chore/` for maintenance and tooling
- `refactor/` for code restructuring without behavior changes
- `docs/` for documentation changes
- `test/` for test-only changes

Use the format:

```text
<type>/<scope>-<short-description>
```

Examples:

```text
fix/weightxreps-exercise-resolution
feature/multi-activity-sync
docs/update-readme
```

This convention applies to branch names only; it does not require adopting the full Gitflow workflow.

## graphify

This project uses a code-only knowledge graph at graphify-out/ when it has been generated. The graph must be built from source code with deterministic AST extraction only.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- Graphify is restricted to deterministic code analysis in this project. Always use `graphify extract . --code-only`; never run `graphify .`, `graphify extract .` without `--code-only`, or any semantic backend.
- To build a clustered graph without LLM-generated labels, run `graphify extract . --code-only --no-cluster` followed by `graphify cluster-only . --no-label`. Visualization is allowed and should be generated when useful.
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After a coherent batch of code changes passes its tests, run `graphify update .` only when every changed file is code; Graphify then skips semantic extraction. Do not run it when the batch includes Markdown, specs, images, or other non-code files.
