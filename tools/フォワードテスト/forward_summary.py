"""フォワードテストの記録から、これまでの成績をまとめた文書を作る。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from フォワードテスト.ledger import Ledger

#: 判定までに貯める開催日の数の目安（約1か月 = 土日で8開催日）。
TARGET_DAYS = 8


class ForwardSummary:
    """精算済みの買い目の回収率を、全体と開催日ごとに出す。未精算の買い目は数だけ出す。"""

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def write(self, now: datetime) -> Path:
        buys, races = self._ledger.buys(), self._ledger.races()
        settled = buys[buys["精算"] != ""].assign(賭け金=lambda f: pd.to_numeric(f["賭け金"]),
                                                  払戻=lambda f: pd.to_numeric(f["払戻"]))
        days = sorted(set(races["開催日"]))
        lines = [
            "# フォワードテストの成績", "",
            f"更新: {now:%Y-%m-%d %H:%M}。当日の予想（tools/当日の予想/）と同じモデル・同じ線で、発走の約10分前のオッズで",
            "予想して「買ったつもり」で記録した結果。実際のお金は使っていない。JV-Data 由来の値を含むため、Git の対象外。", "",
            f"- 開催日: {len(days)} 日（目安の {TARGET_DAYS} 日まで あと {max(TARGET_DAYS - len(days), 0)} 日）"
            + (f"　{days[0]} 〜 {days[-1]}" if days else ""),
            f"- 予想したレース: {len(races):,}　うち予想できなかったレース: {int((races['予想できない理由'] != '').sum()):,}",
            f"- 買い目: {len(buys):,} 点　精算済み: {len(settled):,} 点　未精算: {len(buys) - len(settled):,} 点",
            *self._total(settled), "",
            "## 開催日ごと", "",
            self._by_day(settled), "",
            "## 読み方", "",
            "- 回収率 = 払戻の合計 ÷ 賭け金の合計。返還（出走取消など）は賭け金がそのまま戻る。",
            f"- 約1か月（{TARGET_DAYS} 開催日ほど）たまったところで、回収率が 100% を超えているかを見る。"
            "点数が少ないうちは、たまたまの当たり外れで大きく動く。",
            "- オッズの発表時刻は 買い目.csv にある。発走の10分より前の断面で予想していることを確かめられる。", "",
        ]
        path = self._ledger.folder / "成績.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    @staticmethod
    def _total(settled: pd.DataFrame) -> list[str]:
        if settled.empty:
            return ["- まだ精算済みの買い目がない"]
        stake, paid = settled["賭け金"].sum(), settled["払戻"].sum()
        hits = int((settled["払戻"] > 0).sum())
        return [f"- 的中: {hits:,} 点（的中率 {hits / len(settled):.3f}）",
                f"- 賭け金 {stake:,.0f} 円・払戻 {paid:,.0f} 円・損益 {paid - stake:+,.0f} 円・**回収率 {paid / stake * 100:.1f}%**"]

    @staticmethod
    def _by_day(settled: pd.DataFrame) -> str:
        if settled.empty:
            return "（まだ無い）"
        grouped = settled.groupby("開催日")
        table = pd.DataFrame({"買い目": grouped.size(), "的中": grouped["払戻"].apply(lambda paid: int((paid > 0).sum())),
                              "賭け金": grouped["賭け金"].sum(), "払戻": grouped["払戻"].sum()})
        table["回収率"] = (table["払戻"] / table["賭け金"] * 100).round(1)
        return table.reset_index().to_markdown(index=False)
