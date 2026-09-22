"""この予想だけが読むもの。SQL はこのフォルダだけに書き、1つの SQL につき 1つのリポジトリにする。

出走の行・過去走・調教・速報を読むリポジトリは、予想で変わらないので ``yosou.shared.repository``。

| クラス | 読むもの |
|---|---|
| ``AnnouncedOddsRepository`` | 締め切り前の単勝オッズ（時系列オッズのいちばん新しい断面） |
"""

from .announced_odds_repository import AnnouncedOddsRepository

__all__ = ["AnnouncedOddsRepository"]
