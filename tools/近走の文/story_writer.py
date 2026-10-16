"""近走の文を Markdown にする。"""

from __future__ import annotations

from collections.abc import Sequence

from .horse_story import HorseStory


class StoryWriter:
    """``HorseStory`` を Markdown の行にする。馬ごとに見出し、走ごとに1つの箇条書き、負けた走には敗因の候補を1段下げて添え、
    最後に評価のことば（あれば）。``body`` は見出し無しの箇条書きだけ（今週の予想・全頭評価が自分の文書に差し込むのに使う）。"""

    def lines(self, story: HorseStory, heading: str = "###") -> list[str]:
        shown = len(story.lines)
        extra = f"（中央 {story.career_runs} 走のうち近 {shown} 走）" if story.career_runs > shown else f"（中央 {story.career_runs} 走）"
        return [f"{heading} {story.name}{extra}", "", *self.body(story), ""]

    def body(self, story: HorseStory) -> list[str]:
        if not story.lines:
            return ["- 中央での過去走が無い"]
        lines = []
        for line in story.lines:
            lines.append(f"- {line.sentence}")
            if line.reasons:
                lines.append(f"  - 敗因の候補: {'・'.join(line.reasons)}")
        if story.words:
            lines.append(f"- 評価: {'・'.join(story.words)}")
        return lines

    def markdown(self, stories: Sequence[HorseStory], title: str) -> str:
        lines = [f"## {title}", ""]
        for story in stories:
            lines += self.lines(story)
        return "\n".join(lines)
