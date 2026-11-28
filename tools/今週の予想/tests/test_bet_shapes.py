"""買い目の組を、まとめて買える形（フォーメーション・流し・ボックス）に書き直す。"""

from __future__ import annotations

from itertools import combinations, permutations

from 今週の予想.bet_shapes import BetShapes


def _trio(*horses: int) -> str:
    return "-".join(str(horse) for horse in sorted(horses))


def test_3連複は_フォーメーション_軸1頭流し_軸2頭流し_ボックスにまとめる() -> None:
    shapes = BetShapes()
    # 1頭目 2・6・7 − 2頭目 10 − 3頭目 1・2・5・6・7・11・16（同じ組は1点）の15点
    formation = {_trio(first, 10, third) for first in (2, 6, 7) for third in (1, 2, 5, 6, 7, 11, 16) if first != third}
    assert len(formation) == 15
    assert shapes.text(sorted(formation)) == "フォーメーション 10 − 2・6・7 − 1・2・5・6・7・11・16"
    # 全部の組に入る馬が無いフォーメーション（2頭目が2頭）
    wide = {_trio(first, second, third) for first in (2, 6) for second in (10, 12) for third in (1, 5)}
    assert shapes.text(sorted(wide)) == "フォーメーション 1・5 − 2・6 − 10・12"
    assert shapes.text(["2-7-10", "2-10-11", "2-7-11"]) == "軸1頭流し 軸 2 − 相手 7・10・11"
    assert shapes.text(["2-7-10", "2-7-11", "2-5-7"]) == "軸2頭流し 軸 2・7 − 相手 5・10・11"
    assert shapes.text([_trio(*picked) for picked in combinations((1, 2, 3, 4), 3)]) == "ボックス 1・2・3・4"
    assert shapes.text(["2-5-10"]) == "2-5-10"


def test_馬連とワイドは_流し_フォーメーション_ボックスにまとめる() -> None:
    shapes = BetShapes()
    assert shapes.text(["2-7", "1-2"]) == "流し 軸 2 − 相手 1・7"
    assert shapes.text(["1-3", "1-4", "2-3", "2-4"]) == "フォーメーション 1・2 − 3・4"
    assert shapes.text(["1-2", "1-3", "2-3"]) == "ボックス 1・2・3"


def test_馬単と3連単は_流し_フォーメーション_マルチ_ボックスにまとめる() -> None:
    shapes = BetShapes()
    assert shapes.text(["2→7", "2→1"]) == "1着流し 2 → 1・7"
    assert shapes.text(["7→2", "1→2"]) == "2着流し 1・7 → 2"
    assert shapes.text(["2→7", "7→2", "2→1", "1→2"]) == "マルチ 軸 2 − 相手 1・7"
    assert shapes.text(["1→3", "1→4", "2→3", "2→4"]) == "フォーメーション 1着 1・2 → 2着 3・4"
    trifectas = ["2→7→10", "2→1→10", "2→7→11", "2→1→11", "2→7→1", "2→7→6", "2→1→7", "2→1→6"]
    assert shapes.text(trifectas) == "フォーメーション 1着 2 → 2着 1・7 → 3着 1・6・7・10・11"
    multi = ["→".join(map(str, order)) for picked in combinations((1, 6, 7), 2) for order in permutations((2, *picked))]
    assert shapes.text(multi) == "軸1頭マルチ 軸 2 − 相手 1・6・7"
    assert shapes.text(["→".join(map(str, order)) for order in permutations((1, 2, 3))]) == "ボックス 1・2・3"


def test_1つの形にならない組は_馬で分けて形ごとに点数を添え_買う組は変えない() -> None:
    shapes = BetShapes()
    # 2 の流し（相手 5・7・10・16）と、10 の流しの残り（7・16）と、16→10
    labels = ["2→5", "2→7", "2→10", "2→16", "10→2", "10→7", "10→16", "16→10"]
    found = shapes.of(labels)
    assert [(shape.text, shape.points) for shape in found] == [("1着流し 2 → 5・7・10・16", 4), ("1着流し 10 → 2・7・16", 3), ("16→10", 1)]
    assert shapes.text(labels) == "1着流し 2 → 5・7・10・16（4点） ／ 1着流し 10 → 2・7・16（3点） ／ 16→10（1点）"
    # 3連複: 全部の組に入る馬が無く、フォーメーションにもならない
    trios = ["2-7-10", "2-8-10", "2-5-10", "7-10-16", "2-4-10", "1-3-9"]
    assert sum(shape.points for shape in shapes.of(trios)) == len(trios)
    assert shapes.text(trios) == "軸2頭流し 軸 2・10 − 相手 4・5・7・8（4点） ／ 7-10-16（1点） ／ 1-3-9（1点）"


def test_単勝と複勝は馬番を並べ_同じ番号が重なる組は1点ずつ_空は空() -> None:
    shapes = BetShapes()
    assert shapes.text(["3", "8"]) == "3・8"
    assert shapes.text(["1-1", "1-2"]) == "1-1（1点） ／ 1-2（1点）"
    assert shapes.of([]) == [] and shapes.text([]) == ""


def test_額の違う買い目は_同じ額の組だけをまとめて額の大きい順に書く() -> None:
    shapes = BetShapes()
    assert shapes.staked_text([("2-7", 700), ("1-2", 1200)]) == "1-2 1,200円 ／ 2-7 700円"
    staked = [("2→7→10", 100), ("2→1→10", 100), ("2→7→1", 300), ("2→1→7", 100)]
    assert shapes.staked_text(staked) == "2→7→1 300円 ／ フォーメーション 1着 2 → 2着 1・7 → 3着 7・10 各 100円（3点）"
    assert shapes.staked_text([("3", 2000)]) == "3 2,000円"
