"""基準のページの目次（``index.md``）を書く。対象の期間・見方・作り方・数え方の約束と、ページの一覧。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import codes

from 成績集計.reference_page_writer import GOING_ORDER, page_name

INDEX_NAME = "index.md"
#: 目次のページの一覧に出す馬場状態（「不明」は出さない）。
_LISTED_GOINGS: tuple[str, ...] = GOING_ORDER[:4]

_COLUMNS_TEXT = [
    "**成績**は次の7つ。表では「出走数」「着別度数」「6つの率」の順に並べる。", "",
    "| 列 | 意味 |", "| :--- | :--- |",
    "| 出走数 | その条件で出走した頭数（延べ） |",
    "| 着別度数 | `1着-2着-3着-着外` の回数。`12-8-5-40` なら 1着12回・2着8回・3着5回・4着以下40回 |",
    "| 勝率 | 1着 ÷ 出走数 |", "| 連対率 | 2着以内 ÷ 出走数 |", "| 複勝率 | 3着以内 ÷ 出走数 |",
    "| 馬券外率 | 4着以下（競走中止・失格を含む）÷ 出走数。複勝率の裏返し |",
    "| 単勝回収率 | 単勝の払戻合計 ÷（出走数 × 100円）。全頭に100円ずつ単勝を買ったときの戻り |",
    "| 複勝回収率 | 複勝の払戻合計 ÷（出走数 × 100円） |",
]
_TABLES_TEXT = [
    "**各ページの節（コース×馬場状態）に入っている表。**", "",
    "| 表 | 内容 |", "| :--- | :--- |",
    "| 単勝人気・枠番・馬番・単勝オッズ | その値ごとの成績。1番人気の行が「このコースの1番人気」の成績。"
    "**馬番の大きい行は多頭数のレースにしか無い**ので、勝率の基準（1÷頭数）が小さい馬番より低めに出る |",
    "| 騎手・調教師・父・父の父・母父 | **勝率の上位10**（同点は連対率→複勝率→出走数）。出走5以上に限る。"
    "血統の記録が無い馬の父などは「不明」にまとめる |",
    "| 馬 | **勝率の上位10頭**。出走2以上に限る（同じコースを何度も走る馬は少ないため） |",
    "| 脚質・上がり3F順位・上がり3Fタイム | レースが終わってから分かる値。傾向を知るためのもので、そのまま予想の条件にはできない。"
    "上がり3F順位は、そのレースの出走馬の中で速い順（同じタイムは同じ順位） |",
    "| 性別 | **牡（セン）と牝が混ざったレースだけ**で数える。牝馬限定戦では全馬が牝で、比べる相手がいないため |",
    "| 馬齢 | **年齢が混ざったレースだけ**で数える。2歳戦・3歳限定戦では全馬が同じ年齢で、勝率が 1÷頭数 になるため |",
    "| 馬体重・馬体重の増減・前走からの間隔・前走の着順・前走の人気 | その値ごとの成績。値が無い出走は「不明」（前走の表は"
    "「前走なし・不明」）の行に入る |",
    "| データマイニング予想の範囲 | その節で、タイム型・対戦型の予想があるレースの数と期間。このあとの予想の表は、**予想がある出走だけ**を数える |",
    "| タイム型順位・対戦型順位・対戦型スコア | **データマイニング予想**（JV-Data の `DM`・`TM`）の値ごとの成績。"
    "タイム型は `SE` の `マイニング予想順位`（予想タイムの速い順）、対戦型は `TM` の予測スコアの高い順にレース内で付けた順位"
    "（同点は同じ順位なので、1位が2頭いるレースがある） |",
    "| タイム型順位と人気の差・対戦型順位と人気の差 | 順位 − 人気。「人気より3つ以上高評価」は、たとえば6番人気でタイム型3位以内 |",
    "| タイム型×対戦型 | タイム型と対戦型の順位を、それぞれ 1位 / 2〜3位 / 4位以下 に分けた組み合わせ |",
    "| 人気帯×タイム型・人気帯×対戦型 | 人気帯（1番人気・2番人気・3番人気・4番人気以下）×マイニング予想（1位 / 2〜3位 / 4位以下）の成績 |",
    "| クラス別 × 人気・出走頭数別 × 人気・月別 × 人気 | **クラス（頭数・月）の値ごとに、人気を行にした成績の表**。"
    "クラス・頭数・月はレースの属性なので、全馬で率を出すと勝率が必ず 1÷頭数 になり意味を持たない。そのため人気で分けて出す |",
    "| クラス別・出走頭数別・月別 × 人気帯 × タイム型（対戦型） | 値ごとに、人気帯×マイニング予想（1位 / 2〜3位 / 4位以下）の成績。"
    "標本が小さくなるので、順位は粗く分ける |",
    "",
    "**データマイニング予想はいつの値か。** JV-Data 仕様書の「データ提供タイミング」にあるとおり、貯まっている予想は"
    "**直前予想（馬体重発表後）時点**の値で、発走前に分かる。人気・オッズは確定値なので、マイニング予想の表は"
    "**発走直前に見る**状況にあたる。",
]
_RULES_TEXT = [
    "- 対象は中央競馬（競馬場コード 01 札幌〜10 小倉）で、`ra`・`se` のデータ区分が 5・6（速報成績。全馬の着順が確定）"
    "か 7（月曜の成績）の出走。",
    "- 出走取消・発走除外・競走除外（異常区分 1・2・3）は出走に数えない。競走中止・失格（4・5）は「出走して馬券外」。",
    "- 着別度数は確定着順（降着のあとの着順）で数える。同着はどちらも同じ着に数える。",
    "- 人気・オッズは確定値（`se` の `単勝人気順`・`単勝オッズ`）。払戻は `hr` の単勝・複勝（100円あたり）。同着の払戻は馬番ごとに付く。",
    "- 馬場状態は、ダートのコースならダートの、芝と障害なら芝の馬場状態（芝が空ならダート）。"
    "「コース」はトラックコードの名前（芝・左 など）。",
    "- 「前走」は、この DB にある中央の確定成績で、同じ馬が1つ前に出走したレース（取消・除外のレースは数えない）。"
    "**DB の最初の数か月（2011年の初め）は、それより前の出走が DB に無いので、前走なしの馬が多い。**",
    "- データマイニング予想（タイム型・対戦型）は、DB に 2011年1月から入っているので、成績と同じ期間で数える。",
    "- 回収率の基準は 80%（単勝・複勝の控除率 20%）。ランダムに買うとここに近づく。",
    "- レース数の少ない節（重・不良など）や、細かく分けた行は率が振れやすい。出走数を見てから読む。",
]


class ReferenceIndexWriter:
    """``ReferenceRuns`` の表から、目次を ``out_dir/index.md`` に書く。"""

    def __init__(self, made_on: str) -> None:
        self._made_on = made_on

    def write(self, runs: pd.DataFrame, out_dir: Path) -> Path:
        path = out_dir / INDEX_NAME
        path.write_text("\n".join([*self._intro(runs), *self._page_list(runs), *self._commands()]) + "\n", encoding="utf-8")
        return path

    def _intro(self, runs: pd.DataFrame) -> list[str]:
        return [
            "# 基礎統計 — 競馬場×コース×距離×馬場状態ごとの成績", "",
            "!!! warning \"公開しない\"", "",
            "    この表は JRA-VAN Data Lab. のデータから作ったもので、馬名・騎手名・血統名と払戻を含む。",
            "    `reports/` は Git 対象外にしてあり、公開リポジトリには載せない。", "",
            "**どのコースで、どんな条件の馬が、どれだけ勝ち、どれだけ回収できているか**を、JV-Data の確定成績から"
            "コースの単位（競馬場×コース×距離×馬場状態）ごとに数えたもの。理論を作る前に「このコースではふつうどうなのか」を"
            "知るための基準値として使う。`tools/成績集計/perf.py --check`（答え合わせ）の基準でもある。", "",
            f"対象: 中央競馬 {runs['race_date'].min()} 〜 {runs['race_date'].max()}、"
            f"{runs['rid'].nunique():,} レース・延べ {len(runs):,} 頭（平地・障害とも）。",
            f"`tools/成績集計/build_pages.py` が作る（作成日 {self._made_on}）。**手で直さない。**", "",
            "## 1. 見方", "", *_COLUMNS_TEXT, "", *_TABLES_TEXT, "",
            "**数え方の約束。**", "", *_RULES_TEXT, "",
            "**作り方（答え合わせの基準にするため、集計の道具とは別の道筋で数える）。**"
            "`perf.py` は事実表（`tools/共通/facts.py` の SQL）と `tools/共通/perf.py` の集計で数える。"
            "このページはそのどちらも使わず、元DB の `se`・`ra`・`hr__単勝払戻`・`hr__複勝払戻`・`um__3代血統情報`・"
            "`tm__マイニング予想` を直接読んで（`tools/成績集計/repository/`）、pandas で数える"
            "（`reference_runs.py`・`reference_history.py`・`reference_labels.py`・`reference_tally.py`）。"
            "数え方の約束は JV-Data 仕様書から決め直した。同じ約束を別の書き方で数えて同じ値になれば、どちらの集計も正しいと考えられる。", "",
            "## 2. ページの一覧", "",
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

    @staticmethod
    def _commands() -> list[str]:
        return [
            "", "## 3. 自分で数える", "",
            "表はどれも `tools/成績集計/perf.py` で、条件を足して数え直せる（切り口の一覧は `--list`）。", "",
            "```powershell",
            "uv run python tools/成績集計/perf.py horse --venue 京都 --course 芝・右 --distance 2000 --condition 良   # 勝率の高い馬10頭",
            "uv run python tools/成績集計/perf.py dm-rank --venue 京都 --course 芝・右 --distance 2000 --condition 良 # タイム型順位別",
            "uv run python tools/成績集計/perf.py class --cross popularity-top --cross tm-top --venue 京都 --course 芝・右 --distance 2000",
            "uv run python tools/成績集計/build_pages.py                                                     # このページを作り直す",
            "```",
        ]


def _page_row(venue: str, surface: str, distance: int, counts: pd.Series) -> str:
    cells = [str(counts.get((venue, surface, distance, going), 0)) for going in _LISTED_GOINGS]
    return f"| [{surface} {distance}m]({page_name(venue, surface, distance)}) | " + " | ".join(cells) + " |"
