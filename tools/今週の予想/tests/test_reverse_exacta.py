"""馬単の裏まで買うかを決める部品（``HarvilleReverse``・``ReverseExactaFeatures``・``ReverseExactaModel``・``ReverseExactaJudge``）と、
印の買い目・説明の文への足し方のテスト。値は架空。"""

from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 今週の予想.harville_reverse import HarvilleReverse
from 今週の予想.mark_tickets import RULE, MarkTickets
from 今週の予想.race_describer import RaceDescriber
from 今週の予想.reverse_exacta_features import FEATURES, ReverseExactaFeatures
from 今週の予想.reverse_exacta_judge import FOLDER, LINE, ReverseExactaJudge
from 今週の予想.reverse_exacta_model import MANIFEST_FILE, ReverseExactaModel
from 今週の予想.ticket_rules import REVERSE_EXACTA_RULE

#: 8頭のレースの印。◎3・○1・▲5・△2,4,6・☆8・消7。
_MARKS = {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "△", 6: "△", 8: "☆", 7: "消"}


def _race(star_value: float = 1.40, reverse: bool | None = None) -> pd.DataFrame:
    """☆ の複勝の期待値は ``star_value``（1.25 以上なら裏の相手に入る）。"""
    order = sorted(_MARKS)
    race = pd.DataFrame({
        "race_id": "R", "race_date": pd.Timestamp("2025-01-05"), "fold": "", "win_value_band": "1.00 以上",
        "horse_no": order, "mark": [_MARKS[no] for no in order], "place_value": [star_value if no == 8 else 1.0 for no in order],
        "probability": [0.6 if no == 3 else 0.3 for no in order], "market_top3": 0.375,
        "win_probability": [0.25 if no == 3 else 0.75 / 7 for no in order], "market_win": 0.125,
        "win_odds": [3.0 if no == 3 else 8.0 for no in order], "win_value": [0.75 if no == 3 else 0.86 for no in order],
        "popularity": [1 if no == 3 else 2 for no in order],
    })
    return race if reverse is None else race.assign(reverse_exacta=reverse)


def _brute_force(win: list[float], top: int, partners: list[int]) -> float:
    """全部の着順（1〜3着）を数え上げて、1着が相手で ``top`` が2着か3着になる確率を出す（Harville）。"""
    total = 0.0
    for first, second, third in permutations(range(len(win)), 3):
        if first not in partners or top not in (second, third):
            continue
        rest = 1 - win[first]
        total += win[first] * win[second] / rest * win[third] / (rest - win[second])
    return total


def test_Harville_の裏の確率は全部の着順を数え上げたものと同じ() -> None:
    win = [0.4, 0.3, 0.2, 0.1]
    assert HarvilleReverse().of(np.array(win), 0, [1, 2]) == pytest.approx(_brute_force(win, 0, [1, 2]))
    # 合計が 1 でなくてもそろえてから出す
    assert HarvilleReverse().of(np.array(win) * 2, 0, [1, 2]) == pytest.approx(_brute_force(win, 0, [1, 2]))


def test_材料の相手は対抗と単穴と線以上の星() -> None:
    row = ReverseExactaFeatures().of(_race())
    assert list(row) == list(FEATURES)
    assert row["相手の数"] == 3 and row["頭数"] == 8 and row["◎人気"] == 1
    assert row["◎の1着率÷3着内率"] == pytest.approx(0.25 / 0.6)
    assert row["裏_市場"] == pytest.approx(_brute_force([0.125] * 8, 2, [0, 4, 7]))
    assert ReverseExactaFeatures().of(_race(star_value=1.0))["相手の数"] == 2   # 線に届かない ☆ は入れない


def test_本命が1頭でないか相手がいなければ材料は無い() -> None:
    race = _race()
    assert ReverseExactaFeatures().of(race.assign(mark=race["mark"].replace("◎", "－"))) is None
    assert ReverseExactaFeatures().of(race.assign(mark=race["mark"].replace({"○": "△", "▲": "△", "☆": "△"}))) is None


