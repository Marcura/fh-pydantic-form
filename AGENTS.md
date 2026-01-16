we use uv for python package management. Run command with uv run
we use ty for type checking
we use prek for pre-commit

## FastHTML typing footguns to avoid

- Avoid returning multiple sibling nodes from functions annotated as `FT` (e.g. `return (a, b)`). Prefer `fh.Div(a, b)` (use `cls="contents"` if you need wrapper-less layout).
- Prefer fixing runtime return values over widening FastHTML return annotations (e.g. avoid `FT | tuple[FT, ...]` unless necessary).
- Keep typing-only imports under `if TYPE_CHECKING:` when they introduce circular imports or runtime overhead.
- Renderer `value` can be `None`/unknown (schema drift, optional fields). Don’t assume it’s a dict (e.g. guard before calling `.get`).
