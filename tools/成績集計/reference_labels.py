"""出走の表に、基準のページの表の行の名前（切り口の値）を付ける。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes

from 成績集計 import reference_bands as bands

STYLE_ORDER: tuple[str, ...] = (*codes.STYLE_NAMES.values(), "不明")
SEX_ORDER: tuple[str, ...] = (*codes.SEX_NAMES.values(), "?")
CLASS_ORDER: tuple[str, ...] = (*sorted(codes.CLASS_ORDER, key=codes.CLASS_ORDER.get), codes.UNKNOWN_CLASS)


class ReferenceLabels:
    """``ReferenceRuns`` の表に、表ごとの行の名前の列（``label_*``）を足す。

    行の名前が無い（空の）出走は、その表では数えない。たとえば人気帯は人気のある出走だけ、タイム型の表は
    タイム型の予想がある出走だけ、性別は牡・セン と牝が混ざったレースだけ、馬齢は年齢が混ざったレースだけを数える。
    帯の表で値が無い出走は、帯の「不明」（前走の表なら「前走なし・不明」）の行に入る。
    """

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        has_popularity = runs["popularity"].notna()
        has_dm, has_tm = runs["dm_rank"].notna(), runs["tm_rank"].notna()
        return runs.assign(
            label_odds=bands.ODDS.label(runs["win_odds"]),
            label_style=_ordered(runs["style_code"].map(codes.STYLE_NAMES).fillna("不明"), STYLE_ORDER),
            label_last3f_rank=bands.LAST3F_RANK.label(runs["last3f_rank"]),
            label_last3f_time=bands.LAST3F_TIME.label(runs["last3f"]),
            label_sex=_ordered(runs["sex_code"].map(codes.SEX_NAMES).fillna("?").where(runs["mixed_sex"]), SEX_ORDER),
            label_age=_only(bands.AGE.label(runs["age"]), runs["mixed_age"]),
            label_body_weight=bands.BODY_WEIGHT.label(runs["body_weight"]),
            label_weight_change=bands.WEIGHT_CHANGE.label(runs["weight_change"]),
            label_interval=bands.INTERVAL.label(runs["interval_days"]),
            label_prev_finish=bands.PREV_FINISH.label(runs["prev_finish"]),
            label_prev_popularity=bands.PREV_POPULARITY.label(runs["prev_popularity"]),
            label_popularity_top=_only(bands.POPULARITY_TOP.label(runs["popularity"]), has_popularity),
            label_dm_rank=_only(bands.MINING_RANK.label(runs["dm_rank"]), has_dm),
            label_dm_top=_only(bands.MINING_TOP.label(runs["dm_rank"]), has_dm),
            label_dm_gap=_only(bands.MINING_GAP.label(runs["dm_rank"] - runs["popularity"]), has_dm & has_popularity),
            label_tm_rank=_only(bands.MINING_RANK.label(runs["tm_rank"]), has_tm),
            label_tm_top=_only(bands.MINING_TOP.label(runs["tm_rank"]), has_tm),
            label_tm_score=_only(bands.TM_SCORE.label(runs["tm_score"]), has_tm),
            label_tm_gap=_only(bands.MINING_GAP.label(runs["tm_rank"] - runs["popularity"]), has_tm & has_popularity),
            label_class=_ordered(runs["class_name"], CLASS_ORDER),
            label_field_size=bands.FIELD_SIZE.label(runs["field_size"]),
        )


def _ordered(names: pd.Series, order: tuple[str, ...]) -> pd.Categorical:
    return pd.Categorical(names, categories=list(order), ordered=True)


def _only(labels: pd.Categorical, rows: pd.Series) -> pd.Series:
    """``rows`` が偽の出走の名前を空にする（その表では数えない）。"""
    return pd.Series(labels, index=rows.index).where(rows.to_numpy(dtype=bool))
