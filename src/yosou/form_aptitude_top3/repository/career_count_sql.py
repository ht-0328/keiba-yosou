"""出走別着度数（ck）から、そのレースの条件に合う欄の着回数を取り出す SQL の式。"""

from __future__ import annotations

from itertools import product

from 共通 import codes, keys

#: ck の1つの欄。（そのレースが当てはまる条件の SQL, 欄の名前）。
#: 例: ("t.venue = '東京' AND t.surface = '芝'", "東京芝・着回数")
Cell = tuple[str, str]

#: 1つの欄は、1着〜5着と着外の6つの列（「東京芝・着回数_1」〜「東京芝・着回数_6」）を持つ。
_SLOTS = 6
#: 1着から何番目までの列を足すか。6つ全部で出走数、3つで3着以内の数、1つで勝利数。
_RUNS, _PLACES, _WINS = 6, 3, 1
_TOTAL_ITEM = "中央合計着回数"
_ITEM_SUFFIX = "・着回数"
#: 芝ダ → ck の欄の名前での書き方。
_SURFACES: dict[str, str] = {"芝": "芝", "ダート": "ダ"}
#: 馬場状態コード → ck の欄の名前での書き方。
_GOINGS: dict[str, str] = {"1": "良", "2": "稍", "3": "重", "4": "不"}
#: 距離帯。（その距離帯のいちばん長い距離, ck の欄の名前での書き方）。最後の帯は上限なし。
_DISTANCE_BANDS: tuple[tuple[int | None, str], ...] = (
    (1200, "1200以下"), (1400, "1201-1400"), (1600, "1401-1600"), (1800, "1601-1800"),
    (2000, "1801-2000"), (2200, "2001-2200"), (2400, "2201-2400"), (2800, "2401-2800"),
    (None, "2801以上"),
)


class CareerCountSql:
    """ck の着回数を、そのレースの条件（競馬場・芝ダ・距離・馬場状態）に合う欄から取り出す式を作る。

    ``ck`` は ck の行の別名、``entry`` は出走の行（事実表の列）の別名。
    """

    def __init__(self, ck: str, entry: str) -> None:
        self._ck = ck
        self._entry = entry

    def source_columns(self) -> tuple[str, ...]:
        """ck の表から読む着回数の列。"""
        cells = [*self._venue_cells(), *self._distance_band_cells(), *self._going_cells()]
        items = [_TOTAL_ITEM, *(item for _, item in cells)]
        return tuple(f"{item}_{slot}" for item, slot in product(items, range(1, _SLOTS + 1)))

    def select_list(self) -> str:
        """SELECT に並べる式。通算と、競馬場・距離帯・馬場状態ごとの、出走数と3着以内の数。"""
        expressions = {
            "ck_total_runs": self._sum(_TOTAL_ITEM, _RUNS),
            "ck_total_wins": self._sum(_TOTAL_ITEM, _WINS),
            "ck_total_places": self._sum(_TOTAL_ITEM, _PLACES),
            "ck_venue_runs": self._case(self._venue_cells(), _RUNS),
            "ck_venue_places": self._case(self._venue_cells(), _PLACES),
            "ck_band_runs": self._case(self._distance_band_cells(), _RUNS),
            "ck_band_places": self._case(self._distance_band_cells(), _PLACES),
            "ck_going_runs": self._case(self._going_cells(), _RUNS),
            "ck_going_places": self._case(self._going_cells(), _PLACES),
        }
        return ",\n".join(f"{expression} AS {name}" for name, expression in expressions.items())

    def _venue_cells(self) -> list[Cell]:
        """競馬場 × 芝ダ の欄（例: 東京芝）。"""
        pairs = product(codes.VENUE_NAMES.values(), _SURFACES.items())
        return [self._venue_cell(venue, surface, prefix) for venue, (surface, prefix) in pairs]

    def _venue_cell(self, venue: str, surface: str, prefix: str) -> Cell:
        entry = self._entry
        condition = f"{entry}.venue = '{venue}' AND {entry}.surface = '{surface}'"
        return condition, f"{venue}{prefix}{_ITEM_SUFFIX}"

    def _distance_band_cells(self) -> list[Cell]:
        """芝ダ × 距離帯 の欄（例: 芝1401-1600）。CASE は上から順に見るので、距離帯は短い順に並べる。"""
        pairs = product(_SURFACES.items(), _DISTANCE_BANDS)
        return [self._distance_band_cell(surface, prefix, longest, band)
                for (surface, prefix), (longest, band) in pairs]

    def _distance_band_cell(self, surface: str, prefix: str, longest: int | None, band: str) -> Cell:
        entry = self._entry
        within_band = "" if longest is None else f" AND {entry}.distance_m <= {longest}"
        condition = f"{entry}.surface = '{surface}'{within_band}"
        return condition, f"{prefix}{band}{_ITEM_SUFFIX}"

    def _going_cells(self) -> list[Cell]:
        """芝ダ × 馬場状態 の欄（例: 芝良）。馬場状態が分からなければ、どの欄にも当てはまらない。"""
        pairs = product(_SURFACES.items(), _GOINGS.items())
        return [self._going_cell(surface, prefix, code, going)
                for (surface, prefix), (code, going) in pairs]

    def _going_cell(self, surface: str, prefix: str, code: str, going: str) -> Cell:
        entry = self._entry
        condition = f"{entry}.surface = '{surface}' AND {entry}.condition_code = '{code}'"
        return condition, f"{prefix}{going}{_ITEM_SUFFIX}"

    def _case(self, cells: list[Cell], slots: int) -> str:
        """当てはまる欄の着回数。どの欄にも当てはまらなければ NULL（障害レースなど）。"""
        whens = [f"WHEN {condition} THEN {self._sum(item, slots)}" for condition, item in cells]
        return "CASE " + " ".join(whens) + " END"

    def _sum(self, item: str, slots: int) -> str:
        """欄 ``item`` の、1着から ``slots`` 番目までの着回数の合計。"""
        columns = [keys.q(f"{item}_{slot}") for slot in range(1, slots + 1)]
        counts = [f"TRY_CAST({self._ck}.{column} AS INTEGER)" for column in columns]
        return "(" + " + ".join(counts) + ")"
