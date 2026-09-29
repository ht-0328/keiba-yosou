"""当日のレースを custom_binary のモデルで予想し、複勝の期待値で買う馬を選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from 共通 import card, db
from 共通.render import Table

from yosou.custom_binary.command import PredictionTable
from yosou.custom_binary.feature.registry import FeatureRegistry
from yosou.custom_binary.setting import ModelSettings
from yosou.custom_binary.store import MODELS_ROOT
from yosou.custom_binary.workflow import LoadedModel, PredictionWorkflow, TrainingWorkflow

#: 1レースで表に出す馬の数（期待値の高い順）。
TOP_HORSES = 5
#: 買いの一覧とレースごとの表の列。
BUY_COLUMNS = ["発走", "場", "R", "レース名", "馬番", "馬名", "人気", "複勝オッズ（最低）", "3着以内の確率", "期待値", "モデル"]
RACE_COLUMNS = ["馬番", "馬名", "人気", "単勝オッズ", "複勝オッズ（最低）", "3着以内の確率", "期待値", "買い"]


@dataclass(frozen=True)
class SameDayModel:
    """当日の予想に使う1つのモデル。``label`` は表に出す名前（馬体重あり・馬体重なし）。"""

    label: str
    config: Path

    def folder(self, registry: FeatureRegistry, models_root: Path = MODELS_ROOT) -> Path:
        """学習したモデルのフォルダ（``models_root`` の下の、設定の name のフォルダ）。"""
        name = ModelSettings.load(self.config, registry).name
        return models_root / name


class SameDayPredictor:
    """発走前のレースを、並べた順のモデルで予想する。前のモデルで予想できない（馬体重が未発表など）ときは次のモデルを使う。

    モデルが保存されていなければ、はじめに学習する（1つ数分）。期待値が ``line`` 以上の馬を「買い」（複勝）にする。
    モデルの置き場所は ``models_root``（省略すると ``reports/特徴量と条件を選んで予想/``）。
    """

    def __init__(self, models: list[SameDayModel], registry: FeatureRegistry, database: Path | None, line: float,
                 models_root: Path = MODELS_ROOT) -> None:
        self._models = models
        self._registry = registry
        self._database = database
        self._line = line
        self._models_root = models_root

    def ensure_models(self, log=print) -> None:
        for model in self._models:
            if not (model.folder(self._registry, self._models_root) / "model.json").is_file():
                log(f"「{model.label}」のモデルが無いので学習します（数分かかります）: {model.config.name}")
                TrainingWorkflow(self._registry, self._database, self._models_root).run(model.config)

    def run(self, day: str, after: str) -> list[Table]:
        """開催日 ``day``（YYYY-MM-DD）の、発走が ``after``（HH:MM）以降のレースを予想する。

        元DB は1回だけ開いて全レースで使い回す（開くたびに事実表を作り直すと、1レースに1分近くかかる）。
        """
        loaded = self.load_models()
        buys, tables = [], []
        with db.open_db(self._database) as con:
            for race in self.races(con, day, after):
                tables.append(self._race_table(con, race, loaded, buys))
        buy_table = Table(BUY_COLUMNS, buys, title=f"買い（複勝・期待値 {self._line:g} 以上）", note=self._note(len(tables)))
        return [buy_table, *tables]

    def load_models(self) -> list[tuple[str, LoadedModel]]:
        """（表に出す名前, 読み込んだモデル）を、並べた順に。何レースも予想するときは1回だけ読む。"""
        return [(model.label, LoadedModel.load(model.folder(self._registry, self._models_root), self._registry))
                for model in self._models]

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
        rows = []
        for record in records[:TOP_HORSES]:
            value = record.get("期待値")
            is_buy = value is not None and value >= self._line
            rows.append([record["馬番"], record["馬名"], record["使用した人気"], record.get("単勝オッズ"),
                         record.get("複勝オッズ（最低）"), _round(record.get("3着以内の確率")), _round(value, 2),
                         "買い" if is_buy else ""])
            if is_buy:
                buys.append([race["発走"], race["場"], race["R"], race["レース名"] or "", record["馬番"], record["馬名"],
                             record["使用した人気"], record.get("複勝オッズ（最低）"), _round(record.get("3着以内の確率")),
                             _round(value, 2), label])
        return Table(RACE_COLUMNS, rows, title=f"{title}（{label}）")

    def predict(self, con, race_id: str, loaded: list) -> tuple[str, Table]:
        """並べた順のモデルで1レースを予想する。どれでも予想できなければ ``ValueError``。"""
        message = ""
        workflow = PredictionWorkflow(con, self._registry)
        for label, model in loaded:
            try:
                return label, PredictionTable(model.settings).table(workflow.run(race_id, model))
            except ValueError as error:
                message = str(error)
        raise ValueError(message)

    def _note(self, races: int) -> str:
        return (f"{races}レースを予想した。買いは複勝を1点100円（研究で確かめた買い方）。"
                "オッズは締め切りまで動くので、発走の10〜15分前に取り込み直して予想し直す。"
                "回収率は確定オッズでの検証の値で、買う時点のオッズでは下がりうる。")


def _round(value, digits: int = 3):
    return None if value is None else round(float(value), digits)
