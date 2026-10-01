"""学習したモデルの置き場所。"""

from pathlib import Path

#: keiba-yosou のリポジトリ直下（src/yosou/custom_binary/store/ から4つ上）。
PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: この予想の名前（設計書 ``docs/design/`` のフォルダ名と同じ）。
YOSOU_NAME = "特徴量と条件を選んで予想"
#: 学習したモデルを、設定の name ごとのフォルダに置く場所。JV-Data から作ったもので公開しないので、Git の対象外（reports/）。
MODELS_ROOT = PROJECT_ROOT / "reports" / YOSOU_NAME
