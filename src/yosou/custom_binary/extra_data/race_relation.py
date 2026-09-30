"""予想する1レースだけを対象にする関係（SQL）。"""


class RaceRelation:
    """``ExtraDataLoader.attach()`` に渡す、``race_id`` の列を1行だけ持つ関係。レースIDは数字だけを受け付ける。"""

    def of(self, race_id: str) -> str:
        if not race_id.isdigit():
            raise ValueError(f"レースIDは数字だけで指定してください: {race_id}")
        return f"(SELECT '{race_id}' AS race_id)"
