"""ツールに共通の引数（``--db --format --out --limit`` と絞り込み）と、実行の型。

    from 共通 import cli
    def main(args): ...
    if __name__ == "__main__":
        cli.run(build_parser(...), main)

業務の知識（列名・コード）は持たない。絞り込みの項目は ``filters.FILTER_FIELDS`` から作る。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NoReturn

from . import render
from .filters import FILTER_FIELDS, Filters

#: 利用者に見せて終わる誤り。原因を1行で出して exit 1。
_REPORTED_ERRORS = (FileNotFoundError, LookupError, ValueError, TimeoutError, BlockingIOError)
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


def build_parser(description: str, *, filters: bool = False, limit: int | None = 200,
                 filter_help: dict[str, str] | None = None) -> argparse.ArgumentParser:
    """共通の引数を持つ parser。``filters=True`` で絞り込みのフラグ、``limit`` が None なら ``--limit`` を付けない。

    ``filter_help`` は項目名 → 説明。そのツールで意味が変わるフラグ（事象の ``--finish`` など）の説明を差し替える。
    """
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
    )
    common = parser.add_argument_group("共通")
    common.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    common.add_argument("--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT, help="出力の形式（既定: markdown）")
    common.add_argument("--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）")
    if limit is not None:
        common.add_argument("--limit", type=int, default=limit, help=f"出す行数の上限（既定: {limit}）")
    if filters:
        add_filter_arguments(parser, help_overrides=filter_help)
    return parser


def add_filter_arguments(parser: argparse.ArgumentParser, *, help_overrides: dict[str, str] | None = None) -> None:
    """絞り込みのフラグを足す。フラグ名は ``FILTER_FIELDS`` の項目名と同じ。"""
    group = parser.add_argument_group("絞り込み（省略した条件は効かない。範囲は 1600 か 1400-1800、1400- や -1800 も可）")
    for field in FILTER_FIELDS:
        help_text = (help_overrides or {}).get(field.name, field.help)
        group.add_argument(f"--{field.name}", dest=f"filter_{field.name}", metavar=field.example, help=help_text)


def filter_value(args: argparse.Namespace, name: str) -> str | None:
    """絞り込みのフラグの生の値。"""
    return getattr(args, f"filter_{name}", None)


def filters_from(args: argparse.Namespace, *, exclude: Sequence[str] = ()) -> Filters:
    """引数から絞り込みを作る。``exclude`` の項目は使わない（ツールが別の意味で受け取るとき）。"""
    values = {field.name: filter_value(args, field.name) for field in FILTER_FIELDS if field.name not in exclude}
    return Filters.from_mapping(values)


def emit(result: render.Table | Sequence[render.Table], args: argparse.Namespace) -> None:
    """結果を ``--format`` の形で ``--out`` か標準出力へ。"""
    render.write(render.render(result, args.format), args.out, fmt=args.format)


def run(parser: argparse.ArgumentParser, main: Callable[[argparse.Namespace], None],
        argv: Sequence[str] | None = None) -> NoReturn:
    """引数（``argv``。省略するとコマンドラインの引数）を読んで ``main`` を実行する。誤りは1行で見せ、成功なら 0 で終わる。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parser.parse_args(argv)
    try:
        main(args)
    except _REPORTED_ERRORS as error:
        print(f"エラー: {error}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR)
    except KeyboardInterrupt:
        raise SystemExit(EXIT_INTERRUPTED)
    raise SystemExit(0)
