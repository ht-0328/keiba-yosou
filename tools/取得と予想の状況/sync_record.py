"""同期の記録（jvdata-store・nvdata-store がデータ種別ごとにどこまで取ったか）の1行。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: ``_meta`` の鍵の接頭辞（jvdata-store・nvdata-store の ``sync`` が ``sync:RACE`` のように書く）。
SYNC_PREFIX = "sync:"
#: 中央の蓄積系のデータ種別の説明（jvdata-store の README「取得する範囲」と同じ）。知らない種別は ID のまま出す。
JRA_DATASPEC_TITLES: dict[str, str] = {
    "RACE": "レース情報", "DIFN": "蓄積情報（馬・騎手・調教師 …）", "BLDN": "血統情報", "SNPN": "出走時点情報", "MING": "マイニング予想",
    "SLOP": "坂路調教", "WOOD": "ウッドチップ調教", "YSCH": "開催スケジュール", "HOSN": "競走馬市場取引価格", "HOYU": "馬名の意味由来",
    "COMM": "コース情報", "TOKU": "特別登録馬",
}
#: 地方の蓄積系のデータ種別の説明（nvdata-store の README「取得する範囲」と同じ）。
LOCAL_DATASPEC_TITLES: dict[str, str] = {
    "RACE": "レース情報（出馬表・成績・払戻・オッズ）", "DIFN": "マスタ（馬・騎手・調教師 …）", "SNAP": "出走別着度数",
    "DIFF": "生産者マスタ",
}
#: 記録の時刻の桁数（``YYYYMMDDHHMMSS``）。
_STAMP_LENGTH = 14


@dataclass(frozen=True)
class SyncRecord:
    """1つのデータ種別を、最後にどこまで取ったか。``fetched_at`` は取得の仕組みが返した最も新しいファイルの時刻。"""

    dataspec: str
    title: str
    fetched_at: datetime | None
    raw: str

    @classmethod
    def from_meta(cls, meta: dict[str, str], titles: dict[str, str]) -> list["SyncRecord"]:
        """``_meta`` の鍵と値から、同期の記録だけを取り出す（データ種別の順）。``titles`` はデータ種別の説明。"""
        synced = {key[len(SYNC_PREFIX):]: value for key, value in sorted(meta.items()) if key.startswith(SYNC_PREFIX)}
        return [cls(dataspec, titles.get(dataspec, dataspec), _parse_stamp(value), value) for dataspec, value in synced.items()]


def _parse_stamp(text: str) -> datetime | None:
    """``20260906120000`` を日時に。形が違えば None。"""
    if len(text) != _STAMP_LENGTH or not text.isdigit():
        return None
    try:
        return datetime.strptime(text, "%Y%m%d%H%M%S")
    except ValueError:
        return None
