"""ばんえいの予想: 1レースを予想して、印と 3連単の買い目を JSON で出す（発走前の通知が別プロセスで呼ぶ）。

    uv run python tools/ばんえいの予想/predict.py 2026112383170309                # 画面に JSON
    uv run python tools/ばんえいの予想/predict.py 2026112383170309 --out <ファイル>

先に train.py で学習済みモデル（reports/ばんえいの予想/models/）を作っておく。オッズは使わないので、出馬表があれば発走前のいつでも出せる
（馬体重と馬場水分の速報が元DB に入っていれば使う）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import db  # noqa: E402

from ばんえいの予想.banei_forecaster import BaneiForecaster  # noqa: E402
from ばんえいの予想.banei_model import BaneiModel  # noqa: E402
from ばんえいの予想.folders import MODEL_FOLDER  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rid", help="レースの rid（16桁）")
    parser.add_argument("--db", help=db.LOCAL.help())
    parser.add_argument("--models", default=str(MODEL_FOLDER), help="学習済みモデルの置き場所")
    parser.add_argument("--out", help="JSON を書くファイル（無ければ標準出力）")
    args = parser.parse_args()
    forecaster = BaneiForecaster(BaneiModel.load(Path(args.models)))
    with db.open_db(args.db, default=db.LOCAL) as con:
        result = forecaster.forecast(con, args.rid)
    result["made_at"] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
