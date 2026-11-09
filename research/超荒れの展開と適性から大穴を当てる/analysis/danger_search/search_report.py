"""消の線の探索の結果（基準・区切りごとの線・選んだ線）を表に書く。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import render
from 共通.render import Table

from yosou.shared.feature import PredictionTiming

from .danger_evaluator import Evaluation
from .line_search import BANDS, JUDGED, LineSearch, Trial
from .ticket_metrics import CONFIRM, EXPLORE, GROUPS


def _pct(value: float) -> str:
    return "" if pd.isna(value) else f"{value * 100:.1f}%"


def _lines_text(lines: dict[str, float | None]) -> str:
    return "・".join(f"{band} {'—' if line is None else f'{line * 100:.0f}ポイント'}" for band, line in lines.items())


class SearchReport:
    """``named`` は（決め方の名前 → ``Evaluation``）で、最初が基準（今の消・区切りごとの線）。``searches`` は（消の元の名前 → ``LineSearch``）。
    表は、1. 消の馬の成績、2. 券種ごとの的中率と回収率（期間ごと）、3. 年ごとの回収率、4. 線の探索の経過（探索の期間の差）。
    ``write`` は markdown に書き、``evaluations_csv`` は全部の評価の成績を1つの表に書く。"""

    def __init__(self, timing: PredictionTiming, named: dict[str, Evaluation], searches: dict[str, LineSearch],
                 chosen: dict[str, Trial]) -> None:
        self._timing = timing
        self._named = named
        self._searches = searches
        self._chosen = chosen

    def write(self, path: Path) -> Path:
        parts = [f"# 消の決め方の探索（{self._timing.label}）",
                 "道具「印の成績」と同じ部品で、消の決め方だけを替えて全券種の買い目を組み直した。探索 = 2019〜2024年、確認 = 2025年から。"
                 "線の探索は探索の期間の成績（消を使う買い方と全部の合計の、的中率と回収率の、今の消との差の最小）だけで選び、確認の期間は選んだあとに見た。"
                 "1点 100円 × 印の成績の単位。的中率 = 1点でも当たったレース ÷ 買ったレース。「消を使う買い方」は買い方の名前に「消」を含む 3連複の全部"
                 "（研究 docs/04 の 5.2 と同じ数え方）、「実際に買う3つ」はそのうち中荒れ・大荒れ・超荒れ。「全部の合計」は印の成績の買い目の表の全部の行。"]
        parts.append(render.to_markdown(self._danger_table()))
        parts.append(render.to_markdown(self._metrics_table()))
        parts.append(render.to_markdown(self._yearly_table()))
        for source, search in self._searches.items():
            parts.append(render.to_markdown(self._trials_table(source, search)))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
        return path

    def evaluations_csv(self, path: Path) -> Path:
        frames = [evaluation.metrics.assign(決め方=name) for name, evaluation in self._named.items()]
        for source, search in self._searches.items():
            for trial in search.trials.values():
                frames.append(trial.evaluation.metrics.assign(決め方=f"{source}・固定の線 {trial.label()}"))
        pd.concat(frames, ignore_index=True).to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def _danger_table(self) -> Table:
        rows = []
        for name, evaluation in self._named.items():
            for _, row in evaluation.dangers.iterrows():
                rows.append([name, row["区分"], f"{int(row['消の頭数']):,}", _pct(row["消の馬の4着以下"]), _pct(row["同じ人気の馬全体の4着以下"]),
                             "" if pd.isna(row["消の馬の4着以下"]) else f"{(row['消の馬の4着以下'] - row['同じ人気の馬全体の4着以下']) * 100:+.1f}"])
        return Table(["消の決め方", "区分", "消の頭数", "消の馬の4着以下", "同じ人気の馬全体の4着以下", "差"], rows, title="1. 消の馬の成績（テスト期間の全レース）")

    def _metrics_table(self) -> Table:
        headers = ["券種・買い方", "期間"]
        for name in self._named:
            headers.extend([f"{name} 買ったレース", f"{name} 的中率", f"{name} 回収率"])
        rows = []
        for group in GROUPS:
            for span in (EXPLORE, CONFIRM):
                cells = []
                for evaluation in self._named.values():
                    cells.extend([f"{evaluation.value(group, span, 'races'):,.0f}", _pct(evaluation.value(group, span, "hit_rate")),
                                  _pct(evaluation.value(group, span, "return_rate"))])
                rows.append([group, span, *cells])
        return Table(headers, rows, title="2. 券種ごとの的中率と回収率")

    def _yearly_table(self) -> Table:
        years = sorted({span for evaluation in self._named.values() for span in evaluation.metrics["span"] if span.isdigit()})
        headers = ["券種・買い方", "消の決め方", *(f"{year} 的中率 / 回収率" for year in years)]
        rows = []
        for group in GROUPS:
            for name, evaluation in self._named.items():
                rows.append([group, name, *(f"{_pct(evaluation.value(group, year, 'hit_rate'))} / {_pct(evaluation.value(group, year, 'return_rate'))}"
                                            for year in years)])
        return Table(headers, rows, title="3. 年ごとの的中率と回収率")

    def _trials_table(self, source: str, search: LineSearch) -> Table:
        headers = ["線（ポイント）", *(f"{group} {'的中率' if column == 'hit_rate' else '回収率'}の差" for group, column in JUDGED), "差の最小", "探索で全部が基準以上", "選んだ"]
        chosen = self._chosen.get(source)
        rows = []
        for trial in sorted(search.trials.values(), key=lambda t: t.score, reverse=True):
            rows.append([trial.label(), *(f"{margin:+.2f}" for margin in trial.margins), f"{min(trial.margins):+.2f}",
                         "はい" if trial.satisfied else "", "◎" if chosen is not None and trial.lines == chosen.lines else ""])
        return Table(headers, rows, title=f"4. 線の探索の経過（{source}。探索の期間の、今の消（区切りごとの線）との差。ポイント）",
                     note=f"人気帯の順（{'・'.join(BANDS)}）に、1つの人気帯の線だけを候補の中で動かして全部試し、差の最小がいちばん大きい線に移すのを繰り返した。"
                          "— はその人気帯を消にしない。")
