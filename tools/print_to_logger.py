#!/usr/bin/env python3
import ast
import sys
from pathlib import Path

KEYWORDS_LEVEL = {
    "error": "error",
    "exception": "error",
    "fail": "error",
    "warn": "warning",
    "deprecated": "warning",
    "debug": "debug",
}


def guess_level_from_text(text: str) -> str:
    t = text.lower()
    for k, lvl in KEYWORDS_LEVEL.items():
        if k in t:
            return lvl
    return "info"


def fstring_to_printf(joined: ast.JoinedStr):
    # convert f"Hello {x} {y!r}" -> ("Hello %s %r", [x, y])
    fmt_parts = []
    args = []
    for value in joined.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            fmt_parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            # choose %r if !r used, else %s
            conv = "%r" if value.conversion == ord("r") else "%s"
            fmt_parts.append(conv)
            args.append(value.value)
        else:
            # fallback: treat as string segment
            fmt_parts.append("%s")
            args.append(value)
    fmt_str = "".join(fmt_parts)
    return fmt_str, args


def ensure_logger_in_module(module: ast.Module):
    has_import_logging = False
    has_logger_assign = False
    for n in module.body:
        if isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name == "logging":
                    has_import_logging = True
        elif isinstance(n, ast.Assign):
            # logger = logging.getLogger(__name__)
            if (
                len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "logger"
                and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and isinstance(n.value.func.value, ast.Name)
                and n.value.func.value.id == "logging"
                and n.value.func.attr == "getLogger"
            ):
                has_logger_assign = True
    inserts = []
    if not has_import_logging:
        inserts.append(ast.Import(names=[ast.alias(name="logging", asname=None)]))
    if not has_logger_assign:
        get_logger_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="logging", ctx=ast.Load()), attr="getLogger", ctx=ast.Load()
            ),
            args=[ast.Name(id="__name__", ctx=ast.Load())],
            keywords=[],
        )
        inserts.append(
            ast.Assign(targets=[ast.Name(id="logger", ctx=ast.Store())], value=get_logger_call)
        )
    if inserts:
        # insert after future imports and module docstring, if any
        insert_idx = 0
        # skip module docstring
        if (
            module.body
            and isinstance(module.body[0], ast.Expr)
            and isinstance(module.body[0].value, ast.Constant)
            and isinstance(module.body[0].value.value, str)
        ):
            insert_idx = 1
        # skip __future__ imports
        while insert_idx < len(module.body):
            node = module.body[insert_idx]
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                insert_idx += 1
            else:
                break
        module.body[insert_idx:insert_idx] = inserts


class PrintToLoggerTransformer(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        # target only: print(...)
        if not (isinstance(node.func, ast.Name) and node.func.id == "print"):
            return node
        if len(node.args) == 0:
            # print() → logger.info("") (rare)
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="logger", ctx=ast.Load()), attr="info", ctx=ast.Load()
                ),
                args=[ast.Constant(value="")],
                keywords=[],
            )
        first = node.args[0]
        # f-string
        if isinstance(first, ast.JoinedStr):
            fmt, args = fstring_to_printf(first)
            level = guess_level_from_text(fmt)
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="logger", ctx=ast.Load()), attr=level, ctx=ast.Load()
                ),
                args=[ast.Constant(value=fmt)] + args + node.args[1:],  # preserve extra args if any
                keywords=[],
            )
        # simple string literal
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            level = guess_level_from_text(first.value)
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="logger", ctx=ast.Load()), attr=level, ctx=ast.Load()
                ),
                args=[ast.Constant(value=first.value)] + node.args[1:],
                keywords=[],
            )
        # non-string print → default to info with %s
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="logger", ctx=ast.Load()), attr="info", ctx=ast.Load()
            ),
            args=[ast.Constant(value="%s")] + node.args,
            keywords=[],
        )


def transform_file(path: Path):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False, "syntax-error"
    transformer = PrintToLoggerTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    ensure_logger_in_module(new_tree)
    try:
        # Python 3.9+ unparse 대신 더 안전한 방법 사용
        import astor

        new_src = astor.to_source(new_tree)
    except ImportError:
        # astor가 없으면 기본 unparse 사용
        try:
            new_src = ast.unparse(new_tree)  # 3.9+
        except Exception as e:
            return False, f"unparse-failed: {e}"
    except Exception as e:
        return False, f"astor-failed: {e}"
    if new_src != src:
        # keep original as .bak
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            backup.write_text(src, encoding="utf-8")
        path.write_text(new_src, encoding="utf-8")
        return True, "modified"
    return False, "no-change"


def should_skip(file_path: Path) -> bool:
    name = file_path.name
    # skip migrations/tests as needed; adjust to your repo
    return name.endswith(".bak") or name.startswith("._")


def main():
    root = Path("src")
    if not root.exists():
        print("src directory not found", file=sys.stderr)
        sys.exit(1)
    changed = 0
    scanned = 0
    for p in root.rglob("*.py"):
        if should_skip(p):
            continue
        scanned += 1
        ok, msg = transform_file(p)
        if ok:
            changed += 1
        print(f"{p}: {msg}")
    print(f"\nDone. scanned={scanned}, changed={changed}")


if __name__ == "__main__":
    main()
