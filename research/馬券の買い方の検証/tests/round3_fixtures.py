"""3回目のテストで使う架空の材料（``Round3Materials``）を作る部品。値はすべて作りもの。

2つの区切り（2023年前半・2023年後半）の検証とテストに、開催日 × レース × 12頭 の行を作る。
人気順位 = 馬番。12頭なので 1〜3番人気が人気馬、4〜6番人気が中穴、7番人気以下が大穴。
複勝オッズ（下限）は 1.2 + 0.5 × 人気、上限はその 1.3倍。穴馬モデルの確率は「1 ÷ 複勝オッズ × 上げ下げ（0.8〜1.4）」で、
期待値がおよそ 0.8〜1.4 に散らばる。3着以内は、その確率に比例した重みで3頭を引く（乱数の種は固定）。
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from yosou.upset_level.dataset import BetType, UpsetLevel

from 馬券の買い方の検証.analysis.value_betting import Round3Materials
from 馬券の買い方の検証.analysis.value_betting import columns as c

WINDOW_1, WINDOW_2 = "2023年前半", "2023年後半"
FIELD_SIZE = 12
#: 区切り × 期間 の最初の開催日（研究「既存モデルの改善」の区切りの日付に合わせる）。
FIRST_DAYS: dict[tuple[str, str], date] = {
    (WINDOW_1, c.PART_VALID): date(2022, 7, 2), (WINDOW_1, c.PART_TEST): date(2023, 1, 7),
    (WINDOW_2, c.PART_VALID): date(2023, 1, 7), (WINDOW_2, c.PART_TEST): date(2023, 7, 1),
}
_BOOSTS = (0.8, 1.0, 1.2, 1.4)


def runners(window: str, part: str, *, days: int = 10, races: int = 6, seed: int = 7) -> pd.DataFrame:
    """1つの区切り × 期間 の1頭ごとの行（``RunnerTableBuilder`` の列）。"""
    rng = np.random.default_rng(seed + hash((window, part)) % 1000)
    first = FIRST_DAYS[(window, part)]
    frames = [_race(window, part, first + timedelta(days=7 * day), day, number, rng) for day in range(days) for number in range(1, races + 1)]
    return pd.concat(frames, ignore_index=True)


def _race(window: str, part: str, day: date, day_index: int, number: int, rng: np.random.Generator) -> pd.DataFrame:
    horses = np.arange(1, FIELD_SIZE + 1)
    race_id = f"{day:%Y%m%d}05{day_index + 1:02d}{number:02d}"
    place_odds = 1.2 + 0.5 * horses
    market_top3 = np.clip(0.9 / (1 + 0.45 * (horses - 1)), 0.03, 0.9)
    boosts = np.array([_BOOSTS[(day_index + number + horse) % len(_BOOSTS)] for horse in horses])
    longshot_prob = np.where(horses >= 4, np.minimum(0.6, boosts / place_odds), np.nan)
    weights = np.where(horses >= 4, longshot_prob, market_top3)
    top3 = np.zeros(FIELD_SIZE, dtype=int)
    top3[rng.choice(FIELD_SIZE, size=3, replace=False, p=weights / weights.sum())] = 1
    finish = np.where(top3 == 1, rng.permutation(np.arange(1, 4)).take(np.cumsum(top3) - 1), 4 + np.arange(FIELD_SIZE))
    danger_prob = np.where(horses <= 3, (1 - market_top3) + rng.uniform(-0.05, 0.2, FIELD_SIZE), np.nan)
    return pd.DataFrame({
        c.WINDOW: window, c.PART: part, c.RACE_ID: race_id, c.RACE_DATE: pd.Timestamp(day), c.HORSE_ID: [f"H{number}{horse:02d}" for horse in horses],
        c.HORSE_NO: horses, c.FINISH: finish, c.TOP3: top3, c.WIN_ODDS: 1.5 * horses, c.POPULARITY: horses,
        c.PLACE_PAYOUT: np.where(top3 == 1, np.round(place_odds * 110), 0.0), c.PLACE_ODDS: place_odds, c.PLACE_ODDS_HIGH: place_odds * 1.3,
        c.FIELD_SIZE: FIELD_SIZE, c.MARKET_TOP2: market_top3 * 0.7, c.MARKET_TOP3: market_top3,
        c.FORM_PROB: np.clip(market_top3 + rng.uniform(-0.05, 0.05, FIELD_SIZE), 0.01, 0.99), c.DANGER_PROB: danger_prob,
        c.LONGSHOT_PROB: longshot_prob, c.LONGSHOT_ZONE: np.where(horses >= 7, "大穴", np.where(horses >= 4, "中穴", None)),
    })


def races_of(runners_frame: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    """1頭ごとの行から、レースごとの表（``RaceTableBuilder`` の列）。各開催日の 6R を平地の重賞にする。"""
    rng = np.random.default_rng(seed)
    races = runners_frame[[c.WINDOW, c.PART, c.RACE_ID, c.RACE_DATE]].drop_duplicates().reset_index(drop=True)
    races[c.IS_GRADED] = races[c.RACE_ID].str.endswith("06")
    labels = list(UpsetLevel.labels())
    for bet in BetType:
        solid = rng.uniform(0.2, 0.8, len(races))
        races[c.upset_column(bet)] = 1 - solid
        races[c.upset_level_column(bet)] = np.where(solid >= 0.5, labels[0], labels[1])
    return races


def price_history(seed: int = 3) -> pd.DataFrame:
    """見込みの倍率を学ぶ履歴（2017〜2022年の架空の払戻）。"""
    rng = np.random.default_rng(seed)
    days = pd.to_datetime("2017-01-07") + pd.to_timedelta(rng.integers(0, 6 * 365, 600), "D")
    odds = rng.uniform(1.1, 20.0, 600)
    hit = rng.uniform(size=600) < 0.3
    return pd.DataFrame({c.RACE_DATE: days, c.PLACE_ODDS: odds, c.PLACE_ODDS_HIGH: odds * 1.4,
                         c.PLACE_PAYOUT: np.where(hit, np.round(odds * 115), 0.0)})


def materials(*, days: int = 10, races: int = 6) -> Round3Materials:
    """2つの区切り × 検証とテスト の材料。"""
    frames = [runners(window, part, days=days, races=races) for (window, part) in FIRST_DAYS]
    all_runners = pd.concat(frames, ignore_index=True)
    return Round3Materials(all_runners, races_of(all_runners), price_history())