def _trained(seed: int = 0) -> tuple[ReverseExactaModel, pd.DataFrame]:
    generator = np.random.default_rng(seed)
    features = pd.DataFrame(generator.random((300, len(FEATURES))), columns=list(FEATURES))
    labels = pd.Series((features["裏_モデル"] + generator.normal(0, 0.2, 300) > 0.7).astype(int))
    return ReverseExactaModel.fit(features, labels, threads=1), features


def test_モデルは書いて読んでも同じ確率を出す(tmp_path: Path) -> None:
    model, features = _trained()
    model.save(tmp_path, {"races": 300})
    loaded = ReverseExactaModel.load(tmp_path)
    assert loaded is not None
    assert loaded.predict(features) == pytest.approx(model.predict(features))
    assert ((0 <= model.predict(features)) & (model.predict(features) <= 1)).all()


def test_モデルが無いか材料の並びが違えば読まない(tmp_path: Path) -> None:
    assert ReverseExactaModel.load(tmp_path) is None
    model, _ = _trained()
    model.save(tmp_path, {})
    manifest = tmp_path / MANIFEST_FILE
    manifest.write_bytes(json.dumps({"features": list(FEATURES)[:-1]}).encode("utf-8"))
    assert ReverseExactaModel.load(tmp_path) is None


def test_裏の確率が線以上なら裏まで買う_モデルが無ければ確率なし(tmp_path: Path) -> None:
    assert not ReverseExactaJudge.buys(None) and not ReverseExactaJudge.buys(LINE - 0.01) and ReverseExactaJudge.buys(LINE)
    assert ReverseExactaJudge.load(tmp_path).probability(_race()) is None
    model, _ = _trained()
    model.save(tmp_path / FOLDER, {})
    judge = ReverseExactaJudge.load(tmp_path)
    probability = judge.probability(_race())
    assert probability is not None and 0 <= probability <= 1
    assert judge.probability(_race().assign(mark="－")) is None


def test_裏まで買うレースだけ_印の買い目に馬単の裏を足す() -> None:
    def reverse_combos(race: pd.DataFrame) -> list[str]:
        tickets = MarkTickets().build(race)
        return sorted(tickets.loc[tickets[RULE] == REVERSE_EXACTA_RULE.label, "combo"])

    assert reverse_combos(_race(reverse=True)) == ["0103", "0503", "0803"]   # ○▲☆ → ◎
    assert reverse_combos(_race(star_value=1.0, reverse=True)) == ["0103", "0503"]
    assert reverse_combos(_race(reverse=False)) == [] and reverse_combos(_race()) == []


def _forecast(reverse: dict | None) -> dict:
    tickets = [{"rule": "単勝", "label": "3", "value": 1.1, "odds": 3.0, "dropped": ""},
               {"rule": "馬単（裏）", "label": "1→3", "value": 1.3, "odds": 20.0, "dropped": ""}]
    return {"timing": "当日", "tickets": tickets, "reverse_exacta": reverse}


def test_印の買い目の行に_裏の確率と裏まで買うかを添える() -> None:
    _, lines = RaceDescriber().mark_returns(_forecast({"probability": 0.34, "line": 0.30, "buys": True}))
    assert lines[1].startswith("馬単（裏）（1点 計 ")
    assert lines[-1] == "裏（◎ が2・3着で1着が ○▲☆）の確率 34%（線 30%）: 馬単の裏（○▲☆→◎）も買う"
    _, lines = RaceDescriber().mark_returns(_forecast({"probability": 0.12, "line": 0.30, "buys": False}))
    assert lines[-1].endswith("線に届かないので、裏は買わない")
    _, lines = RaceDescriber().mark_returns(_forecast(None))
    assert not any("裏（" in line for line in lines)
