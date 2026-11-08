"""道具「発走前の通知」が使う置き場所の定数。"""

from __future__ import annotations

from pathlib import Path

#: keiba-yosou（この道具が入っているリポジトリ）。
PROJECT = Path(__file__).resolve().parents[2]
#: 速報を取り込む jvdata-store（keiba-yosou の隣）。
STORE_PROJECT = PROJECT.parent / "jvdata-store"
#: 元DB のファイル名（jvdata-store の中）。
STORE_DB = "jvdata.duckdb"
#: 設定（ウェブフック URL）と記録を置く場所（Git 対象外）。
DEFAULT_FOLDER = PROJECT / "reports" / "発走前の通知"
#: 別プロセス（取り込み・予想）の出力を残す場所。
LOG_FOLDER = DEFAULT_FOLDER / "logs"
#: 中央の通知に添付する全頭の表の画像を置く場所（``<開催日>/<rid>.png``）。
CENTRAL_FOLDER = DEFAULT_FOLDER / "中央"
#: 今週の予想の入口（別プロセスで動かす）。
FORECAST_SCRIPT = PROJECT / "tools" / "今週の予想" / "forecast.py"
#: 地方の速報を取り込む nvdata-store（keiba-yosou の隣）。
LOCAL_STORE_PROJECT = PROJECT.parent / "nvdata-store"
#: 地方の元DB のファイル名（nvdata-store の中）。
LOCAL_STORE_DB = "nvdata.duckdb"
#: 地方の予想の結果（predict の JSON）を置く場所。
LOCAL_FOLDER = DEFAULT_FOLDER / "地方"
#: 地方の予想の入口（予想モデルの predict と荒れ具合の予想を同じ接続で出す。別プロセスで動かす）。
LOCAL_PREDICT_SCRIPT = PROJECT / "tools" / "発走前の通知" / "local_predict.py"
#: 地方の記録のファイル名の頭（中央の記録と分ける）。
LOCAL_LOG_NAME = "地方-"
#: WIN5 の予想（予想「近走と適性からWIN5の買い目を決める」の predict。予算と線は予想のパッケージの formation/buying_defaults.py の既定）。
WIN5_PROGRAM: tuple[str, ...] = ("python", "-m", "yosou.form_aptitude_win5_tickets", "predict")
#: WIN5 の予想の記録のファイル名の頭。
WIN5_LOG_NAME = "WIN5-"
#: 裏で動かす WIN5 の予想が読む、元DB の写しの置き場所（``<開催日>/jvdata.duckdb``。予想が終わったら消す）。
WIN5_SNAPSHOT_FOLDER = DEFAULT_FOLDER / "WIN5の元DBの写し"
