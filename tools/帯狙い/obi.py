"""帯狙い: 開催日ごとに「荒れる」と決めて買うレースを1つ選び、荒れる前提の予想で1レース 1万円の3連単の買い目を出す。

    uv run python tools/帯狙い/obi.py                        # 今日以降の開催日ぜんぶ（出馬表のあるもの）
    uv run python tools/帯狙い/obi.py --date 2026-10-18      # その日だけ
    uv run python tools/帯狙い/obi.py --plan 乙              # 買い方を替える（甲・乙・丙。既定は甲）
    uv run python tools/帯狙い/obi.py --models reports/近走と適性から3着以内を予想/models   # 今の予想のモデルで買い目を組む（比べるため）

予想は「荒れる前提で着順を予想」（設計書 docs/design/荒れる前提で着順を予想/）。
1. その日のレースごとに、荒れ具合の予想（reports/レースの荒れ具合を4段階で予想/models/）で3連単の超荒れ（50万円以上）の確率を出し、
   いちばん高いレースを選ぶ（1日1レース）。
2. 選んだレースを、荒れたレースだけで学んだ 3着以内と1着のモデル（reports/荒れる前提で着順を予想/models/）で予想する
   （印・危険な人気馬の判定は今週の予想と同じ部品）。
3. 締め切り前の組ごとのオッズで、1万円の買い目を組む。オッズが無ければ組まない（当日にもう一度動かす）。
時点（木曜・前日・当日）は、今週の予想と同じく DB に入っている情報から選ぶ。
買い目は参考である。研究「百万馬券を当てる」（docs/04）の確かめで、どの買い方も採用の基準に届かなかったので、
財布（reports/回顧/財布.json）にも買い目の記録にも書かない。買うかどうかは利用者が決める。
結果は reports/帯狙い/<開催日>.json と、今回の表を reports/帯狙い/最新.md にも書く。先に jvdata-store で出馬表と速報（オッズ）を取り込んでおく。
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import card, cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.dataset import OddsResolver  # noqa: E402
from yosou.shared.repository import AnnouncedOddsRepository  # noqa: E402
from yosou.upset_level.dataset import race_dataset_builder  # noqa: E402
from yosou.upset_level.workflow import PredictionWorkflow, model_repositories  # noqa: E402

from 今週の予想.model_folders import DEFAULT_FAVORITE_MODELS  # noqa: E402
from 今週の予想.race_forecaster import RaceForecaster  # noqa: E402
from 帯狙い.obi_day_picker import ObiDayPicker  # noqa: E402
from 帯狙い.obi_day_run import ObiDayRun  # noqa: E402
from 帯狙い.obi_plans import DEFAULT_PLAN, PLANS  # noqa: E402
from 帯狙い.obi_store import DEFAULT_FOLDER, ObiStore  # noqa: E402
from 帯狙い.obi_tables import ObiTables  # noqa: E402

#: 荒れる前提で着順を予想の学習済みモデルの既定の置き場所（予想の名前は yosou.upset_premise の YOSOU_NAME と同じ）。
DEFAULT_MODELS = HERE.parents[1] / "reports" / "荒れる前提で着順を予想" / "models"
#: レースを選ぶ荒れ具合の予想の学習済みモデルの既定の置き場所（予想の名前は yosou.upset_level の YOSOU_NAME と同じ）。
DEFAULT_UPSET_MODELS = HERE.parents[1] / "reports" / "レースの荒れ具合を4段階で予想" / "models"
_RID = card.CARD_LIST_HEADERS.index("rid")
#: いちばん新しい結果の表を書くファイルの名前（--open で開く）。
LATEST_PAGE = "最新.md"


def main(args) -> None:
    store = ObiStore(args.out_dir)
    tables: list[Table] = []
    with db.open_db(args.db) as con:
        upset = PredictionWorkflow(race_dataset_builder(con), model_repositories(args.upset_models), OddsResolver(AnnouncedOddsRepository(con)))
        run = ObiDayRun(ObiDayPicker(upset), RaceForecaster(args.models, args.favorite_models), PLANS[args.plan])
        for day in _days(con, args):
            print(f"{day} のレースを選んでいます …", file=sys.stderr, flush=True)
            result = run.run(con, day)
            store.save(day, result)
            tables += ObiTables().tables(result)
    cli.emit(tables, args)
    page = _write_page(store.folder, tables)
    print(f"\n保存先: {store.folder}", file=sys.stderr)
    if args.open:
        os.startfile(page)  # noqa: S606  Windows で既定のアプリ（Markdown を開くアプリ）で開く


def _write_page(folder: Path, tables: list[Table]) -> Path:
    """今回の結果の表を ``<置き場所>/最新.md`` に書く（ダブルクリック用の run.bat が開く）。"""
    folder.mkdir(parents=True, exist_ok=True)
    page = folder / LATEST_PAGE
    page.write_text(render.render(tables) + "\n", encoding="utf-8")
    return page


def _days(con, args) -> list[date]:
    """帯狙いをする開催日。``--date`` か、今日以降で出馬表のある開催日ぜんぶ。"""
    start = args.date or date.today().isoformat()
    listed = card.list_cards(con, date_from=start, date_to=args.date, limit=card.MAX_LIST_LIMIT)
    if not listed.rows:
        raise LookupError(f"{start} 以降のレースが DB にありません。jvdata-store で今週の出馬表を取り込んでください")
    return sorted({date(int(rid[:4]), int(rid[4:6]), int(rid[6:8])) for rid in (row[_RID] for row in listed.rows)})


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--date", default=None, help="開催日 YYYY-MM-DD（省略すると今日以降の開催日ぜんぶ）")
    parser.add_argument("--plan", choices=tuple(PLANS), default=DEFAULT_PLAN,
                        help=f"買い方（{' / '.join(f'{key}: {plan.name}' for key, plan in PLANS.items())}。既定: {DEFAULT_PLAN}）")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS, help="荒れる前提で着順を予想の学習済みモデルの置き場所")
    parser.add_argument("--upset-models", type=Path, default=DEFAULT_UPSET_MODELS, help="レースを選ぶ荒れ具合の予想の学習済みモデルの置き場所")
    parser.add_argument("--favorite-models", type=Path, default=DEFAULT_FAVORITE_MODELS, help="危険な人気馬を判定する予想の学習済みモデルの置き場所")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_FOLDER, help="結果を書く置き場所（既定: reports/帯狙い）")
    parser.add_argument("--open", action="store_true", help="終わったら、結果の表（<置き場所>/最新.md）を既定のアプリで開く")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
