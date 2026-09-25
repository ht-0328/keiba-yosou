"""条件だけで買うルールを探す（研究「特徴量の組み合わせ探索」の入口②）。

    uv run python research/特徴量の組み合わせ探索/rule_scan.py

レースの区分 × 馬の条件（1つの特徴量の値の範囲）× 人気帯 ごとに、当てはまる馬を全部買った回収率を期間ごとに数え、
``RuleSelection`` の基準で採否を決める。入力は入口①の表だけで、元DB に触らない。
出力は ``reports/特徴量の組み合わせ探索/rules/``（Git 対象外）。
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "tools"), str(ROOT / "src")]

from yosou.custom_binary.feature.registrations import default_registry  # noqa: E402

from 特徴量の組み合わせ探索.analysis.condition_bins import ConditionBins  # noqa: E402
from 特徴量の組み合わせ探索.analysis.feature_table import FeatureTable  # noqa: E402
from 特徴量の組み合わせ探索.analysis.popularity_bands import PopularityBands  # noqa: E402
from 特徴量の組み合わせ探索.analysis.race_segments import RaceSegments  # noqa: E402
from 特徴量の組み合わせ探索.analysis.roi_scan import RoiScan  # noqa: E402
from 特徴量の組み合わせ探索.analysis.rule_selection import BET_TYPES, RuleSelection  # noqa: E402
from 特徴量の組み合わせ探索.analysis.search_periods import SearchPeriods  # noqa: E402

REPORTS = ROOT / "reports" / "特徴量の組み合わせ探索"
#: 馬の条件にしない特徴量。レースの区分・人気帯で扱うものと、オッズ・人気（人気帯で扱う）。
NOT_HORSE_CONDITIONS = {
    "競馬場", "芝ダ", "コース", "距離", "馬場状態", "人気順位", "単勝オッズ", "オッズから見た勝率", "オッズから見た3着以内率",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="条件だけで買うルールを探す", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=REPORTS / "cache")
    parser.add_argument("--out", type=Path, default=REPORTS / "rules")
    args = parser.parse_args()
    table = FeatureTable.load(args.cache)
    periods = SearchPeriods().names(table.rows["race_date"])
    discover = (periods == "見つける").to_numpy()
    registry = default_registry()
    conditions = [
        ConditionBins.fit(name, table.frame[name], registry.definitions[name].kind, discover)
        for name in table.frame.columns if name not in NOT_HORSE_CONDITIONS
    ]
    scan = RoiScan(table.rows, periods, RaceSegments.of(table.frame), PopularityBands(table.rows["popularity"]))
    counts = scan.run(conditions)
    args.out.mkdir(parents=True, exist_ok=True)
    selection = RuleSelection()
    summary = []
    for bet in BET_TYPES:
        wide = selection.wide(counts, bet)
        candidates = selection.candidates(wide)
        adopted = selection.adopted(wide)
        wide.to_pickle(args.out / f"{bet}_全ルール.pkl")
        adopted.to_csv(args.out / f"{bet}_採用.csv", index=False, encoding="utf-8-sig")
        summary.append(summarize(bet, wide, candidates, adopted))
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def summarize(bet: str, wide: pd.DataFrame, candidates: pd.DataFrame, adopted: pd.DataFrame) -> dict:
    """採用したルールが、テスト期間でどれだけ 100% を超えたか。偶然との比較のため、全ルールでの割合も出す。"""
    tested = wide[wide["テスト_点数"] >= 100]
    adopted_tested = adopted[adopted["テスト_点数"] >= 100]
    return {
        "券種": bet, "ルールの数": len(wide), "見つける期間で候補": len(candidates), "確かめる期間でも通過（採用）": len(adopted),
        "採用のうちテストで100%以上": int((adopted_tested["テスト_回収率"] >= 1).sum()),
        "採用のうちテストで点数100以上": len(adopted_tested),
        "全ルールでテスト100%以上の割合": float((tested["テスト_回収率"] >= 1).mean()),
        "採用のテストでの回収率（点数で重み付け）": weighted(adopted_tested),
        "候補（見つける期間だけ）のテストでの回収率": weighted(candidates[candidates["テスト_点数"] >= 100]),
    }


def weighted(rules: pd.DataFrame) -> float | None:
    if rules.empty:
        return None
    return float((rules["テスト_回収率"] * rules["テスト_点数"]).sum() / rules["テスト_点数"].sum())


if __name__ == "__main__":
    main()
