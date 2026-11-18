# Diagrams

One `.mmd` per design doc, named by its prefix; each obeys the `use-mmd` discipline (names on nodes,
meaning on edges, status by color, legend as swatches). The owning doc carries the rules — diagrams
render existence only.

| Diagram | Belongs to |
|---|---|
| `lifecycle-flow.mmd` | `../regime/lifecycle.md` |
| `init-flow.mmd` | `../commands/init.md` |
| `memory-flow.mmd` | `../regime/memory.md` |
| `supervision-flow.mmd` | `../regime/supervision.md` |
| `compact-flow.mmd` | `../commands/compact.md` |
| `flow-flow.mmd` | `../commands/flow.md` |
| `router-fit.mmd` | `../regime/router.md` (section 13) |
| `vinit-fresh.mmd` | the imagined `/viber init` run on a fresh project — peer page `vinit-fresh.html` renders it with Pele |

Update this table in the same change that adds, removes or renames a diagram.

To draw any `.mmd` here as a themed SVG (no browser, no install — Pele fetched from the CDN):
`bun tools/pele-render/render.mjs --all` → `artifacts/pele/`.