"""``Overview`` を、CLI と画面で同じ表（``render.Table``）にする。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from 共通 import card
from 共通.render import Table
from 取得と予想の状況.acquisition_day import AcquisitionDay
from 取得と予想の状況.day_status import DayStatus
from 取得と予想の状況.elapsed import ago_text, clock_text, stamp_text, until_text
from 取得と予想の状況.final_result_range import FinalResultRange
from 取得と予想の状況.local_store_status import LocalStoreStatus
from 取得と予想の状況.overview import Overview
from 取得と予想の状況.race_status import RaceStatus
from 取得と予想の状況.store_file import StoreFile
from 取得と予想の状況.sync_record import SyncRecord

#: 表の名前（画面がどの表かを見分けるのに使う）。
SUMMARY_TITLE = "今の状況"
DAYS_TITLE = "中央: 開催日ごとの取得と予想（今日以降）"
RACES_TITLE = "中央: レースごとの状況"
SYNC_TITLE = "中央: 同期の記録（jvdata-store がどこまで取ったか）"
LOCAL_DAYS_TITLE = "地方: 開催日ごとの取得（今日以降）"
LOCAL_SYNC_TITLE = "地方: 同期の記録（nvdata-store がどこまで取ったか）"
MODELS_TITLE = "学習済みモデル"
#: レースごとの表の判定の列（画面が色を付ける）。
VERDICT_COLUMN = "判定"
_DAYS_NOTE = ("数はレース数。「オッズあり」は締め切り前の単勝オッズが入ったレース、「馬体重あり」は半分以上の馬の馬体重が出たレース。"
              "「予想し直し」は、時点が進んだ・作り方が古い・オッズが新しいの合計。オッズ・馬体重・馬場状態は jvdata-store の「速報の取得」で入る。")
_LOCAL_DAYS_NOTE = ("数はレース数。地方は数日先までの出馬表がレース情報の取得（nvstore sync）で入り、オッズ・馬体重は速報の取得"
                    "（nvstore realtime）で入る。予想は地方を対象にしていないので、予想の数は出さない。")
_SYNC_NOTE = "蓄積系の取得（sync）の記録。速報（realtime）はここに残らないので、オッズ・馬体重の時刻で見る。"
_NO_UPCOMING = "無い（出走馬名表は木曜の夕方、出馬表は金・土に出る。そのあと jvdata-store の画面で「取得する」）"
_NO_LOCAL_UPCOMING = "無い（nvdata-store の画面で「取得する」と、数日先までの出馬表が入る）"
_NOT_READ = "（DB を読めていない）"


class OverviewTables:
    """``Overview`` を表にする: 今の状況（縦表）・中央の開催日ごと・中央のレースごと・中央の同期の記録・
    地方の開催日ごと・地方の同期の記録（地方を見るときだけ）・学習済みモデル。
    """

    def tables(self, overview: Overview) -> list[Table]:
        local = [self.local_days(overview.local), self.local_sync(overview.local, overview.now)] if overview.local else []
        return [self.summary(overview), self.days(overview), self.races(overview), self.sync(overview), *local, self.models(overview)]

    def summary(self, overview: Overview) -> Table:
        """「項目 | 値」の縦表。中央の行のあとに地方の行。"""
        rows: list[list[Any]] = [
            ["確かめた時刻", overview.now.strftime("%Y-%m-%d %H:%M:%S")],
            ["中央: jvdata-store の画面", overview.store.describe()],
            ["中央: DB のファイル", _file_text(overview.db_file, overview.now)],
            ["中央: DB の読み取り", _read_text(overview.db_error)],
            ["中央: 確定成績", _results_text(overview.results)],
            ["中央: 今日以降のレース", _upcoming_text(overview.db_error, [day.acquisition for day in overview.days], _NO_UPCOMING)],
            ["中央: 次の発走", self._next_race_text(overview)],
            ["中央: 学習済みモデル", self._models_text(overview)],
        ]
        if overview.local is not None:
            rows.extend(self._local_rows(overview.local, overview.now))
        return Table(["項目", "値"], rows, title=SUMMARY_TITLE)

    def days(self, overview: Overview) -> Table:
        columns = ["日付", "曜", "競馬場", "レース", "出走馬名表", "出馬表", "結果", "中止", "オッズあり", "最新のオッズ", "馬体重あり", "馬場発表",
                   "予想済み", "時点の内訳", "最新", "予想し直し", "未予想"]
        return Table(columns, [self._day_row(day) for day in overview.days], title=DAYS_TITLE, note=_DAYS_NOTE)

    def races(self, overview: Overview) -> Table:
        columns = ["場", "R", "発走", "レース名", "クラス", "状態", "馬番", "馬体重", "馬場", "オッズ", "今の時点", "予想の時点", "作成",
                   VERDICT_COLUMN, "印", "rid"]
        title = f"{RACES_TITLE}: {overview.day}（{card.weekday_of(overview.day)}）" if overview.day else RACES_TITLE
        note = ("「今の時点」は今の DB で予想すると選ばれる時点、「予想の時点」は作ってある予想の時点。判定が「最新」以外なら、"
                "今週の予想のタブで「予想し直す」か tools/今週の予想/run.bat で作り直す。" if overview.races else
                ("DB にその日のレースが無い。" if overview.day else "今日以降のレースが DB に無い。"))
        return Table(columns, [self._race_row(status) for status in overview.races], title=title, note=note)

    def sync(self, overview: Overview) -> Table:
        return Table(*_sync_parts(overview.sync_records, overview.now), title=SYNC_TITLE, note=_SYNC_NOTE)

    def local_days(self, local: LocalStoreStatus) -> Table:
        columns = ["日付", "曜", "競馬場", "レース", "出馬表", "結果", "中止", "オッズあり", "最新のオッズ", "馬体重あり"]
        rows = [[day.day, day.weekday, "・".join(day.venues), day.races, day.cards, day.finished, day.cancelled, day.with_odds,
                 clock_text(day.latest_odds_at), day.weighed] for day in local.days]
        return Table(columns, rows, title=LOCAL_DAYS_TITLE, note=_LOCAL_DAYS_NOTE)

    def local_sync(self, local: LocalStoreStatus, now: datetime) -> Table:
        return Table(*_sync_parts(local.sync_records, now), title=LOCAL_SYNC_TITLE, note=_SYNC_NOTE)

    def models(self, overview: Overview) -> Table:
        rows = [[model.yosou, model.relative, stamp_text(model.updated_at)] for model in overview.models]
        note = ("置き場所が無い予想: " + "、".join(overview.missing_model_roots) + "（train で作るまで、今週の予想は動かない）"
                if overview.missing_model_roots else "今週の予想（中央）が使うモデル。作り直したら、作ってある予想も作り直す（--skip-saved は版が同じなら飛ばす）。")
        return Table(["予想", "モデル", "最終更新"], rows, title=MODELS_TITLE, note=note)

    @staticmethod
    def _local_rows(local: LocalStoreStatus, now: datetime) -> list[list[Any]]:
        file_missing = not local.file.exists
        return [
            ["地方: nvdata-store の画面", local.store.describe()],
            ["地方: DB のファイル", _file_text(local.file, now)],
            ["地方: DB の読み取り", "（DB のファイルが無い）" if file_missing else _read_text(local.db_error)],
            ["地方: 確定成績", _NOT_READ if file_missing else _results_text(local.results)],
            ["地方: 今日以降のレース", _NOT_READ if file_missing else _upcoming_text(local.db_error, local.days, _NO_LOCAL_UPCOMING)],
        ]

    @staticmethod
    def _next_race_text(overview: Overview) -> str:
        today = overview.now.date().isoformat()
        if overview.db_error is not None:
            return _NOT_READ
        if overview.day != today:
            return "今日はレースが無い" if overview.day is None or not any(day.day == today for day in overview.days) else "（今日のレースを見ていない）"
        status = overview.next_race
        if status is None:
            return "今日の発走は全部終わった"
        signals = status.signals
        return (f"{signals.venue} {signals.race_no}R {signals.post_time}（{until_text(overview.now, signals.post_datetime())}） "
                f"{signals.race_name or signals.class_name} — 予想: {status.verdict.label}")

    @staticmethod
    def _models_text(overview: Overview) -> str:
        newest = max((model.updated_at for model in overview.models), default=None)
        text = f"{len(overview.models)} 個（最終更新 {stamp_text(newest)}）" if overview.models else "無い"
        if overview.missing_model_roots:
            text += "。置き場所が無い: " + "、".join(overview.missing_model_roots)
        return text

    @staticmethod
    def _day_row(day: DayStatus) -> list[Any]:
        acquired = day.acquisition
        return [acquired.day, acquired.weekday, "・".join(acquired.venues), acquired.races, acquired.name_lists, acquired.cards,
                acquired.finished, acquired.cancelled, acquired.with_odds, clock_text(acquired.latest_odds_at), acquired.weighed,
                acquired.going_announced, day.forecasted, day.timing_text(), day.fresh, day.redo, day.missing]

    @staticmethod
    def _race_row(status: RaceStatus) -> list[Any]:
        signals, verdict = status.signals, status.verdict
        odds = f"{signals.odds_count}頭 {clock_text(signals.odds_announced_datetime())}" if signals.has_odds else "無し"
        return [signals.venue, signals.race_no, signals.post_time or "", signals.race_name or "", signals.class_name, signals.stage_name,
                "決定" if signals.is_numbered else "未定", f"{signals.weighed}/{signals.entries}", signals.going, odds, verdict.current_timing,
                verdict.saved_timing or "", clock_text(verdict.made_at), verdict.label, verdict.marks, signals.rid]


def _file_text(file: StoreFile, now: datetime) -> str:
    if not file.exists:
        return f"無い: {file.path}"
    return f"{file.path}（{file.size_mb:,} MB、最終更新 {stamp_text(file.modified_at)} = {ago_text(now, file.modified_at)}）"


def _read_text(db_error: str | None) -> str:
    return "読めた" if db_error is None else f"読めない: {db_error}"


def _results_text(results: FinalResultRange | None) -> str:
    if results is None:
        return _NOT_READ
    if not results.races:
        return "まだ無い（過去のレース情報を取得する）"
    return f"{results.first_date} 〜 {results.last_date}（{results.races:,} レース）"


def _upcoming_text(db_error: str | None, days: list[AcquisitionDay], nothing: str) -> str:
    if db_error is not None:
        return _NOT_READ
    if not days:
        return nothing
    listed = "、".join(f"{day.day}（{day.weekday}）{day.races}" for day in days)
    return f"{sum(day.races for day in days)} レース: {listed}"


def _sync_parts(records: list[SyncRecord], now: datetime) -> tuple[list[str], list[list[Any]]]:
    """同期の記録の表の列と行。"""
    rows = [[record.dataspec, record.title, stamp_text(record.fetched_at) or record.raw, ago_text(now, record.fetched_at)] for record in records]
    return ["データ種別", "内容", "最後に取った時刻", "経過"], rows
