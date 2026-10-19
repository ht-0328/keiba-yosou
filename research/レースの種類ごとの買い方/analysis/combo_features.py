"""保存済みの組の表（1券種・1年）に、組の確率のもとと、足す材料と、レースの種類を付ける。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .race_kinds import KIND_DUMMIES, KIND_GROUP

#: 今の本番の4つのもと（``yosou.shared.combo_value.FEATURE_COLUMNS`` と同じ順・同じ作り）。
BASE_FEATURES: tuple[str, ...] = ("log_own", "log_trifecta", "log_harville", "log_ratio")
#: 案「材料」で足す3つ（docs/01 の 4）。
EXTRA_FEATURES: tuple[str, ...] = ("own_curve", "longshot_ratio", "has_top")
#: 穴馬とみなす人気（この人気より下）。
LONGSHOT_POPULARITY = 10
#: 対数を取る前の下限（本番の ``ComboBlendFeatures`` と同じ）。
_FLOOR = 1e-9
#: 読む列（組の表の列名）。q = その券種自身の市場、t = 3連単から見た市場、hv = モデルの Harville、rw・rt = 馬ごとの1着・3着以内の比。
_COLUMNS = ("rid", "odds", "q", "t", "hv", "payout", "race_date", "expectation", "fold", "top")


class ComboFeatures:
    """``combos/<券種>_<年>.parquet``（研究「複勝以外の回収率100超」の手順6 が作った、全部の組の表）を読み、1行 = 1組の表にする。

    列は ``race_id``・``race_date``・``fold``・``expectation``・``top``・``h1``…・``odds``・``payout``（100円あたり。外れは 0）・``hit``・
    ``BASE_FEATURES``・``EXTRA_FEATURES``・種類の列（``RaceKinds``）。種類の分からないレースと、もとの欠けた組は落とす。行はレースIDの順。

    - ``own_curve``: （その券種自身の市場の対数 + 6）の2乗 ÷ 10。人気薄ほど大きくなる曲がり（6 と 10 は値の大きさをそろえるため）。
    - ``longshot_ratio``: 10番人気以下の馬の比の対数の和（比の選び方は ``log_ratio`` と同じ。穴馬でなければ 0）。
    - ``has_top``: ◎ を含む組なら 1（着順を区別する券種は ◎ が1着の組だけ）。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def of(self, ticket_type: TicketType, year: int, kinds: pd.DataFrame) -> pd.DataFrame:
        count = ticket_type.spec.horse_count
        numbers = tuple(range(1, count + 1))
        columns = [*_COLUMNS, *(f"h{at}" for at in numbers), *(f"pop{at}" for at in numbers),
                   *(f"rt{at}" for at in numbers), *(["rw1"] if ticket_type.spec.is_ordered else [])]
        raw = pd.read_parquet(self._folder / f"{ticket_type.spec.key}_{year}.parquet", columns=columns)
        return self.build(ticket_type, raw, kinds)

    def build(self, ticket_type: TicketType, raw: pd.DataFrame, kinds: pd.DataFrame) -> pd.DataFrame:
        """組の表の列（``_COLUMNS``・``h``・``pop``・``rt``・着順を区別する券種は ``rw1``）から作る（テストはここを呼ぶ）。"""
        count = ticket_type.spec.horse_count
        table = pd.DataFrame({"race_id": raw["rid"].astype(str), "race_date": pd.to_datetime(raw["race_date"]), "fold": raw["fold"],
                              "expectation": raw["expectation"], "top": raw["top"], "odds": raw["odds"].astype(float),
                              "payout": raw["payout"].astype(float)})
        for at in range(1, count + 1):
            table[f"h{at}"] = raw[f"h{at}"].astype(int)
        table["hit"] = table["payout"] > 0
        log_ratio = np.zeros(len(raw))
        longshot = np.zeros(len(raw))
        for at in range(1, count + 1):
            column = "rw1" if ticket_type.spec.is_ordered and at == 1 else f"rt{at}"
            value = np.log(raw[column].to_numpy(dtype=float))
            log_ratio += value
            longshot += np.where(raw[f"pop{at}"].to_numpy(dtype=float) >= LONGSHOT_POPULARITY, value, 0.0)
        table["log_own"] = np.log(raw["q"].astype(float).clip(lower=_FLOOR))
        table["log_trifecta"] = np.log(raw["t"].astype(float).clip(lower=_FLOOR))
        table["log_harville"] = np.log(raw["hv"].astype(float).clip(lower=_FLOOR))
        table["log_ratio"] = log_ratio
        table["own_curve"] = (table["log_own"] + 6.0) ** 2 / 10.0
        table["longshot_ratio"] = longshot
        table["has_top"] = self._has_top(ticket_type, table).astype(float)
        table = table.dropna(subset=[*BASE_FEATURES, *EXTRA_FEATURES])
        table = table.merge(kinds[["race_id", KIND_GROUP, *KIND_DUMMIES]], on="race_id", how="inner")
        for name in (*BASE_FEATURES, *EXTRA_FEATURES, *KIND_DUMMIES):
            table[name] = table[name].astype(np.float32)
        return table.sort_values("race_id", kind="stable").reset_index(drop=True)

    def _has_top(self, ticket_type: TicketType, table: pd.DataFrame) -> pd.Series:
        if ticket_type.spec.is_ordered:
            return table["h1"] == table["top"]
        return pd.concat([table[f"h{at}"] == table["top"] for at in range(1, ticket_type.spec.horse_count + 1)], axis=1).any(axis=1)
