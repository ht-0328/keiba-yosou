"""基準のページの目次（``index.md``）を書く。対象の期間・作り方・数え方の約束と、ページの一覧。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import codes

from 成績集計.reference_page_writer import GOING_ORDER, page_name
from 成績集計.reference_table_spec import SECTION_TABLES

INDEX_NAME = "index.md"
#: 目次のページの一覧に出す馬場状態（「不明」は出さない）。
_LISTED_GOINGS: tuple[str, ...] = GOING_ORDER[:4]


class ReferenceIndexWriter:
    """``ReferenceRuns`` の表から、目次を ``out_dir/index.md`` に書く。"""

    def __init__(self, made_on: str) -> None:
        self._made_on = made_on

    def write(self, runs: pd.DataFrame, out_dir: Path) -> Path:
        path = out_dir / INDEX_NAME
        path.write_text("\n".join([*self._intro(runs), *self._page_list(runs)]) + "\n", encoding="utf-8")
        return path

    def _intro(self, runs: pd.DataFrame) -> list[str]:
        tables = "・".join(table.title for table in SECTION_TABLES)
        return [
            "# 基準のページ — 競馬場×コース×距離×馬場状態ごとの成績", "",
            "!!! warning \"公開しない\"", "",
            "    この表は JRA-VAN Data Lab. のデータから作ったもので、騎手名・調教師名と払戻を含む。",
            "    `reports/` は Git 対象外にしてあり、公開リポジトリには載せない。", "",
            "**どのコースで、どんな条件の馬が、どれだけ勝ち、どれだけ回収できているか**を、コースの単位ごとに数えたもの。"
            "`tools/成績集計/perf.py --check`（答え合わせ）の基準に使う。", "",
            f"対象: 中央競馬 {runs['race_date'].min()} 〜 {runs['race_date'].max()}、"
            f"{runs['rid'].nunique():,} レース・延べ {len(runs):,} 頭（平地・障害とも）。",
            f"`tools/成績集計/build_pages.py` が作る（作成日 {self._made_on}）。**手で直さない。**", "",
            "## 1. 作り方（答え合わせの基準にするため、集計の道具とは別の道筋で数える）", "",
            "`perf.py` は事実表（`tools/共通/facts.py` の SQL）と `tools/共通/perf.py` の集計で数える。"
            "このページはそのどちらも使わず、元DB の `se`（馬毎レース情報）・`ra`（レース詳細）・"
            "`hr__単勝払戻`・`hr__複勝払戻` を直接読んで（`tools/成績集計/repository/`）、pandas で数える"
            "（`reference_runs.py`・`reference_tally.py`）。数え方の約束は JV-Data 仕様書から決め直した。"
            "同じ約束を別の書き方で数えて同じ値になれば、どちらの集計も正しいと考えられる。", "",
            "## 2. 数え方の約束", "",
            "- 対象は中央競馬（競馬場コード 01 札幌〜10 小倉）で、`ra`・`se` のデータ区分が 5・6（速報成績。全馬の着順が確定）"
            "か 7（月曜の成績）の出走。",
            "- 出走取消・発走除外・競走除外（異常区分 1・2・3）は出走に数えない。競走中止・失格（4・5）は「出走して馬券外」。",
            "- 着別度数は確定着順（降着のあとの着順）で数える。同着はどちらも同じ着に数える。",
            "- 人気・オッズは確定値（`se` の `単勝人気順`・`単勝オッズ`）。払戻は `hr` の単勝・複勝（100円あたり）。同着の払戻は馬番ごとに付く。",
            "- 馬場状態は、ダートのコースならダートの、芝と障害なら芝の馬場状態（芝が空ならダート）。"
            "「コース」はトラックコードの名前（芝・左 など）。",
            "- 回収率の基準は 80%（控除率 20%）。細かく分けた行・レース数の少ない節は率が振れやすい。出走数を見てから読む。", "",
            "## 3. 各節の表", "",
            f"{tables}。成績の列は {'・'.join(('出走数', '着別度数', '勝率', '連対率', '複勝率', '馬券外率', '単勝回収率', '複勝回収率'))}。",
            "ほかの切り口（前走・血統・マイニング予想・クラス別など）は `tools/成績集計/perf.py`（`--list` で一覧）で数える。", "",
            "## 4. ページの一覧", "",
            "1ページが競馬場×芝ダ×距離。その中がコース×馬場状態の節に分かれている。数字はレース数。",
        ]

    @staticmethod
    def _page_list(runs: pd.DataFrame) -> list[str]:
        races = runs.drop_duplicates("rid")
        counts = races.groupby(["venue_code", "surface", "distance", "going"]).size()
        pages = races[["venue_code", "surface", "distance"]].drop_duplicates()
        pages = pages.assign(order=pages["surface"].map(codes.SURFACE_ORDER)).sort_values(["venue_code", "order", "distance"])
        lines = []
        for venue, venue_pages in pages.groupby("venue_code", sort=True):
            lines.extend(["", f"### {codes.venue_name(venue)}", "",
                          "| コース・距離 | " + " | ".join(_LISTED_GOINGS) + " |",
                          "| :--- |" + " :--- |" * len(_LISTED_GOINGS)])
            lines.extend(_page_row(venue, surface, int(distance), counts)
                         for surface, distance in zip(venue_pages["surface"], venue_pages["distance"]))
        return lines


def _page_row(venue: str, surface: str, distance: int, counts: pd.Series) -> str:
    cells = [str(counts.get((venue, surface, distance, going), 0)) for going in _LISTED_GOINGS]
    return f"| [{surface} {distance}m]({page_name(venue, surface, distance)}) | " + " | ".join(cells) + " |"
