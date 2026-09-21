"""傾向スコアの結果を、グラフ付きの HTML 1ファイルにする。

描くのは ``static/trend.js``（検索画面のタブと同じ部品）。ここは、結果（``TrendReport.to_dict()``）とその部品を
1つのファイルに埋めるだけ。ファイルはブラウザで開けば見られ、サーバーもネットワークも要らない。
馬名などを含むので、書き出す先は ``reports/``（Git 対象外）にする。
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

#: 画面の部品の置き場。検索画面のサーバーもここから配る。
STATIC_DIR = Path(__file__).resolve().parent / "static"
TREND_SCRIPT = STATIC_DIR / "trend.js"

_PAGE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #100e0b; color: #f2ece1; font-family: "Zen Kaku Gothic New", "Hiragino Sans", "Yu Gothic UI", Meiryo, system-ui, sans-serif; }}
  main {{ padding: 16px 18px 40px; max-width: 1600px; margin: 0 auto; }}
</style>
</head>
<body>
<main id="main"></main>
<script type="application/json" id="trend-data">{data}</script>
<script>
{script}
</script>
<script>
TrendView.render(document.getElementById("main"), JSON.parse(document.getElementById("trend-data").textContent));
</script>
</body>
</html>
"""


def _embed_json(payload: dict[str, Any]) -> str:
    """``<script>`` の中に置ける JSON。``</script>`` や ``<!--`` で途中で閉じないように ``<`` を逃がす。"""
    return json.dumps(payload, ensure_ascii=False, default=str).replace("<", "\\u003c")


def standalone(payload: dict[str, Any]) -> str:
    """結果の辞書から、単体で開ける HTML を作る。"""
    return _PAGE.format(title=html.escape("傾向スコア: " + str(payload.get("title", ""))), data=_embed_json(payload),
                        script=TREND_SCRIPT.read_text(encoding="utf-8"))


_INDEX_PAGE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #100e0b; color: #f2ece1; font-size: 14px; line-height: 1.6;
         font-family: "Zen Kaku Gothic New", "Hiragino Sans", "Yu Gothic UI", Meiryo, system-ui, sans-serif; }}
  main {{ padding: 16px 18px 40px; max-width: 1500px; margin: 0 auto; }}
  h1 {{ font-size: 18px; font-weight: 600; margin: 0 0 4px; }} h2 {{ font-size: 16px; font-weight: 600; margin: 18px 0 8px; }}
  p {{ color: #a1968a; font-size: 13px; margin: 0 0 8px; }}
  .races {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 10px; }}
  a.race {{ display: block; background: #1a1712; border: 1px solid #332c22; border-radius: 10px; padding: 10px 14px; color: inherit; text-decoration: none; }}
  a.race:hover {{ border-color: #d8b268; }}
  .race b {{ color: #d8b268; margin-right: 8px; }} .race small {{ color: #a1968a; display: block; }}
  ol {{ margin: 6px 0 0; padding-left: 22px; }} li {{ font-variant-numeric: tabular-nums; }} li span {{ color: #a1968a; margin-left: 6px; }}
</style>
</head>
<body><main>
<h1>{title}</h1>
<p>{note}</p>
{sections}
</main></body>
</html>
"""
#: 一覧のページで、レースごとに出す上位の頭数。
INDEX_TOP = 5


def index_page(title: str, note: str, races: list[dict[str, Any]]) -> str:
    """その日のレースの一覧のページ。``races`` は ``{"venue", "file", "label", "sub", "top": [(馬番, 馬名, 点), ...]}`` の並び（馬番が未定なら空文字）。"""
    sections = []
    for venue in dict.fromkeys(item["venue"] for item in races):
        cards = []
        for item in (r for r in races if r["venue"] == venue):
            top = "".join(f"<li>{html.escape(str(no) + ' ' + name).strip()}<span>{score:+d}</span></li>" for no, name, score in item["top"])
            cards.append(f'<a class="race" href="{html.escape(item["file"])}"><b>{html.escape(item["label"])}</b>'
                         f'<small>{html.escape(item["sub"])}</small><ol>{top}</ol></a>')
        sections.append(f'<h2>{html.escape(venue)}</h2><div class="races">{"".join(cards)}</div>')
    return _INDEX_PAGE.format(title=html.escape(title), note=html.escape(note), sections="".join(sections))
