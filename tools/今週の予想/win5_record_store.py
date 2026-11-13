"""予想「近走と適性からWIN5の買い目を決める」の predict が自動で書いた記録（``記録/<開催日>.json``）を読む。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from yosou.form_aptitude_win5_tickets.repository import Win5ForecastRecordRepository

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.win5_record import Win5Record

#: 予想の名前（設計書のフォルダ名と同じ）。記録の置き場所 ``reports/<予想の名前>/記録/`` に使う。
#: 予想のパッケージの ``command/yosou_name.py`` と同じ名前（コマンドの部品まで読み込まないよう、ここにも書く）。
WIN5_YOSOU_NAME = "近走と適性からWIN5の買い目を決める"
#: keiba-yosou のリポジトリ直下（tools/今週の予想/ から2つ上）と、記録の置き場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = _PROJECT_ROOT / "reports" / WIN5_YOSOU_NAME


class Win5RecordStore:
    """1開催日の WIN5 の予想の記録を ``Win5Record`` にして返す（書くのは予想のパッケージの predict だけ）。

    ``beside`` は、今週の予想の置き場所（既定 ``reports/今週の予想``）と同じ階層の ``<予想の名前>`` を見る（テストで置き場所をまとめて替えられる）。
    """

    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._repository = Win5ForecastRecordRepository(Path(root))

    @classmethod
    def beside(cls, forecasts: ForecastStore) -> Win5RecordStore:
        return cls(forecasts.folder.parent / WIN5_YOSOU_NAME)

    def load(self, day: date) -> Win5Record | None:
        """その開催日の記録。WIN5 の予想をまだしていない日（WIN5 の無い日も）は None。"""
        try:
            return Win5Record.from_dict(self._repository.load(day))
        except FileNotFoundError:
            return None

    def made_at(self, day: date) -> str | None:
        """その開催日の記録の、予想した時刻（予想し直したかを見るのに使う）。無ければ None。"""
        record = self.load(day)
        return record.made_at if record else None
