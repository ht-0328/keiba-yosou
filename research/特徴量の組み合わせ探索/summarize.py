"""入口②・③の結果を1つの Markdown にまとめる（研究「特徴量の組み合わせ探索」の入口④）。

    uv run python research/特徴量の組み合わせ探索/summarize.py

出力は ``reports/特徴量の組み合わせ探索/結果.md``（Git 対象外。JV-Data 由来の数値を含むため）。
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "特徴量の組み合わせ探索"
RULE_COLUMNS = [
    "区分", "人気帯", "馬の条件", "見つける_点数", "見つける_回収率", "確かめる_点数", "確かめる_回収率",
    "テスト_点数", "テスト_回収率", "テスト_z",
]


def main() -> None:
    lines = ["# 特徴量の組み合わせ探索の結果", ""]
    lines += rule_section()
    lines += model_section(REPORTS / "models", "モデルで探した結果（馬柱の特徴量）")
    lines += model_section(REPORTS / "pool", "モデルで探した結果（券種オッズの特徴量を足した探索）")
    (REPORTS / "結果.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORTS / "結果.md")


def rule_section() -> list[str]:
    summary = json.loads((REPORTS / "rules" / "summary.json").read_text(encoding="utf-8"))
    lines = ["## ルールで探した結果", "", markdown(pd.DataFrame(summary).set_index("券種").T.reset_index()), ""]
    for bet in ("単勝", "複勝"):
        wide = pd.read_pickle(REPORTS / "rules" / f"{bet}_全ルール.pkl")
        baseline = wide[(wide["区分の段"] == "全レース") & (wide["特徴量"] == "（馬の条件なし）")]
        adopted = pd.read_csv(REPORTS / "rules" / f"{bet}_採用.csv")
        tested = adopted[adopted["テスト_点数"] >= 100]
        by_band = tested.groupby("人気帯").apply(lambda rules: pd.Series({
            "採用の数": len(rules), "テストで100%以上": int((rules["テスト_回収率"] >= 1).sum()),
            "採用のテスト回収率": (rules["テスト_回収率"] * rules["テスト_点数"]).sum() / rules["テスト_点数"].sum(),
        }), include_groups=False).reset_index()
        by_band = by_band.merge(baseline[["人気帯", "テスト_回収率"]].rename(columns={"テスト_回収率": "絞らずに買ったテスト回収率"}))
        lines += [f"### {bet}: 採用したルールのテスト期間の回収率（人気帯ごと）", "", markdown(by_band), ""]
        lines += [f"### {bet}: 採用したルールのうち、テスト期間でも回収率が高かったもの（上位20）", "",
                  markdown(tested.sort_values("テスト_回収率", ascending=False).head(20)[RULE_COLUMNS]), ""]
    return lines


def model_section(folder: Path, title: str) -> list[str]:
    rows = []
    for path in sorted(folder.glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        chosen, tested, bet = result["選んだ買い方"], result["テストでの結果"], result["券種"]
        everyone = next(row for row in result["テスト期間"]["paybacks"] if row["買い方"].startswith("対象の全頭"))
        auc = next(row for row in result["テスト期間"]["scores"] if row["モデル"] == "平均" and row["人気"] == "全体")["AUC"]
        rows.append({
            "設定": path.stem, "券種": bet, "テストのAUC": auc, "選んだ買い方": chosen["買い方"] if chosen else "なし",
            "確かめる_点数": chosen["点数"] if chosen else None, "確かめる_回収率": chosen[f"{bet}回収率"] if chosen else None,
            "テスト_点数": tested["点数"] if tested else None, "テスト_回収率": tested[f"{bet}回収率"] if tested else None,
            "全頭買いのテスト回収率": everyone[f"{bet}回収率"],
            "テスト_下限": tested.get(f"{bet}回収率の下限") if tested else None,
            "採用": adopted(tested, bet),
        })
    if not rows:
        return [f"## {title}", "", "まだ結果がありません。", ""]
    return [f"## {title}", "", ADOPTION_NOTE, "", markdown(pd.DataFrame(rows)), ""]


#: 採用の基準（計画で、テスト期間を見る前に決めた）。
ADOPTION_NOTE = "採用: テスト期間で回収率100%以上・点数300以上・開催日単位の90%の幅の下限が100%以上。参考: 回収率100%以上だが、ほかを満たさない。"


def adopted(tested: dict | None, bet: str) -> str:
    if not tested or tested.get(f"{bet}回収率") is None or tested[f"{bet}回収率"] < 1:
        return "不採用"
    lower = tested.get(f"{bet}回収率の下限")
    if tested["点数"] >= 300 and lower is not None and lower >= 1:
        return "採用"
    return "参考"


def markdown(frame: pd.DataFrame) -> str:
    """表を Markdown にする（tabulate を入れずに済ませる）。"""
    def cell(value) -> str:
        if isinstance(value, float):
            if pd.isna(value):
                return ""
            return f"{value:.0f}" if value.is_integer() and abs(value) >= 2 else f"{value:.3f}"
        return str(value)

    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = ["| " + " | ".join(cell(value) for value in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


if __name__ == "__main__":
    sys.exit(main())
