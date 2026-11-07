"""発走前の通知（--local）が別プロセスで動かす、地方の1レースの予想。

    uv run python tools/発走前の通知/local_predict.py --upset-out <rid>.荒れ具合.json predict <rid> --timing 当日 --format json --out <rid>.json

predict の後ろの引数は ``python -m yosou.local_form_aptitude_top3 predict`` と同じ（rid は省けない）。元DB を1回だけ開き、
その接続で 予想モデルの predict → 推奨買目の荒れ具合の条件に使う券種ごとの中荒れ以上の確率（``UpsetProbabilities``。当日の時点）
の順に出して、予想は ``--out``、確率は ``--upset-out`` に書く。2つの予想は同じ事実表（地方の全成績の一時表。作るのに数分かかる）を使うので、
同じ接続で出すと作るのは1回で済む。荒れ具合の確率が出せなくても予想は失敗にせず、``--upset-out`` に理由を書く
（推奨買目はその券種だけを対象外にして理由を添える）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

import duckdb  # noqa: E402

from 共通 import cli, db  # noqa: E402

from yosou.local_form_aptitude_top3.command.predict_command import PredictCommand  # noqa: E402

from 地方の推奨買目.upset_probabilities import UPSET_BETS, UpsetProbabilities  # noqa: E402

from 発走前の通知.local_upset_file import LocalUpsetFile  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--upset-out", type=Path, required=True, help="券種ごとの中荒れ以上の確率を書くファイル（<rid>.荒れ具合.json）")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="predict")
    PredictCommand().add_parser(subparsers)
    return parser


def main(args: argparse.Namespace) -> None:
    if not args.rid:
        raise ValueError("rid を指定してください")
    upset_file = LocalUpsetFile()
    upset_file.clear(args.upset_out)
    with db.open_db(args.db, default=db.LOCAL) as con:
        cli.emit(PredictCommand().tables(con, args), args)
        _write_upsets(con, args.rid, args.upset_out, upset_file)


def _write_upsets(con: duckdb.DuckDBPyConnection, rid: str, path: Path, upset_file: LocalUpsetFile) -> None:
    """荒れ具合の予想のある券種（単勝・馬連・3連複・3連単）の中荒れ以上の確率。出せなければ理由を書く。"""
    try:
        upset_file.write(path, UpsetProbabilities().of(con, rid, list(UPSET_BETS)))
    except (FileNotFoundError, LookupError, ValueError) as error:
        upset_file.write_reason(path, str(error))
    except Exception as error:  # noqa: BLE001 — 荒れ具合が出せなくても、予想（印と残りの推奨買目）は通知する
        upset_file.write_reason(path, f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    cli.run(build_parser(), main)
