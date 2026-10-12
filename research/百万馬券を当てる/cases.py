"""手順1・5: 帯のレースと、荒れたレースで来た人気薄の事例を集める（研究「百万馬券を当てる」の入口①）。

    uv run python research/百万馬券を当てる/cases.py races    # 手順1: 帯のレースの事例と、切り口ごとの帯の集まり方
    uv run python research/百万馬券を当てる/cases.py horses   # 手順5: 荒れたレースで来た人気薄と来なかった人気薄

理論を作る年（2020年まで）だけを見る。確かめに使う 2021年以降は見ない。
先にレース単位の表を作っておく（README の「動かし方」）。馬ごとの表は、研究「既存モデルの改善」の表（当日の3着以内の今の本番のもの）を読む。
出力は ``reports/百万馬券を当てる/事例-レース選び.md``・``事例-来る馬.md``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 複勝以外の回収率100超.analysis.retrain_targets import retrain_target_named  # noqa: E402
from 百万馬券を当てる.analysis.horse_case_report import LIFT_COLUMNS as HORSE_COLUMNS  # noqa: E402
from 百万馬券を当てる.analysis.horse_case_report import HorseCaseReport  # noqa: E402
from 百万馬券を当てる.analysis.horse_frame import horse_frame  # noqa: E402
from 百万馬券を当てる.analysis.obi_rules import THEORY_LAST_YEAR  # noqa: E402
from 百万馬券を当てる.analysis.race_case_report import RaceCaseReport  # noqa: E402
from 百万馬券を当てる.analysis.race_frame import YEAR, race_frame  # noqa: E402
from 百万馬券を当てる.analysis.race_table_loader import RaceTableLoader  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_OUT = _REPORTS / "百万馬券を当てる"
#: レース単位の表の置き場所（この研究が作ったもの）と、馬ごとの表の置き場所（研究「既存モデルの改善」が作ったもの）。
DEFAULT_RACE_TABLES = DEFAULT_OUT / "tables"
DEFAULT_HORSE_TABLES = _REPORTS / "既存モデルの改善" / "tables"
#: 馬ごとの事例に使う表（当日の3着以内の今の本番の表と列）。
HORSE_TARGET = "当日・3着以内"


def main() -> None:
    args = _parser().parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    races = race_frame(RaceTableLoader(args.race_tables).read())
    races = races[races[YEAR].le(THEORY_LAST_YEAR)]
    {"races": _races, "horses": _horses}[args.step](args, races)


def _races(args: argparse.Namespace, races) -> None:
    first, last = int(races[YEAR].min()), int(races[YEAR].max())
    lines = [f"# 帯のレースの事例（{first}〜{last}年）", "",
             "帯 = 3連単の払戻が 100万円以上、大荒れ = 10万〜100万円。集まり方 = その値の帯の割合 ÷ 全レースの帯の割合。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    lines += RaceCaseReport().lines(races)
    _write(args.out / "事例-レース選び.md", lines)


def _horses(args: argparse.Namespace, races) -> None:
    target = retrain_target_named(HORSE_TARGET)
    print(f"馬ごとの表 {target.variant.model} を読んでいます …", flush=True)
    data = TableStore(args.horse_tables).read(target.variant.model, target.catalog)
    columns = sorted({column for group in HORSE_COLUMNS.values() for column in group} & set(data.features.columns))
    horses = horse_frame(data, columns, races)
    first, last = int(horses[YEAR].min()), int(horses[YEAR].max())
    lines = [f"# 荒れたレースで来た人気薄の事例（{first}〜{last}年）", "",
             "人気薄 = 確定の単勝6番人気以下。荒れたレース = 3連単の払戻が 10万円以上。",
             "集まり方 = その値の人気薄の3着以内率 ÷ 同じレースの群れの人気薄全体の3着以内率。集まり方の差 = 荒れたレースの集まり方 − それ以外のレースの集まり方。",
             "JV-Data 由来の値を含むため Git の対象外。", ""]
    lines += HorseCaseReport().lines(horses)
    _write(args.out / "事例-来る馬.md", lines)


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="帯のレースと、荒れたレースで来た人気薄の事例を集める", allow_abbrev=False)
    parser.add_argument("step", choices=("races", "horses"), help="races（手順1）・horses（手順5）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="出力の置き場所")
    parser.add_argument("--race-tables", type=Path, default=DEFAULT_RACE_TABLES, help="レース単位の表の置き場所")
    parser.add_argument("--horse-tables", type=Path, default=DEFAULT_HORSE_TABLES, help="馬ごとの表の置き場所")
    return parser


if __name__ == "__main__":
    main()
