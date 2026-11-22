"""招待馬を、過去の同じ種類の招待馬の中央での初出走の成績で評価する部品のテスト（合成DB だけを使う）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from 合成DB import synth
from 今週の予想.forecast_columns import INVITED_NOTE, IS_DANGER, MARK, PLACE_VALUE, PROBABILITY, UNRATED, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.invited_rate import InvitedRate
from 今週の予想.invited_rates import SHRINK, InvitedRates
from 今週の予想.mark_rule import MarkRule
from 今週の予想.unrated_rater import UnratedRater

FOREIGN_PAST, FOREIGN_NEW, LOCAL_NEW = "2019190001", "2019190002", "2019190003"


def _runners(day: str, no: str, finishes: dict[int, int], invited: dict[int, tuple[str, str]] | None = None,
             stage: str = "7") -> list[dict[str, str]]:
    """人気 → 着順 の出走。``invited`` は 人気 → （血統登録番号, 東西所属コード）。"""
    race = synth.race(day, no, stage=stage)
    rows = []
    for pop, fin in finishes.items():
        hid, code = (invited or {}).get(pop, (f"2018{pop:06d}", "1"))
        rows.append(synth.runner(race, pop, pop, fin, hid=hid, 東西所属コード=code))
    return rows


@pytest.fixture(scope="module")
def con(tmp_path_factory: pytest.TempPathFactory):
    se = [
        *_runners("20200105", "01", {1: 1, 2: 2, 3: 3, 4: 4}),
        *_runners("20200112", "01", {1: 2, 2: 1, 3: 4, 4: 3}),
        # 外国招待の馬の中央での初出走（3番人気で1着）
        *_runners("20210301", "01", {1: 2, 2: 3, 3: 1, 4: 4}, {3: (FOREIGN_PAST, "4")}),
        # これから走るレースの出馬表（確定前。外国招待と地方招待が1頭ずつ）
        *_runners("20210601", "11", {1: 0, 2: 0, 3: 0}, {1: (FOREIGN_NEW, "4"), 2: (LOCAL_NEW, "3")}, stage="2"),
    ]
    path = synth.build_db(tmp_path_factory.mktemp("invited") / "invited.duckdb", tables={"se": se})
    connection = duckdb.connect(str(path), read_only=True)
    yield connection
    connection.close()


def test_同じ人気の中央の馬の率に_同じ種類の招待馬の倍率を掛ける(con) -> None:
    rates = InvitedRates(con)
    assert rates.kind_of(FOREIGN_NEW) == "外国招待" and rates.kind_of(LOCAL_NEW) == "地方招待" and rates.kind_of("2018000001") is None
    rate = rates.rate(FOREIGN_NEW, 4, "2021-06-01")
    # 2020年の中央の馬: 4番人気は2走で1着0・3着以内1。過去の外国招待の初出走は3番人気（3着以内率 1/2）で1着
    win_factor, top3_factor = (1 + SHRINK) / (0 + SHRINK), (1 + SHRINK) / (0.5 + SHRINK)
    assert rate.kind == "外国招待" and rate.runs == 1
    assert rate.win_factor == pytest.approx(win_factor) and rate.top3_factor == pytest.approx(top3_factor)
    assert rate.win == pytest.approx(0.0) and rate.top3 == pytest.approx(top3_factor / 2)
    # 地方招待には過去の初出走が無いので倍率は 1（同じ人気の中央の馬なみ）。2番人気は2走で1着1・3着以内2
    local = rates.rate(LOCAL_NEW, 2, "2021-06-01")
    assert local.runs == 0 and local.win == pytest.approx(0.5) and local.top3 == pytest.approx(1.0)


def test_そのレースの日より前の成績だけで数える(con) -> None:
    rates = InvitedRates(con)
    # 外国招待の初出走（2021-03-01）の日とそれより前の日なら、数える初出走は無い
    assert rates.rate(FOREIGN_NEW, 4, "2021-03-01").runs == 0
    # 人気ごとの率はその年より前の年だけで数えるので、2020年のレースには基準が無い
    assert rates.rate(FOREIGN_NEW, 4, "2020-12-31") is None
    assert rates.rate(FOREIGN_NEW, float("nan"), "2021-06-01") is None


class _Rates:
    """1番の馬だけを評価する、決まった値の部品。"""

    def rate(self, horse_id: str, popularity: float, race_date: str) -> InvitedRate | None:
        if horse_id != "h1":
            return None
        assert popularity == 2 and race_date == "2021-06-01"
        return InvitedRate(kind="外国招待", win=0.10, top3=0.20, runs=5, win_factor=1.0, top3_factor=0.8)


def _race(odds: list[float]) -> pd.DataFrame:
    table = pd.DataFrame({
        "horse_id": [f"h{i}" for i in range(1, 6)], "horse_no": range(1, 6), "horse_name": [f"馬{i}" for i in range(1, 6)],
        PROBABILITY: [0.40, 0.45, 0.42, 0.35, 0.30], "probability_lightgbm": [0.50, 0.45, 0.42, 0.35, 0.30],
        "win_odds": odds, "market_top3": [0.40, 0.55, 0.45, 0.40, 0.30], PLACE_VALUE: [1.60, 0.9, 0.9, 0.9, 0.9],
        "place_value_lightgbm": [2.00, 0.9, 0.9, 0.9, 0.9], WIN_PROBABILITY: [0.30, 0.25, 0.20, 0.12, 0.09],
        UNRATED: [True, False, False, False, False], IS_DANGER: [True, False, False, False, False],
    })
    table[WIN_VALUE] = table[WIN_PROBABILITY] * table["win_odds"]
    table["win_value_lightgbm"] = table[WIN_VALUE]
    return table


def test_評価できない馬の確率と期待値を置き換えて印の候補に戻す() -> None:
    rated = UnratedRater(_Rates()).rate(_race([4.0, 3.0, 5.0, 8.0, 12.0]), "2021-06-01").set_index("horse_no")
    first = rated.loc[1]
    assert not first[UNRATED] and not first[IS_DANGER] and "外国招待" in first[INVITED_NOTE]
    assert first[PROBABILITY] == pytest.approx(0.20) and first["probability_lightgbm"] == pytest.approx(0.20)
    # 複勝の期待値は、見込みの払戻の倍率をそのままに確率の比で直す（1.60 × 0.20 / 0.40、モデルごとは 2.00 × 0.20 / 0.50）
    assert first[PLACE_VALUE] == pytest.approx(0.80) and first["place_value_lightgbm"] == pytest.approx(0.80)
    assert first[WIN_PROBABILITY] == pytest.approx(0.10) and first[WIN_VALUE] == pytest.approx(0.40)
    assert first["win_value_lightgbm"] == pytest.approx(0.40)
    assert rated.loc[2:, INVITED_NOTE].isna().all() and rated.loc[2, PROBABILITY] == pytest.approx(0.45)
    # 置き換えたあとは印の候補に戻る（消にはならない）。単勝の期待値は下がったので ◎ ではない
    marked = MarkRule().assign(rated.reset_index()).set_index("horse_no")
    assert marked.loc[1, MARK] not in ("◎", "消")


def test_オッズの無い時点は置き換えず評価できない馬のまま() -> None:
    rated = UnratedRater(_Rates()).rate(_race([float("nan")] * 5), "2021-06-01")
    assert rated[UNRATED].iloc[0] and rated[INVITED_NOTE].isna().all()
    assert UnratedRater(None).rate(_race([4.0, 3.0, 5.0, 8.0, 12.0]), "2021-06-01")[UNRATED].iloc[0]
