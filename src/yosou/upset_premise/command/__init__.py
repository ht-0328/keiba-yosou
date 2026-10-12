"""コマンド（train・predict）。

| クラス | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |

``train``・``predict`` は、手本の予想のコマンド（``yosou.form_aptitude_top3`` の ``TrainCommand``・``PredictCommand``）に、
この予想の名前（モデルの置き場所）と、学ぶ行の選び方（``WildRaceRows``）を渡して使う（同じ材料の作り方を2か所に書かないため）。
"""

from .command_line import CommandLine

__all__ = ["CommandLine"]
