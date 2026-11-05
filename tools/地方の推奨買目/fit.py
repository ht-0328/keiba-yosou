"""地方の推奨買目: 1着・2着・3着の条件つきロジットの係数を当てはめて保存する（1回だけ。全頭の予想のモデルを学び直したらやり直す）。

    uv run python tools/地方の推奨買目/fit.py                       # 2024-01-01 以降の 11頭以上のレースで当てはめ、reports/地方の推奨買目/係数.json に書く（10〜20分）
    uv run python tools/地方の推奨買目/fit.py --from 2025-01-01      # 対象の最初の開催日を変える

材料は、事実表の出走の行（確定着順・単勝オッズ）、全頭の予想の当日の予測の表（backtest が書いた pkl。既定は 2024検証）、
3連単・馬単・3連複・複勝の確定オッズ。評価（年ごとの未見の成績）は研究「地方の万馬券」の positions.py で、ここは本番用に全部の年で当てはめるだけ。
係数の表は同じ場所の 係数.md にも書く。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 地方の推奨買目.coefficient_store import DEFAULT_PATH, CoefficientStore  # noqa: E402
from 地方の推奨買目.fit_flow import CoefficientFit, FitSettings  # noqa: E402

_PROJECT = _TOOLS.parent
DEFAULT_PREDICTIONS = _PROJECT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"


def main(args: argparse.Namespace) -> None:
    settings = FitSettings(date_from=args.date_from, predictions=args.predictions, min_heads=args.min_heads)
    with db.open_db(args.db, default=db.LOCAL) as con:
        coefficients, meta = CoefficientFit(con, settings).run()
    store = CoefficientStore(args.out)
    path = store.save(coefficients, meta)
    table = Table.from_records(coefficients.rows(f"{'・'.join(str(y) for y in meta['年'])}年"), ("当てはめ", "着", "特徴量", "係数"),
                               title="地方の推奨買目: 1着・2着・3着の条件つきロジットの係数",
                               note=f"対象 {meta['対象の最初の開催日']} 以降・{meta['最少の頭数']}頭以上・{meta['レース数']:,} レース。当てはめた日 {meta['当てはめた日']}。")
    markdown = path.with_suffix(".md")
    render.write(render.render(table, "markdown"), markdown, fmt="markdown")
    print(f"書きました: {path}（表は {markdown}）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help=f"全頭の予想の当日の予測の表の置き場所（既定: {DEFAULT_PREDICTIONS}）")
    parser.add_argument("--min-heads", type=int, default=11, help="対象にする最少の頭数（既定: 11）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--out", type=Path, default=DEFAULT_PATH, help=f"係数を書く JSON（既定: {DEFAULT_PATH}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
