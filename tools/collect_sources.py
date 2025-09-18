from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

LANG_MAP = {
    ".py": "python",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".ini": "ini",
    ".txt": "",
}


def detect_lang(path: Path) -> str:
    return LANG_MAP.get(path.suffix.lower(), "")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"<READ_ERROR: {e}>\n"


def make_section(path: Path, content: str) -> str:
    lang = detect_lang(path)
    fence = lang if lang else ""
    heading = f"## {path.as_posix()}\n\n"
    body = f"```{fence}\n{content}\n```\n\n"
    return heading + body


def generate_markdown(paths: Iterable[Path]) -> str:
    parts = ["# ファイル内容スナップショット\n\n"]
    for p in paths:
        parts.append(make_section(p, read_text(p)))
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI引数で与えたファイルを、パス名見出し+コードブロックでMarkdownに列挙します。"
    )
    parser.add_argument("files", nargs="+", help="列挙したいファイルパス（複数可）")
    parser.add_argument("--out", type=Path, default=None, help="出力先Markdown（未指定ならstdout）")
    args = parser.parse_args()

    files = [Path(f).resolve() for f in args.files]
    md = generate_markdown(files)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
