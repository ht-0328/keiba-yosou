"""コマンド（tables・walk・train）。引数を読み、流れ（workflow）を呼び、結果を表にして出す。

| 名前 | 仕事 |
|---|---|
| ``CommandLine`` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す |
| ``TablesCommand`` | ``tables``: 過去のレースの組の表を作る。``--from``・``--to`` で期間、``--ticket`` で券種、``--force`` で作り直し |
| ``WalkCommand`` | ``walk``: 年ごとに学んで次の年を予測し、買い目の年ごとの成績を出す |
| ``TrainCommand`` | ``train``: 本番のモデルを学習して保存し、検証の期間での当たり具合を出す |

``--ticket`` の読み方は ``ticket_argument.py``、置き場所の引数は ``folder_arguments.py``、途中経過の出し方は ``progress.py``、
この予想の名前は ``yosou_name.py``。共通の引数（``--models --db --format --out``）は ``yosou.shared.command`` の ``CommonArguments``。
"""

from .command_line import CommandLine
from .yosou_name import YOSOU_NAME

__all__ = ["CommandLine", "YOSOU_NAME"]
