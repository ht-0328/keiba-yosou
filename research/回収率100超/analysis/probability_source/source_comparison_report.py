"""比べた結果を1つの文書にする。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ..backtest import EARLY_YEARS, LATE_YEARS, MIN_YEARLY_BETS, LineStudyTable
from .probability_source_table import ORIGINAL
from .source_result import SourceResult
from .source_verdicts import SourceVerdicts


class SourceComparisonReport:
    """出どころごとの線の選び方・年ごとの成績・判定・確率の当たり具合を、Markdown の文書にする（Git 対象外の reports/ に書く）。

    ``results`` は出どころの名前 → 成績（元を先頭に）。``verdicts`` は元以外の判定。``log_loss`` は年ごとのログ損失の表。
    """

    def __init__(self, line_table: LineStudyTable | None = None) -> None:
        self._line_table = line_table or LineStudyTable()

    def build(self, results: Mapping[str, SourceResult], verdicts: SourceVerdicts, log_loss: pd.DataFrame,
              rows: int, years: tuple[int, int]) -> str:
        lines = [*self._header(rows, years), *self._verdict_section(results, verdicts)]
        for result in results.values():
            lines += self._source_section(result)
        lines += ["## 確率の当たり具合（ログ損失。小さいほど良い）", "", log_loss.to_markdown(index=False), "",
                  *self._overlap_section(results)]
        return "\n".join(lines)

    def _header(self, rows: int, years: tuple[int, int]) -> list[str]:
        return ["# 回収率100超 — 確率の出どころを替えて同じ複勝の買い方で比べる", "",
                "JV-Data 由来の値を含むため、この文書は Git の対象外。やり方と採用の基準は docs/04-買い方.md の 8。", "",
                f"- 比べた行: {rows:,} 頭（{years[0]}〜{years[1]}年。元の予測と新しい予測の両方にある馬だけ）",
                "- 新しい確率: 予想「近走と適性から3着以内を予想」の当日のモデル（券種の支持 N を含む）を、"
                "その年より前だけで年ごとに学習し直したもの。レース内で合計が対象着順の数になるようそろえ直してある",
                "- 買い方: 期待値 = 確率 × 想定払戻倍率。線は候補（1.00〜1.40）から"
                f"前半 {EARLY_YEARS[0]}〜{EARLY_YEARS[1]}年だけで選ぶ（回収率 100% 超・1年あたり {MIN_YEARLY_BETS} 点以上のうち"
                f"回収率がいちばん高い線）。後半 {LATE_YEARS[0]}〜{LATE_YEARS[1]}年は選ぶのに使わない。1点 100円", ""]

    def _verdict_section(self, results: Mapping[str, SourceResult], verdicts: SourceVerdicts) -> list[str]:
        rows = [self._summary_row(result, verdicts) for result in results.values()]
        return ["## 判定", "", pd.DataFrame(rows).to_markdown(index=False), "",
                "採用の基準（結果を見る前に決めた）: 線が選べ、全期間の回収率と 90% の下限が 100% を超え（使える）、"
                "そのうえ後半の回収率が元より高く後半の下限も 100% を超える（元より良い）。", ""]

    def _summary_row(self, result: SourceResult, verdicts: SourceVerdicts) -> dict[str, object]:
        late = result.late
        return {"出どころ": result.name, "選んだ線": "なし" if result.line is None else f"{result.line:.2f}",
                "買い目": int(len(result.bought)), "全期間の回収率": result.total_rate, "全期間の90%の下限": result.total_low,
                "後半の回収率": "" if late is None else round(late.rate, 1),
                "後半の90%の下限": "" if late is None else round(late.low, 1),
                "判定": "（比べる元）" if result.name == ORIGINAL else verdicts.of(result.name).text}

    def _source_section(self, result: SourceResult) -> list[str]:
        chosen = "なし" if result.line is None else f"{result.line:.2f}"
        return [f"## {result.name}", "", "### 線の選び方", "", self._line_table.build(result.study).to_markdown(index=False), "",
                f"決まりで選んだ線: **{chosen}**", "", "### 選んだ線で買ったときの年ごとの成績", "",
                result.yearly.to_markdown(index=False), ""]

    def _overlap_section(self, results: Mapping[str, SourceResult]) -> list[str]:
        original = results[ORIGINAL].bought[["rid", "horse_no"]]
        rows = [{"出どころ": result.name, "買い目": len(result.bought),
                 "元と同じ買い目": len(result.bought[["rid", "horse_no"]].merge(original, on=["rid", "horse_no"]))}
                for name, result in results.items() if name != ORIGINAL]
        return ["## 元と同じ買い目をどれだけ買ったか", "", pd.DataFrame(rows).to_markdown(index=False), ""]
