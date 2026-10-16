"""全頭評価の文書を Markdown にする。"""

from __future__ import annotations

from .review_document import FieldReviewDocument, HorseReview


class ReviewWriter:
    """``FieldReviewDocument`` を Markdown の文章にする。

    冒頭にレースの条件と有力馬の候補、評価順の表（馬名・性齢・調教師・負担重量・3着以内と1着の確率）、
    そのあとに馬ごとの基本情報・強み・弱み。印・期待度・買い目は無い。
    """

    def markdown(self, document: FieldReviewDocument) -> str:
        distance = f"{document.distance_m}m" if document.distance_m else ""
        grade = f" {document.grade}" if document.grade else ""
        lines = [
            f"# {document.race_name}（{document.race_date.isoformat()} {document.venue} {document.surface}{distance}{grade}）登録 {document.entries} 頭の全頭評価",
            "",
            "特別登録の時点（出走馬・騎手・枠・馬場・オッズはまだ無い）の評価。確率は「出走すれば」のもので、出走するかどうかは当てていない。",
            "",
            f"**有力馬の候補**: {'・'.join(document.candidates) if document.candidates else 'なし'}（1着の確率の上位）",
            "",
            "| 評価順 | 馬名 | 性齢 | 調教師 | 負担重量 | 交流 | 3着以内の確率 | 1着の確率 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            *(self._row(horse) for horse in document.horses),
            "",
        ]
        for horse in document.horses:
            lines += self._horse(horse)
        if document.notes:
            lines += ["---", "", *(f"- {note}" for note in document.notes), ""]
        return "\n".join(lines)

    def _row(self, horse: HorseReview) -> str:
        carried = f"{horse.carried:.0f}" if horse.carried is not None else "—"
        return (f"| {horse.rank} | {horse.name} | {horse.sex_age} | {horse.trainer} | {carried} | {horse.exchange or ''} "
                f"| {horse.top3:.1%} | {horse.win:.1%} |")

    def _horse(self, horse: HorseReview) -> list[str]:
        lines = [f"## {horse.rank}. {horse.name}", "", horse.profile, "",
                 f"出走すれば 3着以内に入る確率 {horse.top3:.1%}、1着になる確率 {horse.win:.1%}。", ""]
        lines += ["**強み**", ""] + ([f"- {text}" for text in horse.strong] or ["- （目立つ強みは無い）"]) + [""]
        lines += ["**弱み**", ""] + ([f"- {text}" for text in horse.weak] or ["- （目立つ弱みは無い）"]) + [""]
        lines += ["**近走**（古い順。4着以下の走には敗因の候補、最後に評価のことば）", ""] + (horse.story or ["- 中央での過去走が無い"]) + [""]
        return lines
