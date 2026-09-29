"""券種オッズの材料は、締め切り前のオッズでも◎を良くするかを、過去1年のレースで確かめる（研究「一番人気を疑う」の入口④）。

    uv run --with pyarrow --with tabulate python research/一番人気を疑う/pre_deadline_check.py

オッズを使う予想（今の予想の当日版の材料）に、券種ごとのオッズから見た支持を足すと、◎が1番人気より多く3着以内に
来た（研究「既存モデルの改善」の材料の実験）。ただし、それは確定オッズで確かめたもの。ここでは、2025年8月までの
確定オッズで学習したモデルに、2025年9月〜2026年9月の締め切り前の断面（発走の11分前・6分前）で作り直した材料を渡す。
締め切り前の断面が過去にあるのは単勝・複勝・馬連だけなので、比べるのは次の3つ。

- A: 単勝オッズだけ（今の予想の当日版と同じ材料）
- B: A ＋ 馬連と複勝の支持
- C: A ＋ 6券種の支持（3連単などは締め切り前の値が無いので、確定オッズの断面の行だけで見る）

先に研究「既存モデルの改善」の表と、元DB に締め切り前の断面（jvdata-store の ``jvstore timeseries``・``merge-odds``）が要る。
出力は ``reports/一番人気を疑う/締め切り前での確かめ.md``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402
from 回収率100超.analysis.repository import PreDeadlineQuinellaRepository, PreDeadlineWinPlaceRepository  # noqa: E402
from 既存モデルの改善.analysis.windows import TestWindow  # noqa: E402

from 一番人気を疑う.analysis.feature import PreDeadlineOddsFeatures  # noqa: E402
from 一番人気を疑う.analysis.feature.pre_deadline_odds_features import PLACE_RATIO, QUINELLA_RATIO  # noqa: E402
from 一番人気を疑う.analysis.model import LightGBMWindowModel, WindowSplit  # noqa: E402
from 一番人気を疑う.analysis.source import FormTableSource  # noqa: E402

DEFAULT_TABLES = Path("reports/既存モデルの改善/tables")
DEFAULT_OUT = Path("reports/一番人気を疑う/締め切り前での確かめ.md")
#: 学習は検証の始まりの前日まで、検証（木の数を決める）は 2025年7〜8月、確かめるのは締め切り前の断面がある1年。
WINDOW = TestWindow("過去1年", date(2025, 7, 1), date(2025, 9, 1), date(2026, 9, 27))
#: 何分前までに発表された断面を使うか（断面は発走の11分前・6分前・1分前にある。1分前は、発売の締め切り（発走の
#: 2分前とされる）の後の集計である見込みが高く、買う時点には見えないので使わない）。
MINUTES: tuple[int, ...] = (10, 5)


def main() -> None:
    parser = argparse.ArgumentParser(description="券種オッズの材料を締め切り前のオッズで確かめる", allow_abbrev=False)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    frame = FormTableSource(args.tables).read()
    odds = FormTableSource.columns("base") + FormTableSource.columns("odds")
    sets = {"A: 単勝オッズだけ": odds, "B: ＋馬連と複勝の支持": odds + [QUINELLA_RATIO, PLACE_RATIO],
            "C: ＋6券種の支持": odds + FormTableSource.columns("pool")}
    split = WindowSplit(WINDOW)
    models = {name: (LightGBMWindowModel().fit(frame, columns, split), columns) for name, columns in sets.items()}
    snapshots = {"確定オッズ": split.test(frame).reset_index(drop=True)}
    with db.open_db(args.db) as connection:
        for minutes in MINUTES:
            win_place = PreDeadlineWinPlaceRepository(connection, WINDOW.test_first_day, WINDOW.test_last_day, minutes).read()
            quinella = PreDeadlineQuinellaRepository(connection, WINDOW.test_first_day, WINDOW.test_last_day, minutes).read()
            snapshots[f"発走の{minutes + 1}分前"] = PreDeadlineOddsFeatures().rebuild(snapshots["確定オッズ"], win_place, quinella)
    common = set.intersection(*(set(rows["レースID"]) for rows in snapshots.values()))
    rows = [_row(snapshot, name, model, columns, table[table["レースID"].isin(common)])
            for snapshot, table in snapshots.items() for name, (model, columns) in models.items()
            if snapshot == "確定オッズ" or not name.startswith("C")]
    period = (f"学習は {WINDOW.valid_first_day} より前の確定オッズ。確かめるのは {WINDOW.test_first_day}〜"
              f"{WINDOW.test_last_day} の、すべての断面がそろう {len(common):,} レース。")
    lines = ["# 一番人気を疑う — 締め切り前での確かめ", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             period, "", pd.DataFrame(rows).to_markdown(index=False), "",
             "「その時点の1番人気」は、その断面の単勝オッズがいちばん低い馬。C は締め切り前の3連単などが無いので、確定オッズの行だけ。", ""]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {args.out}", flush=True)


def _row(snapshot: str, name: str, model, columns: list[str], table: pd.DataFrame) -> dict[str, object]:
    scored = table.assign(score=model.predict_proba(table[columns])[:, 1])
    top = scored.loc[scored.groupby("レースID")["score"].idxmax()]
    now = scored.loc[scored.groupby("レースID")["単勝オッズ"].idxmin()]
    final = scored[scored["確定の単勝人気"] == 1].sort_values("馬番").drop_duplicates("レースID")
    return {"オッズの断面": snapshot, "材料": name, "レース": len(top), "◎の3着以内率": round(top["3着以内"].mean(), 4),
            "その時点の1番人気": round(now["3着以内"].mean(), 4), "確定の1番人気": round(final["3着以内"].mean(), 4)}


if __name__ == "__main__":
    main()
