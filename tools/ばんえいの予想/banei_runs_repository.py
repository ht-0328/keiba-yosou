"""ばんえい（帯広・競馬場コード 83）の出走を、地方の元DB から読んで数に直す。

読むのは2つ: 確定した成績の全部（過去走の材料）と、これから走る1レースの出馬表（取消・騎手変更・馬体重・馬場水分の速報を重ねる）。
ばんえいの元データは、負担重量（そりの重さ）と馬体重が16進3桁、馬場水分が「芝馬場状態コード＋ダート馬場状態コード」の16進2桁（10倍の値）で入っている。
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

BANEI_VENUE_CODE = "83"
_RID = 'r.開催年 || r.開催月日 || r.競馬場コード || r."開催回[第N回]" || r."開催日目[N日目]" || r.レース番号'
_RACE_KEY = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'
_COLUMNS = f"""
  {_RID} AS rid, r.開催年 || r.開催月日 AS ymd, r.レース番号 AS race_no, r.発走時刻 AS post,
  r.競走名本題 AS race_name, r.競走条件名称 AS cond_name, r.グレードコード AS grade, r.競走種別コード AS kind,
  r.重量種別コード AS weight_rule, r.本賞金_1 AS prize1, r.天候コード AS weather,
  r.芝馬場状態コード AS w_hi, r.ダート馬場状態コード AS w_lo,
  s.枠番 AS waku, s.馬番 AS umaban, s.血統登録番号 AS hid, s.馬名 AS name, s.性別コード AS sex, s.馬齢 AS age,
  s.調教師コード AS trainer, s.騎手コード AS jockey, s.負担重量 AS load_hex, s.馬体重 AS bw_hex, s.増減符号 AS bw_sign,
  s.増減差 AS bw_diff, s.異常区分コード AS abnormal, s.確定着順 AS finish, s.走破タイム AS time_raw,
  s.単勝オッズ AS win_odds, s.単勝人気順 AS pop
