"""印の成績の結果を作り方ごとに並べる表。架空の値の Markdown だけを使う。"""

from __future__ import annotations

from pathlib import Path

from 危険な人気馬を見極める.analysis.mark_comparison import MarkComparison


def _report(path: Path, win_return: str, danger: bool) -> Path:
    danger_rows = ("| 消のうち 1番人気 | 0.2 | 100 | 1-1-1-97 | 1.0% | 2.0% | 50.0% | 50.0% | 70.0% | 70.0% |\n"
                   "| 消のうち 2〜5番人気 | 0.2 | 80 | 1-1-1-77 | 1.0% | 2.0% | 30.0% | 70.0% | 70.0% | 70.0% |\n") if danger else ""
    path.write_text(
        "### 1. 印ごとの成績\n\n" + danger_rows + "\n"
        "### 7. 買い方ごとの買い目の成績（印のルール）\n\n"
        "| 買い方 | 対象 | 買ったレース | 点数 | 1レースの点数 | 投資 | 払戻 | 回収率 | 回収率の90%の幅 | 的中レース | 的中率 | a | b |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        f"| 単勝 | 全レース | 10 | 10 | 1.0 | 1,000円 | 900円 | {win_return} | 1 | 2 | 20.0% | 0 | 0 |\n"
        "| 単勝 | ◎の期待値 1.00 以上 | 5 | 5 | 1.0 | 500円 | 600円 | 120.0% | 1 | 1 | 20.0% | 0 | 0 |\n"
        "\n### 8. 年ごと\n", encoding="utf-8")
    return path


def test_lines_up_the_whole_race_rows_and_the_danger_rows(tmp_path: Path):
    reports = {"今の本番": _report(tmp_path / "a.md", "90.0%", True), "消なし": _report(tmp_path / "b.md", "95.0%", False)}
    bets, dangers = MarkComparison().tables(reports)
    # 全レースの行だけを、作り方の順に 回収率・的中率 で並べる
    assert bets.rows == [["単勝", "90.0%", "20.0%", "95.0%", "20.0%"]]
    assert dangers.rows == [["今の本番", "100頭・50.0%", "80頭・30.0%"], ["消なし", "", ""]]
