"""1レースの予想の結果を、全頭の予想根拠の Markdown にする。"""

from __future__ import annotations

from typing import Any

from 今週の予想.race_grades import RaceGrades

#: 複勝の券種の名前（買い目の行から複勝だけを拾う）。
_PLACE = "複勝"


class ReasonDocument:
    """``RaceForecaster.forecast`` の辞書を、人が読む全頭の予想根拠の Markdown にする。

    頭にレースの時点・的中率と配当率（等級つき）・印の並び・複勝の買い目。そのあと全頭を3着以内の確率の高い順に、馬ごとに
    確率と期待値、総合の文（確率・市場との差・押し上げた／割り引いた分類・印とその理由）、良い点・悪い点（分類ごとの確率の動きと根拠の特徴量）、
    近走の文（近5走・敗因の候補・評価のことば）を並べる。前の版の結果（``story`` が無い）は近走を省く。
    """

    def markdown(self, forecast: dict[str, Any]) -> str:
        lines = [f"# {forecast['title']} の全頭の予想根拠", "", *self._head(forecast), ""]
        for horse in forecast["horses"]:
            lines += self._horse(horse)
        return "\n".join(lines)

    def _head(self, forecast: dict[str, Any]) -> list[str]:
        marks = " ".join(f"{horse['mark']}{horse['horse_no']}" for horse in forecast["horses"] if horse["mark"] != "－")
        place = [ticket["label"] + (f"（{ticket['dropped']}で外す）" if ticket.get("dropped") else "")
                 for ticket in forecast.get("tickets", []) if ticket["ticket_type"] == _PLACE]
        return [
            f"- 時点: {forecast['timing']}（{forecast['timing_reason']}）",
            f"- 予想: {forecast['model']}",
            *RaceGrades.from_dict(forecast).lines(),
            f"- 印: {marks or 'なし'}",
            f"- 複勝の買い目: {'・'.join(place) if place else 'なし'}",
            f"- 作成: {forecast['made_at']}",
        ]

    def _horse(self, horse: dict[str, Any]) -> list[str]:
        popularity = f"{horse['popularity']:.0f}番人気" if horse.get("popularity") is not None else "人気なし"
        odds = f" {horse['win_odds']}倍" if horse.get("win_odds") is not None else ""
        lines = [f"## {horse['rank']}. {horse['mark']} {horse['horse_no'] or ''} {horse['horse_name']}（{popularity}{odds}）", ""]
        lines.append(f"- 確率: {self._numbers(horse)}")
        lines.append(f"- 総合: {horse['summary']}")
        lines.append(f"- 良い点: {self._points(horse['good'])}")
        lines.append(f"- 悪い点: {self._points(horse['bad'])}")
        story = horse.get("story")
        if story is not None:
            lines.append("- 近走（古い順）:")
            lines += [f"  {line}" for line in story["lines"]]
        return lines + [""]

    def _numbers(self, horse: dict[str, Any]) -> str:
        parts = [f"3着以内 {horse['probability']:.1%}"]
        if horse.get("market_top3") is not None:
            parts.append(f"市場の見立て {horse['market_top3']:.1%}")
        if horse.get("win_probability") is not None:
            parts.append(f"1着 {horse['win_probability']:.1%}")
        if horse.get("win_value") is not None:
            parts.append(f"単勝の期待値 {horse['win_value']:.2f}")
        if horse.get("place_value") is not None:
            parts.append(f"複勝の期待値 {horse['place_value']:.2f}")
        return "・".join(parts)

    def _points(self, points: list[dict[str, Any]]) -> str:
        if not points:
            return "目立つものはない"
        texts = []
        for point in points:
            details = "／".join(f"{detail['name']} {detail['value']}" for detail in point["details"])
            texts.append(f"「{point['category']}」{point['effect']:+.1f}ポイント（{details}）")
        return "、".join(texts)
