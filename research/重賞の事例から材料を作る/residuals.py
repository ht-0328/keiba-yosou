"""事例から考えた理由の候補ごとに、重賞（2015〜2022年）で予想の確率より実際に来たか（ずれ）を数える（段1の確かめ）。

    uv run python research/重賞の事例から材料を作る/residuals.py    # reports/重賞の事例から材料を作る/ずれ.md に書く

ずれ = 実際の3着以内率 ÷ 予想の3着以内の確率の平均。1 より大きければ、予想がその馬たちを低く見ている。
複勝の回収率も並べる（市場もその理由を見落としているか）。DB は開かない（facts.parquet と予測の表を読む）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import _OUT, _predictions  # noqa: E402

#: 格の段（大きいほど上）。
_STEP_SQL = """CASE WHEN {g} = 'A' THEN 6 WHEN {g} = 'B' THEN 5 WHEN {g} IN ('C', 'D') THEN 4 WHEN {g} = 'L' THEN 3
                    WHEN {c} = 'オープン' THEN 3 ELSE 2 END"""


def main() -> None:
    rows = _rows()
    lines = ["# 理由の候補ごとのずれ（重賞・2015〜2022年）", "",
             "ずれ = 実際の3着以内率 ÷ 予想の確率の平均（1 より大きいほど予想が低く見ている）。複勝の回収率は 100円あたり。", ""]
    for title, column in _CANDIDATES:
        lines += _table(rows, title, column)
    out = _OUT / "ずれ.md"
    out.write_bytes("\n".join(lines).encode("utf-8"))
    print("\n".join(lines))


def _rows() -> pd.DataFrame:
    con = duckdb.connect()
    con.register("pred", _predictions())
    facts = (_OUT / "facts.parquet").as_posix()
    frame = con.execute(f"""
    WITH f AS (SELECT * FROM read_parquet('{facts}') WHERE ran),
    h AS (
        SELECT f.*, {_STEP_SQL.format(g='grade_code', c='class_name')} AS step,
               lag({_STEP_SQL.format(g='grade_code', c='class_name')}) OVER w AS prev_step,
               lag(carried) OVER w AS prev_carried
        FROM f WINDOW w AS (PARTITION BY horse_id ORDER BY race_date, race_id)
    ),
    g AS (SELECT h.*, p.p FROM h JOIN pred p USING (race_id, horse_id)
          WHERE grade_code IN ('A', 'B', 'C') AND surface <> '障害' AND year BETWEEN 2015 AND 2022),
    meet AS (  -- 今回の出走馬どうしの、それより前の対戦（同じレースに出た回）
        SELECT a.race_id, a.horse_id, count(*) AS meetings,
               avg(CASE WHEN pa.finish < pb.finish THEN 1.0 ELSE 0.0 END) AS ahead_share
        FROM g a JOIN g b ON a.race_id = b.race_id AND a.horse_id <> b.horse_id
        JOIN f pa ON pa.horse_id = a.horse_id AND pa.race_date < a.race_date
        JOIN f pb ON pb.horse_id = b.horse_id AND pb.race_id = pa.race_id
        GROUP BY a.race_id, a.horse_id
    )
    SELECT g.*, m.meetings, m.ahead_share FROM g LEFT JOIN meet m USING (race_id, horse_id)
    """).df()
    numeric = ["step", "prev_step", "prev_finish", "prev_popularity", "carried", "prev_carried", "age", "interval_days", "meetings", "ahead_share", "prev_last3f_rank", "finish", "place_payout", "p"]
    return _derive(frame.astype({c: float for c in numeric}))


def _derive(frame: pd.DataFrame) -> pd.DataFrame:
    move = np.sign(frame["step"] - frame["prev_step"].fillna(frame["step"]))
    prev = frame["prev_finish"]
    prev_bin = np.select([prev.le(1), prev.le(3), prev.le(9)], ["前走1着", "前走2〜3着", "前走4〜9着"], "前走10着以下")
    upset = frame["prev_finish"] - frame["prev_popularity"]
    carried = frame["carried"] - frame["prev_carried"]
    young = frame["age"].eq(3) & frame["mixed_age"].fillna(False).astype(bool)
    return frame.assign(
        格の上下と前走の着順=pd.Series(np.select([move > 0, move < 0], ["格上げ", "格下げ"], "同じ格"), index=frame.index) + "・" + prev_bin,
        前走の人気と着順=np.select([upset.le(-3), upset.ge(5), upset.ge(1)], ["人気より3つ以上上", "人気より5つ以上下", "人気より1〜4下"], "人気どおり"),
        間隔=pd.cut(frame["interval_days"], [0, 20, 35, 63, 120, 9999], labels=["〜20日", "21〜35日", "36〜63日", "64〜120日", "121日〜"]).astype(str),
        乗り替わり=frame["jockey_change"].astype(str),
        斤量の増減=np.select([carried.le(-2), carried.ge(2)], ["2kg以上減", "2kg以上増"], "ほぼ同じ"),
        年齢=np.where(young, "3歳（古馬と）", frame["age"].clip(upper=7).astype(str) + "歳"),
        対戦の数=pd.cut(frame["meetings"].fillna(0), [-1, 0, 3, 10, 9999], labels=["対戦なし", "1〜3", "4〜10", "11〜"]).astype(str),
        対戦で先着した割合=pd.cut(frame["ahead_share"], [-0.01, 0.25, 0.5, 0.75, 1.0], labels=["〜25%", "26〜50%", "51〜75%", "76〜100%"]).astype(str),
        前走の上がり順位=np.select([frame["prev_last3f_rank"].eq(1), frame["prev_last3f_rank"].le(3)], ["1位", "2〜3位"], "4位以下・不明"),
        place=np.where(frame["finish"].le(3), frame["place_payout"], 0),
        top3=frame["finish"].le(3).astype(float),
    )


_CANDIDATES = (
    ("格の上下と前走の着順", "格の上下と前走の着順"),
    ("前走の人気と着順", "前走の人気と着順"),
    ("前走からの間隔", "間隔"),
    ("騎手の乗り替わり", "乗り替わり"),
    ("斤量の増減", "斤量の増減"),
    ("年齢", "年齢"),
    ("今回の出走馬との対戦の数", "対戦の数"),
    ("今回の出走馬との対戦で先着した割合", "対戦で先着した割合"),
    ("前走の上がり3Fの順位", "前走の上がり順位"),
)


def _table(rows: pd.DataFrame, title: str, column: str) -> list[str]:
    lines = [f"## {title}", "", "| 区分 | 頭数 | 3着以内率 | 予想の確率 | ずれ | 複勝の回収率 |", "|---|---|---|---|---|---|"]
    for key, group in rows.groupby(column):
        if len(group) < 100:
            continue
        actual, predicted = group["top3"].mean(), group["p"].mean()
        lines.append(f"| {key} | {len(group):,} | {actual:.3f} | {predicted:.3f} | {actual / predicted:.2f} | {group['place'].mean():.0f}% |")
    return lines + [""]


if __name__ == "__main__":
    sys.exit(main())
