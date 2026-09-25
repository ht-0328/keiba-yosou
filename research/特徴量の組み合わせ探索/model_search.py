"""custom_binary のモデルで、回収率 100% を超える設定を探す（研究「特徴量の組み合わせ探索」の入口③）。

    uv run python research/特徴量の組み合わせ探索/model_search.py [--only 名前 ...]

設定ごとに、見つける期間で学習 → 確かめる期間で早期終了と買い方の選択 → テスト期間で1回だけ確かめる。
入力は入口①の表だけで、元DB に触らない。出力は ``reports/特徴量の組み合わせ探索/models/``（Git 対象外）。
済んだ設定は飛ばすので、止まっても続きから動かせる。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "tools"), str(ROOT / "src")]

from yosou.custom_binary.feature.registrations import default_registry  # noqa: E402

from 特徴量の組み合わせ探索.analysis.feature_table import FeatureTable  # noqa: E402
from 特徴量の組み合わせ探索.analysis.model_configs import model_configs  # noqa: E402
from 特徴量の組み合わせ探索.analysis.model_trial import ModelTrial  # noqa: E402
from 特徴量の組み合わせ探索.analysis.search_periods import SearchPeriods  # noqa: E402

REPORTS = ROOT / "reports" / "特徴量の組み合わせ探索"


def main() -> None:
    parser = argparse.ArgumentParser(description="custom_binary のモデルで探す", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=REPORTS / "cache")
    parser.add_argument("--out", type=Path, default=REPORTS / "models")
    parser.add_argument("--only", nargs="+", default=None, help="この名前の設定だけ動かす")
    parser.add_argument("--group", choices=("form", "pool"), default="form",
                        help="form: 馬柱の特徴量の探索、pool: 券種オッズの特徴量を足した探索")
    args = parser.parse_args()
    table = FeatureTable.load(args.cache)
    trial = ModelTrial(table, default_registry(), SearchPeriods())
    args.out.mkdir(parents=True, exist_ok=True)
    for config in model_configs(args.group):
        path = args.out / f"{config.name}.json"
        if path.exists() or (args.only and config.name not in args.only):
            continue
        result = trial.run(config)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        chosen, tested = result["選んだ買い方"], result["テストでの結果"]
        line = "買い方なし" if chosen is None else (
            f"{chosen['買い方']} 確かめる{chosen[config.bet + '回収率']:.3f}（{chosen['点数']}点）"
            f" → テスト{tested[config.bet + '回収率']:.3f}（{tested['点数']}点）"
        )
        print(f"{config.name}: {line}（{result['秒']}秒）", flush=True)


if __name__ == "__main__":
    main()
