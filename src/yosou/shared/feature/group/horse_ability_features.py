"""M. 馬の力の材料（202個）。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from ..ability import AbilitySources, AbilityTableBuilder, ability_columns
from ..entry_records import EntryRecords

#: 出走の行と、材料の表を突き合わせる鍵（木曜は馬番が無いので、馬で突き合わせる）。
_KEY = ["race_id", "horse_id"]
#: 予測のときに、出走の行（速報を反映したあと）の値で置き換える、対象の出走の列。
_ANNOUNCED = ["horse_no", "frame_no", "body_weight", "weight_change"]


class HorseAbilityFeatures:
    """M. 馬の力の材料。研究「馬の力と展開でオッズに勝つ」のオッズを使わない 197個と、セリの価格の5個。

    スピード指数・過去走の位置取りと相手の強さとペース・騎手と調教師と馬主と生産者と母と血統の通算の成績・調教・
    同じレースの馬との比べ・セリの価格から作る（研究「一番人気を疑う」で、木曜の予想をこの材料で作り直すと、
    ◎の3着以内率が今の木曜版よりはっきり上がった）。元の記録は ``records.ability_sources``（``AbilitySourcesLoader`` が読む）。
    予測のときは、対象のレースの行を、速報（馬体重・取消）を反映した出走の行に合わせてから作る。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        if records.ability_sources is None:
            return pd.DataFrame(float("nan"), index=entries.index, columns=list(ability_columns()))
        sources = replace(records.ability_sources, runs=self._announced(records.ability_sources.runs, entries))
        table = AbilityTableBuilder().build(sources)
        keys = pd.DataFrame({"race_id": entries["race_id"].astype(str).to_numpy(),
                             "horse_id": entries["horse_id"].astype(str).to_numpy()})
        table = table.assign(race_id=table["race_id"].astype(str), horse_id=table["horse_id"].astype(str))
        aligned = keys.merge(table.drop_duplicates(_KEY), on=_KEY, how="left")
        return aligned[list(ability_columns())].set_axis(entries.index)

    def _announced(self, runs: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
        """対象のレースの行を、出走の行に合わせる。出走の行に無い馬（取消・除外）は出走しなかったことにする。

        出走の行のあるレースだけを合わせ、ほかのレース（学習のときのウォームアップの期間など）はそのまま。
        """
        shown = entries[[*_KEY, *_ANNOUNCED]].drop_duplicates(_KEY).set_index(_KEY)
        index = pd.MultiIndex.from_frame(runs[_KEY])
        in_race = runs["is_target"] & runs["race_id"].isin(entries["race_id"])
        present = index.isin(shown.index)
        aligned = shown.reindex(index)
        updated = runs.assign(ran=runs["ran"].where(~in_race, present))
        for column in _ANNOUNCED:
            updated[column] = runs[column].where(~(in_race & present), aligned[column].to_numpy())
        return updated
