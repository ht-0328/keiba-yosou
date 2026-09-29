"""K. 重賞の傾向（10個）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import EntryRecords

from 共通.stakes import FRONT_STYLES, INNER_FRAME_NO, REST_INTERVAL_DAYS

#: 縮める強さ k（設計書 09 の K）。ずれ = n/(n+k) × (そのレースの過去の率 − 基準の率)。
#: 過去の出走数 n が k と同じで、ずれを半分だけ信じる。切り口の1開催あたりの頭数に合わせている。
SHRINK_FAV1 = 8
SHRINK_FAV123 = 24
SHRINK_FRONT = 30
SHRINK_INNER = 30
SHRINK_REST = 20
SHRINK_WEST = 40
SHRINK_REPEAT = 12

#: 特徴量の名前（``feature_catalog.py`` の K と同じ並び）。
EDITIONS = "重賞の過去開催の数"
FAV123_GAP = "上位人気の信頼度のずれ"
FAV1_GAP = "1番人気の信頼度のずれ"
FRONT_GAP = "前に行く馬のずれ"
FRONT_GAP_SELF = "前に行く馬のずれ×前に行くか"
INNER_GAP = "内枠のずれ"
INNER_GAP_SELF = "内枠のずれ×枠の内寄り"
REST_GAP_SELF = "休み明けのずれ×休み明けか"
WEST_GAP_SELF = "関西馬のずれ×関西馬か"
REPEAT_GAP_SELF = "好走経験者のずれ×好走経験があるか"


class StakesTendencyFeatures:
    """K. 重賞の傾向（設計書 09 の K）。``FeatureGroup`` を守る。

    ``records.stakes_tendency``（レースごとの、それより前の開催の数え上げと基準。
    ``StakesTendencyRepository`` が読む）から、レースごとの「縮めたずれ」を計算し、
    馬の側の値（推定脚質・枠番・間隔・所属・好走経験）と掛け合わせる。
    重賞でないレースの行と、過去の開催が無いレースは、ずれ 0（基準どおり）になる。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        gaps = self._race_gaps(records.stakes_tendency)
        joined = entries[["race_id"]].merge(gaps, on="race_id", how="left") if len(gaps) else pd.DataFrame()
        race = {name: (joined[name].to_numpy() if len(joined) else np.zeros(len(entries)))
                for name in ("editions", "fav123_gap", "fav1_gap", "front_gap", "inner_gap",
                             "rest_gap", "west_gap", "repeat_gap")}
        race = {name: np.nan_to_num(values, nan=0.0) for name, values in race.items()}
        return pd.DataFrame({
            EDITIONS: race["editions"],
            FAV123_GAP: race["fav123_gap"],
            FAV1_GAP: race["fav1_gap"],
            FRONT_GAP: race["front_gap"],
            FRONT_GAP_SELF: race["front_gap"] * self._is_front(entries),
            INNER_GAP: race["inner_gap"],
            INNER_GAP_SELF: race["inner_gap"] * self._inner_score(entries),
            REST_GAP_SELF: race["rest_gap"] * self._is_rest(entries),
            WEST_GAP_SELF: race["west_gap"] * self._is_west(entries),
            REPEAT_GAP_SELF: race["repeat_gap"] * self._has_experience(entries),
        }, index=entries.index)

    def _race_gaps(self, tendency: pd.DataFrame) -> pd.DataFrame:
        """レースごとの縮めたずれ。列は ``race_id`` と ``*_gap``・``editions``。"""
        if len(tendency) == 0:
            return pd.DataFrame(columns=["race_id"])
        t = tendency
        return pd.DataFrame({
            "race_id": t["race_id"],
            "editions": t["editions"].astype("float64"),
            "fav123_gap": self._gap(t, "fav123", SHRINK_FAV123, t["base_fav123"]),
            "fav1_gap": self._gap(t, "fav1", SHRINK_FAV1, t["base_fav1"]),
            "front_gap": self._excess_gap(t, "front", SHRINK_FRONT, t["base_front_excess"]),
            "inner_gap": self._excess_gap(t, "inner", SHRINK_INNER, t["base_inner_excess"]),
            "rest_gap": self._gap(t, "rest", SHRINK_REST, t["base_rest"]),
            "west_gap": self._gap(t, "west", SHRINK_WEST, t["base_west"]),
            "repeat_gap": self._gap(t, "repeat", SHRINK_REPEAT, t["base_repeat"]),
        })

    def _gap(self, t: pd.DataFrame, prefix: str, shrink: int, base: pd.Series) -> np.ndarray:
        """縮めたずれ = n/(n+k) × (過去の3着以内率 − 基準の3着以内率)。過去か基準が無ければ 0。"""
        n = t[f"{prefix}_n"].astype("float64").to_numpy()
        hits = t[f"{prefix}_hits"].astype("float64").to_numpy()
        base_values = pd.to_numeric(base, errors="coerce").to_numpy(dtype="float64")
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(n > 0, hits / np.maximum(n, 1.0), np.nan)
            gap = n / (n + shrink) * (rate - base_values)
        return np.nan_to_num(gap, nan=0.0)

    def _excess_gap(self, t: pd.DataFrame, prefix: str, shrink: int, base_excess: pd.Series) -> np.ndarray:
        """脚質・枠のずれ。頭数の違いをならすため、超過複勝率（3着以内率 − 3÷頭数）どうしで比べる。"""
        n = t[f"{prefix}_n"].astype("float64").to_numpy()
        hits = t[f"{prefix}_hits"].astype("float64").to_numpy()
        expected = t[f"{prefix}_exp"].astype("float64").to_numpy()
        base_values = pd.to_numeric(base_excess, errors="coerce").to_numpy(dtype="float64")
        with np.errstate(invalid="ignore", divide="ignore"):
            excess = np.where(n > 0, (hits - expected) / np.maximum(n, 1.0), np.nan)
            gap = n / (n + shrink) * (excess - base_values)
        return np.nan_to_num(gap, nan=0.0)

    def _is_front(self, entries: pd.DataFrame) -> np.ndarray:
        """推定脚質が前（逃げ・先行）なら 1。過去走が無く推定できなければ 0。"""
        return entries["style_before"].isin(FRONT_STYLES).to_numpy(dtype="float64")

    def _inner_score(self, entries: pd.DataFrame) -> np.ndarray:
        """枠の内寄り。1枠 = 1.0、4枠 = 0.25、5枠から外 = 0。枠が未定（木曜）は 0。"""
        frame = pd.to_numeric(entries["frame_no"], errors="coerce").to_numpy(dtype="float64")
        score = ((INNER_FRAME_NO + 2) - frame) / ((INNER_FRAME_NO + 2) - 1)
        return np.nan_to_num(np.clip(score, 0.0, 1.0), nan=0.0)

    def _is_rest(self, entries: pd.DataFrame) -> np.ndarray:
        """休み明け（中9週以上）なら 1。前走が無ければ 0。"""
        interval = pd.to_numeric(entries["interval_days"], errors="coerce")
        return (interval >= REST_INTERVAL_DAYS).to_numpy(dtype="float64")

    def _is_west(self, entries: pd.DataFrame) -> np.ndarray:
        return (entries["affiliation"] == "栗東").to_numpy(dtype="float64")

    def _has_experience(self, entries: pd.DataFrame) -> np.ndarray:
        """同じレースで3着以内の経験があれば 1。"""
        places = pd.to_numeric(entries["same_race_places_before"], errors="coerce")
        return (places >= 1).to_numpy(dtype="float64")
