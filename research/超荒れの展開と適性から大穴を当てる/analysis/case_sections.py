"""段1・段2 の報告の節と表を、出走の表とレースの表から作る（元DB を読んだあとの部分。テストから呼べるよう分けてある）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .tables.concentration_table import ConcentrationTable
from .tables.forecast_hit_table import ForecastHitTable
from .tables.gap_table import GapTable
from .tables.pace_share_table import PaceShareTable
from .tables.pair_alignment_table import PairAlignmentTable
from .tables.pair_pattern_table import PairPatternTable
from .tables.pre_close_table import PreCloseTable
from .tables.rank_capture_table import RankCaptureTable
from .tables.upset_count_table import UpsetCountTable
from .tables.win_shape_table import WinShapeTable

#: 事例の数を分ける切り口。
COUNT_CUTS: tuple[str, ...] = ("ハンデ戦か", "重量種別", "頭数", "競馬場", "芝ダ", "距離", "クラス", "馬場状態", "年", "大穴のオッズから見た勝率の合計")
#: 斤量の見方（人気から見た差を重量種別で分けて出す）。
WEIGHT_CUTS: tuple[str, ...] = ("平均との差", "トップとの差", "斤量÷馬体重", "前走との差", "減量騎手")
#: 軽い斤量と重ねる見方。
OVERLAP_CUTS: tuple[str, ...] = ("推定脚質（前後）", "距離", "馬場")
#: コースの単位の表に出す行の数（全部は CSV）。
COURSE_ROWS = 40

Sections = list[tuple[str, list[Table]]]


@dataclass(frozen=True)
class CaseSections:
    """``runners``（``RunnerCuts`` の列を持つ出走の表）と ``races``（``RaceTable``）から、事例の報告の節を作る。"""

    runners: pd.DataFrame
    races: pd.DataFrame

    def build(self) -> Sections:
        return [*self.counts(), *self.development(), *self.bias(), *self.pairs(), *self.weights(), *self.aptitude(),
                *self.periods(), *self.which_longshot()]

    def counts(self) -> Sections:
        table = UpsetCountTable()
        cuts = [table.build(self.races, cut, f"{cut}ごと") for cut in COUNT_CUTS]
        course = table.build(self.races, "コースの単位（競馬場・コース・距離・馬場状態）",
                             f"コースの単位ごと（大穴1着の多い順に {COURSE_ROWS} 行。全部は コースの単位ごとの数.csv）", by_count=True, limit=COURSE_ROWS)
        handicap = self.races.loc[self.races["handicap"] == "ハンデ戦"]
        spread = table.build(handicap, "斤量の幅（いちばん重い − いちばん軽い）", "ハンデ戦の斤量の幅ごと（ハンデ戦だけ）")
        pre_close = PreCloseTable().build(self.races, "確定の人気と締め切り前の人気（2025年から）")
        return [("1. 事例の数", [*cuts, course, spread, pre_close])]

    def development(self) -> Sections:
        longshots = self.longshots()
        gap, hit = GapTable(), ForecastHitTable()
        handicap = self.races.loc[self.races["handicap"] == "ハンデ戦"]
        tables = [
            PaceShareTable().build(self.races, "決着ごとの結果のペース（全レース）"),
            PaceShareTable().build(handicap, "決着ごとの結果のペース（ハンデ戦）"),
            UpsetCountTable().build(self.races, "結果のペース", "結果のペースごとの事例の数"),
            UpsetCountTable().build(self.races, "予想のペース", "予想のペース（前日の時点）ごとの事例の数"),
            WinShapeTable().build(longshots.loc[longshots["won"] > 0], "大穴の勝ち馬の勝ち方の形 × 結果のペース"),
            WinShapeTable().build(self.runners.loc[(self.runners["won"] > 0) & (self.runners["popularity"] <= 3)],
                                  "比べる基準: 1〜3番人気の勝ち馬の勝ち方の形 × 結果のペース"),
            hit.summary(self.races, "展開の予想の当たり方（決着ごと）"),
            hit.matrix(self.races, "予想のペース × 結果のペース（決着ごと）"),
            gap.build(longshots, ["結果のペース", "結果の脚質"], "大穴: 結果のペース × 結果の脚質（結果側。理解のため）"),
            gap.build(longshots, ["結果のペース", "いつもとの位置の差"], "大穴: 結果のペース × いつもとの位置の差（結果側）"),
            gap.build(longshots, ["結果のペース", "推定脚質"], "大穴: 結果のペース × 推定脚質（ペースが分かっていたら選べたか）"),
            gap.build(longshots, ["予想のペース", "推定脚質"], "大穴: 予想のペース × 推定脚質（レース前に分かる）"),
            gap.build(longshots, ["予想のペース", "位置の見込み"], "大穴: 予想のペース × 位置の見込み（レース前に分かる）"),
            gap.build(self.runners, ["予想のペース", "推定脚質"], "全体: 予想のペース × 推定脚質（レース前に分かる）"),
        ]
        return [("2. 展開", tables)]

    def bias(self) -> Sections:
        gap = GapTable()
        tables = [gap.build(self.longshots(), ["その日の内外の傾き", "枠の側"], "大穴: その日の内外の傾き × 枠の側"),
                  gap.build(self.longshots(), ["その日の内外の傾き", "結果の脚質"], "大穴: その日の内外の傾き × 結果の脚質（結果側）")]
        return [("3. 馬場（その日のバイアス）", tables)]

    def pairs(self) -> Sections:
        multi = self.races.index[self.races["longshot_multi"]]
        tables = [PairAlignmentTable().build(self.runners, multi, "来た大穴どうしが同じ形だったか"),
                  PairPatternTable().build(self.runners, self.races, "来た大穴の前後の脚質（結果）の組み合わせ × 結果のペース"),
                  PairPatternTable("corner4_group").build(self.runners, self.races, "来た大穴の4コーナーの位置の組み合わせ × 結果のペース")]
        return [("4. 大穴が2頭以上のレース", tables)]

    def weights(self) -> Sections:
        gap = GapTable()
        longshots = self.longshots()
        handicap = self.runners.loc[self.runners["handicap"] == "ハンデ戦"]
        tables = []
        for cut in WEIGHT_CUTS:
            tables.append(gap.build(self.runners, ["重量種別", cut], f"全体: 重量種別 × {cut}"))
            tables.append(gap.build(longshots, ["重量種別", cut], f"大穴: 重量種別 × {cut}"))
        for cut in OVERLAP_CUTS:
            tables.append(gap.build(self.runners, ["ハンデ戦か", "斤量の軽さ", cut], f"全体: 斤量の軽さ × {cut}"))
            tables.append(gap.build(longshots, ["ハンデ戦か", "斤量の軽さ", cut], f"大穴: 斤量の軽さ × {cut}"))
        tables += [
            gap.build(handicap, ["トップハンデか", "人気"], "ハンデ戦: トップハンデか × 人気"),
            gap.build(handicap, ["クラスの替わり", "前走との差（3つ）"], "ハンデ戦（全体）: クラスの替わり × 前走との斤量の差"),
            gap.build(handicap.loc[handicap["longshot"]], ["クラスの替わり", "前走との差（3つ）"], "ハンデ戦（大穴）: クラスの替わり × 前走との斤量の差"),
            gap.build(handicap.loc[handicap["longshot"]], ["結果のペース", "前走との差（3つ）", "推定脚質（前後）"],
                      "ハンデ戦（大穴）: 結果のペース × 前走との斤量の差 × 推定脚質（事例で目立った形を数で確かめる）"),
            gap.build(longshots, ["重量種別", "同じ斤量の実績"], "大穴: 重量種別 × 同じ斤量の実績"),
            gap.build(longshots, ["重量種別", "重い斤量の実績"], "大穴: 重量種別 × 今回より重い斤量での実績"),
        ]
        return [("5. ハンデ・斤量", tables)]

    def aptitude(self) -> Sections:
        gap = GapTable()
        return [("6. 適性", [gap.build(self.longshots(), ["ハンデ戦か", "コースの実績"], "大穴: コースの実績")])]

    def periods(self) -> Sections:
        gap = GapTable()
        longshots = self.longshots()
        handicap = self.runners.loc[self.runners["handicap"] == "ハンデ戦"]
        tables = [
            gap.build(longshots, ["期間", "予想のペース", "推定脚質"], "大穴: 予想のペース × 推定脚質（前半・後半の年）"),
            gap.build(longshots, ["期間", "位置の見込み"], "大穴: 位置の見込み（前半・後半の年）"),
            gap.build(handicap, ["期間", "クラスの替わり", "前走との差（3つ）"], "ハンデ戦（全体）: クラスの替わり × 前走との斤量の差（前半・後半の年）"),
            gap.build(handicap, ["期間", "トップハンデか", "人気"], "ハンデ戦: トップハンデか × 人気（前半・後半の年）"),
        ]
        return [("7. 前半と後半の年で同じか", tables)]

    def which_longshot(self) -> Sections:
        longshots = self.longshots()
        won_races = self.races.index[self.races["longshot_won"]]
        multi_races = self.races.index[self.races["longshot_multi"]]
        in_won = longshots.loc[longshots["race_id"].isin(won_races)]
        in_multi = longshots.loc[longshots["race_id"].isin(multi_races)]
        won, top3 = ConcentrationTable("won"), ConcentrationTable("top3")
        tables = [
            RankCaptureTable().build(in_won, "大穴が勝ったレースで、勝ち馬を大穴の中の上位何頭に置けたか"),
            won.build(in_won, ["予想のペース", "位置の見込み"], "大穴1着のレース: 予想のペース × 位置の見込み"),
            won.build(in_won, ["予想のペース", "推定脚質"], "大穴1着のレース: 予想のペース × 推定脚質"),
            won.build(in_won, ["ハンデ戦か", "平均との差"], "大穴1着のレース: 斤量（平均との差）"),
            won.build(in_won, ["ハンデ戦か", "前走との差（3つ）"], "大穴1着のレース: 前走との斤量の差"),
            won.build(in_won, ["ハンデ戦か", "重い斤量の実績"], "大穴1着のレース: 今回より重い斤量での実績"),
            won.build(in_won, ["コースの実績"], "大穴1着のレース: コースの実績"),
            won.build(in_won, ["その日の内外の傾き", "枠の側"], "大穴1着のレース: その日の内外の傾き × 枠の側"),
            top3.build(in_multi, ["予想のペース", "位置の見込み"], "大穴2頭以上のレース: 予想のペース × 位置の見込み"),
            top3.build(in_multi, ["予想のペース", "推定脚質"], "大穴2頭以上のレース: 予想のペース × 推定脚質"),
            top3.build(in_multi, ["ハンデ戦か", "斤量の軽さ"], "大穴2頭以上のレース: 斤量の軽さ"),
        ]
        return [("8. 大穴が来たレースの中で、どの大穴が来たか", tables)]

    def longshots(self) -> pd.DataFrame:
        return self.runners.loc[self.runners["longshot"]]
