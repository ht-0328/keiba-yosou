"""当日のレースを custom_binary のモデルで予想し、複勝の期待値で買う馬を選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from 共通 import card, db
from 共通.render import Table

from yosou.custom_binary import workflow
from yosou.custom_binary.feature.registry import FeatureRegistry
from yosou.custom_binary.settings import ModelSettings

from 当日の予想.stakes_predictor import StakesPredictor

#: 1レースで表に出す馬の数（期待値の高い順）。
TOP_HORSES = 5
#: 買いの一覧とレースごとの表の列。
BUY_COLUMNS = ["発走", "場", "R", "レース名", "馬番", "馬名", "人気", "複勝オッズ（最低）", "3着以内の確率", "期待値", "モデル"]
RACE_COLUMNS = ["馬番", "馬名", "人気", "単勝オッズ", "複勝オッズ（最低）", "3着以内の確率", "期待値", "買い"]


@dataclass(frozen=True)
class SameDayModel:
    """当日の予想に使う1つのモデル。``label`` は表に出す名前（馬体重あり・馬体重なし）。

    ``line`` は、このモデルで期待値がいくつ以上の馬に印を付けるか。``buys`` が偽のモデルは、
    学習に使っていない期間で回収率の下限が 100% に届く線が無かったもので、印を「買い」ではなく「参考」にし、買いの一覧に入れない。
    線の選び方と結果は ``line_check.py``（``reports/当日の予想/線の確かめ.md``）。
    """

    label: str
    config: Path
    line: float
    buys: bool

    def folder(self, registry: FeatureRegistry) -> Path:
        name = ModelSettings.load(self.config, registry).name
        return workflow.PROJECT_ROOT / "reports" / "特徴量と条件を選んで予想" / name


class SameDayPredictor:
    """発走前のレースを、並べた順のモデルで予想する。前のモデルで予想できない（馬体重が未発表など）ときは次のモデルを使う。

    モデルが保存されていなければ、はじめに学習する（1つ数分）。期待値がモデルの線（``SameDayModel.line``）以上の馬を
    「買い」（複勝）にする。買わないモデル（``buys`` が偽）では「参考」にして、買いの一覧に入れない。
    ``line`` を渡すと、どのモデルの線もその値に置き換える（線を変えて試すとき用。買うかどうかはモデルのまま）。
    ``stakes`` を渡すと、重賞のレースには、その予想（重賞の傾向と近走から3着以内を予想）の表もレースの表の下に並べる。
    重賞の予想は見せるだけで、買いの判断には使わない。
    """

    def __init__(self, models: list[SameDayModel], registry: FeatureRegistry, database: Path | None,
                 line: float | None = None, stakes: StakesPredictor | None = None) -> None:
        self._models = {model.label: model for model in models}
        self._registry = registry
        self._database = database
        self._line = line
        self._stakes = stakes

    def line_of(self, label: str) -> float:
        """モデル ``label`` の、印を付ける期待値の線。"""
        return self._models[label].line if self._line is None else self._line

    def buys_with(self, label: str) -> bool:
        """モデル ``label`` の予想で買うか（偽なら印は「参考」で、買わない）。"""
        return self._models[label].buys

    def ensure_models(self, log=print) -> None:
        for model in self._models.values():
            if not (model.folder(self._registry) / "model.json").is_file():
                log(f"「{model.label}」のモデルが無いので学習します（数分かかります）: {model.config.name}")
                workflow.train(model.config, self._database, self._registry)

    def run(self, day: str, after: str) -> list[Table]:
        """開催日 ``day``（YYYY-MM-DD）の、発走が ``after``（HH:MM）以降のレースを予想する。

        元DB は1回だけ開いて全レースで使い回す（開くたびに事実表を作り直すと、1レースに1分近くかかる）。
        """
        loaded = self.load_models()
        buys, tables = [], []
        with db.open_db(self._database) as con:
            races = self.races(con, day, after)
            for race in races:
                tables.append(self._race_table(con, race, loaded, buys))
                tables.extend(self._stakes_tables(con, race))
        buy_table = Table(BUY_COLUMNS, buys, title=f"買い（複勝・期待値 {self._lines_label()}）", note=self._note(len(races)))
        return [buy_table, *tables]

    def load_models(self) -> list[tuple[str, workflow.LoadedModel]]:
        """（表に出す名前, 読み込んだモデル）を、並べた順に。何レースも予想するときは1回だけ読む。"""
        return [(model.label, workflow.LoadedModel.load(model.folder(self._registry), self._registry))
                for model in self._models.values()]

    def races(self, con, day: str, after: str) -> list[dict]:
        """開催日 ``day`` の、発走が ``after`` 以降のレース（出馬表の一覧の行。``rid``・``発走``・``場``・``R`` …）。"""
        listed = card.list_cards(con, date_from=day, date_to=day)
        rows = [dict(zip(listed.columns, row)) for row in listed.rows]
        return sorted((row for row in rows if (row["発走"] or "") >= after), key=lambda row: (row["発走"], row["場"]))

    def _race_table(self, con, race: dict, loaded: list, buys: list) -> Table:
        title = f"{race['場']}{race['R']}R {race['発走']} {race['コース']}{race['距離']}m {race['レース名'] or ''}".strip()
        try:
            label, result = self.predict(con, race["rid"], loaded)
        except ValueError as error:
            return Table(["理由"], [[str(error)]], title=f"{title}（予想できない）")
        records = [dict(zip(result.columns, row)) for row in result.rows]
        records.sort(key=lambda record: -(record.get("期待値") or 0))
        line, model_buys = self.line_of(label), self.buys_with(label)
        rows = []
        for record in records[:TOP_HORSES]:
            value = record.get("期待値")
            reaches_line = value is not None and value >= line
            rows.append([record["馬番"], record["馬名"], record["使用した人気"], record.get("単勝オッズ"),
                         record.get("複勝オッズ（最低）"), _round(record.get("3着以内の確率")), _round(value, 2),
                         _mark(reaches_line, model_buys)])
            if reaches_line and model_buys:
                buys.append([race["発走"], race["場"], race["R"], race["レース名"] or "", record["馬番"], record["馬名"],
                             record["使用した人気"], record.get("複勝オッズ（最低）"), _round(record.get("3着以内の確率")),
                             _round(value, 2), label])
        kind = label if model_buys else f"{label}・参考: 買わない"
        return Table(RACE_COLUMNS, rows, title=f"{title}（{kind}）")

    def _stakes_tables(self, con, race: dict) -> list[Table]:
        """重賞のレースなら、重賞の予想の表。重賞でないか、``stakes`` を渡していなければ空。"""
        if self._stakes is None:
            return []
        return self._stakes.tables(con, race)

    def predict(self, con, race_id: str, loaded: list) -> tuple[str, Table]:
        """並べた順のモデルで1レースを予想する。どれでも予想できなければ ``ValueError``。"""
        message = ""
        for label, model in loaded:
            try:
                return label, workflow.predict_race(con, race_id, model, self._registry)
            except ValueError as error:
                message = str(error)
        raise ValueError(message)

    def _lines_label(self) -> str:
        """買いの一覧の見出しに出す、モデルごとの線（例「馬体重あり 1.2 以上」）。買わないモデルは「参考」と書く。"""
        return "・".join(f"{label} {self.line_of(label):g} 以上" if model.buys else f"{label} は参考"
                        for label, model in self._models.items())

    def _note(self, races: int) -> str:
        return (f"{races}レースを予想した。買いは複勝を1点100円（研究で確かめた買い方）。"
                "「参考」の印は、学習に使っていない期間で回収率の下限が 100% に届かなかったモデルの予想で、買わない。"
                "オッズは締め切りまで動くので、発走の10〜15分前に取り込み直して予想し直す。"
                "回収率は確定オッズでの検証の値で、買う時点のオッズでは下がりうる。")


def _mark(reaches_line: bool, model_buys: bool) -> str:
    """レースの表の「買い」の列。線に届いた馬に、買うモデルなら「買い」、買わないモデルなら「参考」。"""
    if not reaches_line:
        return ""
    return "買い" if model_buys else "参考"


def _round(value, digits: int = 3):
    return None if value is None else round(float(value), digits)
