"""地方の推奨買目: 1レースの推奨買目（単勝・複勝・枠連・馬連・ワイド・馬単・3連複・3連単。1点 100円）を、全頭の予想の結果と最新のオッズから出す。

    uv run python tools/地方の推奨買目/recommend.py 2026110550170505                       # 発走前の通知が保存した予想（reports/発走前の通知/地方/<開催日>/<rid>.json）から
    uv run python tools/地方の推奨買目/recommend.py 2026110550170505 --forecast 予想.json   # predict --format json --out で書いた結果から
    uv run python tools/地方の推奨買目/recommend.py 2026110550170505 --format json --out 買い目.json

予想の結果は、地方の予想モデル（yosou.local_form_aptitude_top3）の predict（当日か前日の時点。モデルごとの 1着の確率つき）の JSON。
オッズは元DB の最新の発表（発走前なら速報 0B30 を取り込んでから）。係数は reports/地方の推奨買目/係数.json（fit.py で当てはめる）。
頭数の線は券種ごと（複勝・馬単・3連複・3連単は 8頭以上、馬連は 11頭以上。単勝・枠連・ワイドは問わない）。馬連は 人気馬（1〜3番人気）× 中穴（4〜7番人気）の組だけ。
3連複は、地方の荒れ具合の予想（yosou.local_upset_level。モデルは reports/地方のレースの荒れ具合を4段階で予想/models）の 3連複の中荒れ以上の確率が
0.6 以上のレースだけ、期待値の上位 3点。荒れ具合の予想が出せない（モデルが無い・馬体重がまだ無い）ときは、3連複だけを対象外にして理由に添える。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.local_upset_level.workflow import DEFAULT_CACHE_DIR as UPSET_CACHE_DIR, DEFAULT_MODELS_DIR as UPSET_MODELS_DIR, LocalUpsetForecast  # noqa: E402

from 地方の推奨買目.coefficient_store import DEFAULT_PATH, CoefficientStore  # noqa: E402
from 地方の推奨買目.recommendation_set import RecommendationSet  # noqa: E402
from 地方の推奨買目.recommender import Recommender  # noqa: E402
from 地方の推奨買目.upset_probabilities import UpsetProbabilities  # noqa: E402

_PROJECT = _TOOLS.parent
NOTIFY_FOLDER = _PROJECT / "reports" / "発走前の通知" / "地方"


def main(args: argparse.Namespace) -> None:
    forecast_path = args.forecast or NOTIFY_FOLDER / f"{args.rid[:4]}-{args.rid[4:6]}-{args.rid[6:8]}" / f"{args.rid}.json"
    if not forecast_path.is_file():
        raise FileNotFoundError(f"予想の結果がありません: {forecast_path}")
    forecast = json.loads(forecast_path.read_text(encoding="utf-8"))
    coefficients = CoefficientStore(args.coefficients).load()
    upsets = UpsetProbabilities(LocalUpsetForecast(args.upset_models, args.upset_cache))
    with db.open_db(args.db, default=db.LOCAL) as con:
        chosen = Recommender(con, coefficients, upsets=upsets).recommend(args.rid, forecast)
    render.write(render.render(table_of(args.rid, chosen), args.format), args.out, fmt=args.format)


def table_of(rid: str, chosen: RecommendationSet) -> Table:
    rows = [[row.ticket, row.label, round(row.odds, 1), round(row.probability, 4), round(row.value, 2), row.yen] for row in chosen.rows]
    note = f"合計 {chosen.points} 点 {chosen.yen:,}円。1点 100円。期待値は 組の確率 × 最新のオッズ（複勝・ワイドは幅の真ん中）。" if rows else f"推奨買目なし（{chosen.reason}）。"
    return Table(["券種", "買い目", "オッズ", "確率", "期待値", "金額"], rows, title=f"{rid} の推奨買目", note=note)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("rid", help="レースの rid（16桁）")
    parser.add_argument("--forecast", type=Path, default=None, help="全頭の予想の結果（predict --format json の JSON。既定: 発走前の通知が保存したもの）")
    parser.add_argument("--coefficients", type=Path, default=DEFAULT_PATH, help=f"係数の JSON（既定: {DEFAULT_PATH}）")
    parser.add_argument("--upset-models", type=Path, default=UPSET_MODELS_DIR, help=f"地方の荒れ具合の予想の学習したモデルの置き場所（既定: {UPSET_MODELS_DIR}）")
    parser.add_argument("--upset-cache", type=Path, default=UPSET_CACHE_DIR, help=f"地方の荒れ具合の予想の過去の傾きの表の置き場所（既定: {UPSET_CACHE_DIR}）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--format", choices=render.FORMATS, default=render.DEFAULT_FORMAT, help="出力の形式")
    parser.add_argument("--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
