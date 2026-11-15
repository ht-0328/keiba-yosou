"""オッズの動き（前日の最後の単勝オッズ → 確定の単勝オッズ）で、今の当日の予想の確率を直す（段3）。

    uv run python research/重賞の事例から材料を作る/odds_move.py                 # 元DB（の写し）で前日のオッズを読み、直した予測を書く
    uv run python research/重賞の事例から材料を作る/odds_move.py --save-models   # 2025・2026年の全部で学んだ重みを本番のモデルの置き場所に書く

途中のオッズ（データ区分 1）が DB にあるのは 2025年9月6日から。2025年の確率は 2026年の全レースで、2026年の確率は 2025年の全レースで学んだ直し方で直す
（その年を学びに使わない）。前日のオッズの無い馬と 2024年までの行は、今の予想の確率のまま。
直し方は、今の予想のロジットを出発点にしたロジスティック回帰（材料は オッズの動き・オッズの動き × log(確定オッズ)・前日のオッズがあるか。重みに弱い罰）。
本番と同じ部品（``yosou.shared.odds_move``）で学び、直す。1着の確率は、直したあとにレースの中で合計 1 にそろえる。
出るもの（Git 対象外）: 研究「既存モデルの改善」の ``predictions/graded_race_day/odds_move-top3.pkl``・``odds_move-win.pkl``（今の予想の表と同じ形）。
``--save-models`` は、本番のモデルの置き場所（``reports/近走と適性から3着以内を予想/models``）の ``odds_move.json``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tools"))

from 共通 import db  # noqa: E402

from yosou.shared.odds_move import TARGET_TOP3, TARGET_WIN, OddsMoveFeatures, OddsMoveFitter  # noqa: E402
from yosou.shared.odds_move.odds_move_fitter import logit  # noqa: E402
from yosou.shared.repository import OddsMoveWeightsRepository  # noqa: E402

_OUT = _ROOT / "reports" / "重賞の事例から材料を作る"
_PREDICTIONS = _ROOT / "reports" / "既存モデルの改善" / "predictions" / "graded_race_day"
_PRODUCTION_MODELS = _ROOT / "reports" / "近走と適性から3着以内を予想" / "models"
#: （今の予想, 書く名前, 何着までを当たりにするか, 目的の名前）
_TARGETS = (("general-top3", "odds_move-top3", 3, TARGET_TOP3), ("general-win", "odds_move-win", 1, TARGET_WIN))
_YEARS = (2025, 2026)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save-models", action="store_true", help="2025・2026年の全部で学んだ重みを本番のモデルの置き場所に書く")
    args = parser.parse_args()
    with db.open_db(None) as con:
        eve = _eve_odds(con)
    facts = pd.read_parquet(_OUT / "facts.parquet", columns=["race_id", "horse_id", "horse_no", "surface", "year", "finish", "ran", "win_odds"])
    facts = facts[facts["ran"] & facts["surface"].ne("障害") & facts["year"].isin(_YEARS)]
    facts = facts.merge(eve, on=["race_id", "horse_no"], how="left").astype({"finish": float, "win_odds": float, "eve_odds": float})
    weights = {}
    for source, name, places, target in _TARGETS:
        frame = pd.read_pickle(_PREDICTIONS / f"{source}.pkl")
        rows = _rows(frame, facts, places)
        if args.save_models:
            weights[target] = OddsMoveFitter().fit(OddsMoveFeatures().matrix(rows["win_odds"], rows["eve_odds"]), rows["y"].to_numpy(), rows["p"].to_numpy())
            print(f"{target}: {weights[target].to_dict()}", flush=True)
            continue
        corrected = _correct(frame, rows, target)
        corrected.to_pickle(_PREDICTIONS / f"{name}.pkl")
        print(_PREDICTIONS / f"{name}.pkl")
    if args.save_models:
        print(OddsMoveWeightsRepository(_PRODUCTION_MODELS).save(weights))


def _eve_odds(con) -> pd.DataFrame:
    """レースごとの、開催日より前に発表された最後の途中の単勝オッズ（馬番ごと）。"""
    return con.execute("""
    WITH h AS (
        SELECT 開催年 || 開催月日 || 競馬場コード || "開催回[第N回]" || "開催日目[N日目]" || レース番号 AS race_id, 発表月日時分
        FROM o1 WHERE データ区分 = '1' AND 開催年 >= '2025' AND substr(発表月日時分, 1, 4) < 開催月日
    ), last AS (SELECT race_id, max(発表月日時分) AS t FROM h GROUP BY race_id)
    SELECT l.race_id, TRY_CAST(c.馬番 AS INTEGER) AS horse_no, TRY_CAST(c.オッズ AS INTEGER) / 10.0 AS eve_odds
    FROM last l JOIN "o1__単勝オッズ" c
      ON c.開催年 || c.開催月日 || c.競馬場コード || c."開催回[第N回]" || c."開催日目[N日目]" || c.レース番号 = l.race_id AND c.発表月日時分 = l.t
    """).df()


def _rows(frame: pd.DataFrame, facts: pd.DataFrame, places: int) -> pd.DataFrame:
    """テスト期間の予測に、結果・確定オッズ・前日のオッズを付けた行（2025・2026年。結果か確定オッズの無い行は除く）。"""
    test = frame["期間"].eq("テスト").to_numpy()
    keyed = pd.DataFrame({"race_id": frame["レースID"].astype(str), "horse_id": frame["馬ID"].astype(str), "p": frame["確率"].to_numpy(),
                          "row": np.arange(len(frame))})[test]
    rows = keyed.merge(facts, on=["race_id", "horse_id"]).dropna(subset=["finish", "win_odds"])
    rows["y"] = (rows["finish"] <= places).astype(float)
    return rows


def _correct(frame: pd.DataFrame, rows: pd.DataFrame, target: str) -> pd.DataFrame:
    """その年を抜いて学んだ重みで、その年の行の確率を直す（1着はあとでレースの中で合計 1 にそろえる）。"""
    x = OddsMoveFeatures().matrix(rows["win_odds"], rows["eve_odds"])
    probability = frame["確率"].to_numpy(dtype=float).copy()
    for year in _YEARS:
        held = rows["year"].eq(year).to_numpy()
        w = OddsMoveFitter().fit(x[~held], rows["y"].to_numpy()[~held], rows["p"].to_numpy()[~held])
        raw = logit(rows["p"].to_numpy()[held]) + w.intercept + x[held] @ w.slopes()
        probability[rows["row"].to_numpy()[held]] = 1.0 / (1.0 + np.exp(-raw))
        print(f"{year}年: 重み {w.to_dict()}", flush=True)
    out = frame.copy()
    out["確率"] = probability
    if target == TARGET_WIN:
        changed = out["レースID"].astype(str).str[:4].astype(int).isin(_YEARS) & out["期間"].eq("テスト")
        sums = out[changed].groupby(["区切り", "レースID"])["確率"].transform("sum")
        out.loc[changed, "確率"] = out.loc[changed, "確率"] / sums
    return out


if __name__ == "__main__":
    sys.exit(main())
