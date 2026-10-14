"""展開スコア: 脚質 × ペースの有利・不利を、市場の見立てとの差で数える（設計書「買うレースと買い目を決める」05）。

予想「展開から着順を予想」の前半の予想（① 先頭の馬・② 序盤の位置・③ 前半のペース）から、各馬が逃げ・先行・差し・追込の
位置を取る確率とレースのペースの確率を出し、過去のレースから数えた表 G（脚質 × ペース × 競馬場と芝ダ ごとの
「実際の3着以内率 − 市場から見た3着以内率」）と掛け合わせて、馬ごとの展開スコア D を出す。D は3着以内の確率のポイントで、
+0.02 なら市場の見立てより 2ポイント来やすい。線（±0.01）で展開有利・展開不利を判定する。

| 名前 | 仕事 |
|---|---|
| ``DevelopmentRunRepository`` | 表 G の元になる、中央・平地の全出走（最初のコーナーの順位・前3ハロン・単勝オッズ・着順）を読む |
| ``RaceCourseRepository`` | これから走る1レースの競馬場コードと芝ダを読む |
| ``EntryNameRepository`` | 1レースの出走馬の馬番と馬名を読む（結果を人が見るため） |
| ``PreRaceStyle`` | 出走ごとに、レース前に分かる脚質（近5走の先頭率と序盤の位置の平均）を付ける |
| ``ResultPace`` | レースごとに、結果のペース（前半タイムを基準と比べた z の区分）を付ける |
| ``AdvantageRuns`` | 上の2つと、オッズから見た3着以内率・実際の3着以内を出走の表にそろえる（表 G の材料） |
| ``AdvantageTableBuilder`` | 材料から表 G を作る（件数の少ないマスは、同じ脚質 × ペースの全競馬場の値に寄せる） |
| ``AdvantageTable`` | 表 G の入れ物。競馬場と芝ダごとの 4 × 3 の表を引く |
| ``AdvantageTableRepository`` | 表 G の pickle のファイルと元DB の印（``stamp.json``）を書く・読む（``repository/``） |
| ``AdvantageTableStore`` | 表 G を ``reports/展開スコア/cache/`` にとっておき、元DB が変わったら作り直す |
| ``StyleProbabilities`` | ①②③ の予測から、脚質の確率（4つ）とペースの確率（3つ）を出す |
| ``DevelopmentScore`` | 確率と表 G から、馬ごとの展開スコア D と脚質ごとの内訳を出す |
| ``AdvantageJudge`` | D を線で展開有利・展開不利・どちらでもないに分ける |
| ``RaceScoreSource`` | これから走る1レースを、保存した展開のモデルで予測して展開スコアの表にする（道具と、全頭の予想の予測の流れが使う） |
| ``RaceScoreWorkflow``・``RaceScore`` | 1レースの展開スコアの表に判定と馬番・馬名を付けて、人が見る形（``RaceScore``）にする（道具用） |
| ``RaceScoreAttacher`` | 1レースの展開スコアの表を予測用データに足す関数の形（全頭の予想の予測の流れに渡す。同じレースでは表を使い回す） |
| ``YearlyScorer`` | 過去の出走に、レースの年ごとに「その年より前のレースだけで作った表 G」で展開スコアを付ける（リークを防ぐ） |
| ``ScoreHistory`` | 年ごとの確かめの予測を読んで ``YearlyScorer`` に渡す（線の確かめ・研究用） |
| ``ScoreAttachment`` | 学習データ・予測用データに S の 5列を足す（P の ``PaceAttachment`` と同じ形） |
| ``DevelopmentScoreFreeData`` | 学習データ・予測用データから S を外す（1着のモデルは S を使わない） |
| ``DEVELOPMENT_SCORE_FEATURES`` | 展開スコアを予想の特徴量にするときの一覧（まとまり S。5個） |
"""

from .advantage_judge import DEFAULT_LINE, AdvantageJudge
from .advantage_runs import AdvantageRuns
from .advantage_table import AdvantageTable
from .advantage_table_builder import PRIOR_WEIGHT, AdvantageTableBuilder
from .advantage_table_store import DEFAULT_CACHE_FOLDER, AdvantageTableStore, cache_folder_beside
from .development_score import DevelopmentScore
from .features import DEVELOPMENT_SCORE_FEATURES, DEVELOPMENT_SCORE_NAMES
from .pre_race_style import PreRaceStyle
from .race_score import RaceScore
from .race_score_attacher import RaceScoreAttacher
from .race_score_source import RaceScoreSource
from .race_score_workflow import RaceScoreWorkflow
from .repository import AdvantageTableRepository, DevelopmentRunRepository, EntryNameRepository, RaceCourseRepository
from .result_pace import ResultPace
from .score_attachment import ScoreAttachment
from .score_free_data import DevelopmentScoreFreeData
from .score_history import ScoreHistory
from .style_probabilities import StyleProbabilities
from .yearly_scorer import YearlyScorer

__all__ = [
    "DevelopmentRunRepository", "RaceCourseRepository", "EntryNameRepository", "PreRaceStyle", "ResultPace", "AdvantageRuns",
    "AdvantageTableBuilder", "AdvantageTable", "AdvantageTableRepository", "AdvantageTableStore", "StyleProbabilities", "DevelopmentScore", "AdvantageJudge",
    "RaceScoreSource", "RaceScoreAttacher", "RaceScoreWorkflow", "RaceScore", "YearlyScorer", "ScoreHistory", "ScoreAttachment", "DevelopmentScoreFreeData", "DEVELOPMENT_SCORE_FEATURES", "DEVELOPMENT_SCORE_NAMES",
    "DEFAULT_LINE", "PRIOR_WEIGHT", "DEFAULT_CACHE_FOLDER", "cache_folder_beside",
]
