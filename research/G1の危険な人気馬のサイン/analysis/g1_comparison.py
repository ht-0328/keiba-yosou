"""G1の人気馬のテスト期間で、作り方どうしを比べる表。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from 共通.render import Table
from yosou.shared.dataset import RACE_ID, TrainingData

from 既存モデルの改善.analysis.scores import BinaryScores
from 既存モデルの改善.analysis.stakes_rebuild import AdoptionRule
from 既存モデルの改善.analysis.walk_forward import WINDOW

from .g1_test_rows import BAND, LOST, MARKET_OUT, PLACE_PAYOUT, POPULARITY, WIN_PAYOUT, G1TestRows
from .sign_columns import SIGN_COUNT
from .sign_variants import ODDS_ONLY, SIGN_VARIANTS

#: 今の本番と同じ作り（全レースで学ぶ・今の材料）。
CURRENT = "all-current"
#: 市場の見立てそのまま（学習しない）の行の名前。
MARKET = "market"
#: 消の候補とみなす危険度の線（危険度 = 4着以下の確率 − 市場から見た4着以下の確率）。
_DANGER_LINE = 0.05
#: ルールだけで選ぶときの、サインの数の下限。
_RULE_SIGNS = 2
_ROUND = 4


class G1Comparison:
    """作り方ごとの予測を、G1の人気馬のテスト期間（2020〜2026年の7つの区切り）で比べる。

    1. 確率の誤差（ログ損失）と見分けやすさ（AUC・人気別AUC）。オッズだけ・今の本番と、区切りごとに比べた採否（7つのうち5つ以上で小さく、
       全期間でも小さい）。
    2. 区切りごとのログ損失。
    3. 人気帯ごとのログ損失。
    4. 消の候補の成績: 各レースで危険度がいちばん高い人気馬、危険度が線以上の人気馬（1番人気だけも）、サインの数で選んだ人気馬
       （学習しないルール）の 4着以下率・市場から見た4着以下率・差・単勝と複勝の回収率。
    """

    def tables(self, data: TrainingData, predictions: Mapping[str, pd.DataFrame]) -> list[Table]:
        rows = G1TestRows().build(data, predictions)
        rows = pd.concat([rows, self._market_rows(rows)], ignore_index=True)
        rows["danger"] = rows["probability"] - rows[MARKET_OUT]
        names = {variant.key: variant.name for variant in SIGN_VARIANTS} | {MARKET: "市場の見立てそのまま（学習しない）"}
        order = [MARKET, *(variant.key for variant in SIGN_VARIANTS if variant.key in set(rows["variant"]))]
        return [self._scores(rows, order, names), self._windows(rows, order, names), self._bands(rows, order, names),
                self._picks(rows, order, names)]

    def _market_rows(self, rows: pd.DataFrame) -> pd.DataFrame:
        first = rows[rows["variant"].eq(rows["variant"].iloc[0])]
        return first.assign(variant=MARKET, probability=first[MARKET_OUT])

    def _scores(self, rows: pd.DataFrame, order: list[str], names: dict[str, str]) -> Table:
        losses = {key: self._window_losses(rows[rows["variant"].eq(key)]) for key in order}
        overall = {key: self._loss(rows[rows["variant"].eq(key)]) for key in order}
        records = []
        for key in order:
            part = rows[rows["variant"].eq(key)]
            scores = BinaryScores().of(part[LOST], part["probability"], part[POPULARITY])
            record = {"作り方": names[key], "頭数": scores["頭数"], "ログ損失": round(scores["ログ損失"], _ROUND),
                      "AUC": round(scores["AUC"], 3), "人気別AUC": round(scores["人気別AUC"], 3)}
            for reference, label in ((ODDS_ONLY.key, "オッズだけ"), (CURRENT, "今の本番")):
                record[f"{label}より小さい区切り"] = self._verdict_text(losses, overall, key, reference)
            records.append(record)
        return Table.from_records(records, title="1. G1の人気馬の確率の誤差（7つの区切りのテスト期間を合わせて）",
                                  note="採否の基準: 7つの区切りのうち5つ以上でログ損失が小さく、全期間でも小さい（研究「既存モデルの改善」と同じ）。")

    def _verdict_text(self, losses: dict, overall: dict, key: str, reference: str) -> str:
        if key == reference or reference not in losses:
            return "-"
        verdict = AdoptionRule().verdict(losses[key], losses[reference], overall[key], overall[reference])
        return f"{verdict.better_windows}/{verdict.windows}（{'合格' if verdict.passes else '不合格'}）"

    def _windows(self, rows: pd.DataFrame, order: list[str], names: dict[str, str]) -> Table:
        table = pd.DataFrame({names[key]: self._window_losses(rows[rows["variant"].eq(key)]) for key in order})
        counts = rows[rows["variant"].eq(order[0])].groupby(WINDOW).size()
        records = [{"区切り": window, "頭数": int(counts[window]), **{name: round(value, _ROUND) for name, value in row.items()}}
                   for window, row in table.iterrows()]
        return Table.from_records(records, title="2. 区切りごとのログ損失（G1の人気馬。区切りは1年ずつ）")

    def _bands(self, rows: pd.DataFrame, order: list[str], names: dict[str, str]) -> Table:
        records = []
        for band, part in rows.groupby(BAND, sort=True):
            record = {"人気帯": band, "頭数": int(part["variant"].eq(order[0]).sum())}
            record |= {names[key]: round(self._loss(part[part["variant"].eq(key)]), _ROUND) for key in order}
            records.append(record)
        return Table.from_records(records, title="3. 人気帯ごとのログ損失（G1の人気馬）")

    def _picks(self, rows: pd.DataFrame, order: list[str], names: dict[str, str]) -> Table:
        records = []
        # 市場の見立てそのままは危険度がどの馬も 0 なので、危険度で選ぶ行は出さない
        for key in order[1:]:
            part = rows[rows["variant"].eq(key)]
            top = part.loc[part.groupby(RACE_ID)["danger"].idxmax()]
            records.append({"作り方": names[key], "選び方": "各レースで危険度1位", **self._measures(top)})
            records.append({"作り方": names[key], "選び方": f"危険度 {_DANGER_LINE:+.2f} 以上", **self._measures(
                part[part["danger"].ge(_DANGER_LINE)])})
            first = part[part[POPULARITY].eq(1)]
            records.append({"作り方": names[key], "選び方": f"1番人気で危険度 {_DANGER_LINE:+.2f} 以上", **self._measures(
                first[first["danger"].ge(_DANGER_LINE)])})
        base = rows[rows["variant"].eq(order[0])]
        records.append({"作り方": "サインの数だけ（学習しない）", "選び方": f"サインが {_RULE_SIGNS}つ以上",
                        **self._measures(base[base[SIGN_COUNT].ge(_RULE_SIGNS)])})
        records.append({"作り方": "（比べる元）", "選び方": "G1の人気馬の全部", **self._measures(base)})
        records.append({"作り方": "（比べる元）", "選び方": "G1の1番人気の全部", **self._measures(base[base[POPULARITY].eq(1)])})
        return Table.from_records(records, title="4. 消の候補の成績（G1の人気馬・テスト期間）",
                                  note="差 = 4着以下率 − 市場から見た4着以下率（ポイント）。プラスほど、市場の見立てより負けた。"
                                       "単勝オッズから出す市場の見立ては、G1 の1番人気の負けを少なく見る（比べる元の1番人気の行）ので、"
                                       "差はどの選び方でもプラスに寄る。作り方どうしは同じ選び方の行で比べる。"
                                       "回収率はその馬の単勝・複勝を買い続けたとき（消す馬なので低いほどよい）。")

    def _measures(self, part: pd.DataFrame) -> dict[str, object]:
        if part.empty:
            return {"頭数": 0, "4着以下率": "-", "市場から見た4着以下率": "-", "差": "-", "単勝回収率": "-", "複勝回収率": "-"}
        return {
            "頭数": len(part), "4着以下率": f"{part[LOST].mean():.1%}", "市場から見た4着以下率": f"{part[MARKET_OUT].mean():.1%}",
            "差": f"{(part[LOST].mean() - part[MARKET_OUT].mean()) * 100:+.1f}",
            "単勝回収率": f"{part[WIN_PAYOUT].sum() / (100 * len(part)):.0%}",
            "複勝回収率": f"{part[PLACE_PAYOUT].sum() / (100 * len(part)):.0%}",
        }

    def _window_losses(self, part: pd.DataFrame) -> pd.Series:
        return part.groupby(WINDOW).apply(self._loss, include_groups=False)

    def _loss(self, part: pd.DataFrame) -> float:
        p = np.clip(part["probability"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
        y = part[LOST].to_numpy(dtype=float)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