"""
#: 確定した成績（データ区分 7）の全部。
_CONFIRMED_SQL = f"""
SELECT {_COLUMNS}
FROM se s JOIN ra r USING ({_RACE_KEY})
WHERE s.競馬場コード = '{BANEI_VENUE_CODE}' AND s.データ区分 = '7' AND r.データ区分 = '7'
"""
#: 1レースの出馬表。同じ馬の行が複数あれば（出馬表 → 成績）データ区分の新しい方だけ。
_CARD_SQL = f"""
SELECT {_COLUMNS}
FROM se s JOIN ra r USING ({_RACE_KEY})
WHERE {_RID} = ?
QUALIFY row_number() OVER (PARTITION BY s.馬番 ORDER BY s.データ区分 DESC, s.データ作成年月日 DESC, r.データ区分 DESC, r.データ作成年月日 DESC) = 1
"""
_RACE_WHERE = '開催年 || 開催月日 || 競馬場コード || "開催回[第N回]" || "開催日目[N日目]" || レース番号 = ?'
_DAY_WHERE = "開催年 || 開催月日 || 競馬場コード = ?"
_SCRATCH_SQL = f"SELECT 馬番 FROM av WHERE {_RACE_WHERE}"
_JOCKEY_SQL = f"SELECT 馬番, 騎手コード FROM jc WHERE {_RACE_WHERE} ORDER BY 発表月日時分"
_WEIGHT_SQL = f'SELECT 馬番, 馬体重, 増減符号, 増減差 FROM "wh__馬体重情報" WHERE {_RACE_WHERE} ORDER BY _連番'
_TRACK_SQL = f'SELECT 天候状態, "馬場状態・芝", "馬場状態・ダート" FROM we WHERE {_DAY_WHERE} ORDER BY データ作成年月日, 発表月日時分'
#: 馬体重として読む範囲（kg）。外れた値（未発表の 000・FFF など）は欠損にする。
_BODY_WEIGHT_RANGE = (500, 1400)


class BaneiRunsRepository:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def confirmed(self, exclude_rid: str = "") -> pd.DataFrame:
        """確定した出走の全部（1行 = 1頭）。``exclude_rid`` のレースは入れない（予想するレースが確定済みでも、答えを材料にしない）。"""
        frame = self._decode(self._con.execute(_CONFIRMED_SQL).df())
        return frame[frame["rid"] != exclude_rid].reset_index(drop=True)

    def card(self, rid: str) -> pd.DataFrame:
        """これから走る1レースの出走馬（結果の列は欠損にする）。取消の馬を除き、騎手変更・馬体重・馬場水分・天候の速報を重ねる。"""
        raw = self._con.execute(_CARD_SQL, [rid]).df()
        if raw.empty:
            raise LookupError(f"{rid} の出馬表が元DB にありません")
        frame = self._decode(raw)
        frame[["finish", "time", "win_odds", "pop"]] = np.nan
        frame["abnormal"] = 0
        scratched = {int(number) for (number,) in self._rows(_SCRATCH_SQL, [rid]) if str(number).strip().isdigit()}
        frame = frame[~frame["umaban"].isin(scratched)].reset_index(drop=True)
        self._overlay_jockeys(frame, rid)
        self._overlay_weights(frame, rid)
        self._overlay_track(frame, rid)
        return frame

    def _rows(self, sql: str, parameters: list[str]) -> list[tuple]:
        """速報の表がまだ元DB に無い（1度も取り込んでいない）ときは空。"""
        try:
            return self._con.execute(sql, parameters).fetchall()
        except duckdb.CatalogException:
            return []

    def _overlay_jockeys(self, frame: pd.DataFrame, rid: str) -> None:
        for number, jockey in self._rows(_JOCKEY_SQL, [rid]):
            if str(number).strip().isdigit() and str(jockey).strip():
                frame.loc[frame["umaban"] == int(number), "jockey"] = str(jockey)

    def _overlay_weights(self, frame: pd.DataFrame, rid: str) -> None:
        for number, weight, sign, diff in self._rows(_WEIGHT_SQL, [rid]):
            if not str(number).strip().isdigit():
                continue
            body = self._body_weight(pd.Series([weight])).iloc[0]
            if np.isnan(body):
                continue
            change = pd.to_numeric(str(diff).strip(), errors="coerce")
            row = frame["umaban"] == int(number)
            frame.loc[row, "bw"] = body
            frame.loc[row, "bw_change"] = -change if str(sign).strip() == "-" else change

    def _overlay_track(self, frame: pd.DataFrame, rid: str) -> None:
        """その日の最後に発表された天候と馬場水分（発表の行は、変わった方だけに値が入る）。"""
        for weather, high, low in self._rows(_TRACK_SQL, [rid[:10]]):
            water = self._hex(pd.Series([f"{high}{low}"])).iloc[0]
            if water > 0:
                frame["water"] = water / 10.0
            if str(weather).strip() not in ("", "0"):
                frame["weather"] = pd.to_numeric(str(weather).strip(), errors="coerce")

    @classmethod
    def _decode(cls, raw: pd.DataFrame) -> pd.DataFrame:
        frame = raw.copy()
        frame["date"] = pd.to_datetime(frame["ymd"], format="%Y%m%d")
        frame["load"] = cls._hex(frame["load_hex"])
        frame["bw"] = cls._body_weight(frame["bw_hex"])
        diff = cls._number(frame["bw_diff"])
        frame["bw_change"] = np.where(frame["bw_sign"].str.strip() == "-", -diff, diff)
        water = cls._hex(frame["w_hi"] + frame["w_lo"]) / 10.0
        frame["water"] = water.where(water > 0)
        raw_time = cls._number(frame["time_raw"])
        frame["time"] = np.where(raw_time > 0, (raw_time // 1000) * 60 + (raw_time % 1000) / 10.0, np.nan)
        frame["finish"] = cls._number(frame["finish"])
        frame["win_odds"] = cls._number(frame["win_odds"]) / 10.0
        for column in ("pop", "race_no", "umaban", "waku", "age", "prize1", "abnormal", "weather"):
            frame[column] = cls._number(frame[column])
        frame["weather"] = frame["weather"].where(frame["weather"] > 0)
        frame["name"] = frame["name"].str.strip()
        frame = frame.drop(columns=["load_hex", "bw_hex", "bw_sign", "bw_diff", "w_hi", "w_lo", "time_raw"])
        return frame.sort_values(["date", "race_no", "umaban"]).reset_index(drop=True)

    @classmethod
    def _body_weight(cls, series: pd.Series) -> pd.Series:
        weight = cls._hex(series)
        return weight.where((weight >= _BODY_WEIGHT_RANGE[0]) & (weight <= _BODY_WEIGHT_RANGE[1]))

    @staticmethod
    def _hex(series: pd.Series) -> pd.Series:
        """16進の文字列を数に直す（空や読めない値は欠損）。"""
        def one(text: object) -> float:
            try:
                return float(int(str(text or "").strip(), 16))
            except ValueError:
                return np.nan
        return series.map(one).astype(float)

    @staticmethod
    def _number(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")
