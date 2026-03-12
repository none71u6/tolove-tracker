"""
ToLOVEる ダークネス 設定6候補 & ハイエナ狙い目 チェッカー
対象台: 178〜192番
- 178〜185: ブロックA（最低1台設定6）
- 186〜192: ブロックB（最低1台設定6）
"""

import re
import json
import math
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
import time

# ============================================================
# 設定
# ============================================================
BASE_URL = "https://www.pscube.jp/h/a763601/cgi-bin/nc-v06-001.php?cd_dai={:04d}"
DAI_RANGE = list(range(178, 193))  # 178〜192

BLOCK_A = list(range(178, 186))  # 178〜185
BLOCK_B = list(range(186, 193))  # 186〜192

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept-Language": "ja,en;q=0.9",
}

# ============================================================
# スクレイピング
# ============================================================

def fetch_page(dai_no: int) -> str:
    url = BASE_URL.format(dai_no)
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except URLError as e:
        print(f"  [ERROR] 台{dai_no}: {e}")
        return ""


def parse_history(html: str) -> list[dict]:
    """特賞履歴をパース。[{count, time, games, type}, ...]（新しい順）"""
    tbody = re.search(r'id="tblHISTb"[^>]*>(.*?)</tbody>', html, re.DOTALL)
    if not tbody:
        return []
    rows = re.findall(
        r'<td[^>]*>(\d+)</td>\s*<td>([\d:]+)</td>\s*<td>(\d+)</td>\s*<td>(BIG|REG)</td>',
        tbody.group(1)
    )
    result = []
    for count, t, games, btype in rows:
        result.append({
            "count": int(count),
            "time": t,
            "games": int(games),
            "type": btype,
        })
    # 回数の昇順（古い順）に並べ直す
    result.sort(key=lambda x: x["count"])
    return result


def parse_slump_graph(html: str) -> list[float]:
    """
    当日スランプグラフのSVGパスから差枚リストを返す。
    Y軸: pixel 229.5 = 0枚, 0.5 = +2000枚, 457.5 = -2000枚
    → diff_mai = 2000 - (y_pixel / 457) * 4000
    """
    # 当日グラフ（svg0）のブロックを抽出
    idx = html.find('id="svg0"')
    if idx < 0:
        return []
    chunk = html[idx: idx + 30000]

    graph_paths = re.findall(
        r'amcharts-graph-line[^>]*>.*?<path[^>]*d="([^"]+)"',
        chunk, re.DOTALL
    )
    if not graph_paths:
        return []

    coords = re.findall(r'[ML]([\d.]+),([\d.]+)', graph_paths[0])
    diff_list = []
    for x, y in coords:
        yf = float(y)
        if yf == 0:
            continue
        diff_mai = 2000 - (yf / 457) * 4000
        diff_list.append(round(diff_mai))
    return diff_list


def parse_bonus_count(html: str) -> dict:
    """当日BONUS/BIG/REG回数と合成確率をパース"""
    bonus = re.search(r'<td class="col-1">BONUS</td>\s*<td class="col-2">(\d+)</td>', html)
    big   = re.search(r'<td class="col-1">BIG</td>\s*<td class="col-2">(\d+)</td>', html)
    reg   = re.search(r'<td class="col-1">REG</td>\s*<td class="col-2">(\d+)</td>', html)
    gosei = re.search(r'<td class="col-1">合成確率</td>\s*<td class="col-2">1/([\d.]+)</td>', html)
    return {
        "bonus": int(bonus.group(1)) if bonus else 0,
        "big":   int(big.group(1))   if big   else 0,
        "reg":   int(reg.group(1))   if reg   else 0,
        "gosei": float(gosei.group(1)) if gosei else None,
    }


# ============================================================
# 分析ロジック
# ============================================================

def analyze_setting6(history: list[dict], diff_list: list[float]) -> dict:
    """
    設定6らしさスコアを算出。
    ポイント:
      1. 250G以降当選後に差枚が大きく伸びた回数（優遇）
      2. 650Gゾーン当選（650〜700G or 1000G以上）の有無
      3. ジグザグ度（優遇冷遇の波の大きさ）
    """
    score = 0
    reasons = []

    # --- 1. 250G以降当選後の大きな出玉上昇 ---
    over250_big_bounce = 0
    for i, h in enumerate(history):
        if h["games"] >= 250 and h["type"] == "BIG":
            # 直後の差枚変化をdiff_listから推定（履歴インデックスとdiff_listは完全一致しないので概算）
            over250_big_bounce += 1

    if over250_big_bounce >= 3:
        score += 3
        reasons.append(f"250G以降BIG当選が{over250_big_bounce}回（優遇パターン多数）")
    elif over250_big_bounce >= 2:
        score += 1
        reasons.append(f"250G以降BIG当選が{over250_big_bounce}回")

    # --- 2. 650Gゾーン当選 ---
    zone650 = [h for h in history if 650 <= h["games"] <= 700 or h["games"] >= 1000]
    if len(zone650) >= 2:
        score += 2
        reasons.append(f"650Gゾーン/天井当選が{len(zone650)}回")
    elif len(zone650) == 1:
        score += 1
        reasons.append(f"650Gゾーン/天井当選が{len(zone650)}回")

    # --- 3. ジグザグ度（差枚の上下動の激しさ）---
    zigzag_score = 0
    if len(diff_list) >= 4:
        # 連続する差枚変化量の符号反転回数（山谷の数）
        changes = [diff_list[i+1] - diff_list[i] for i in range(len(diff_list)-1)]
        reversals = sum(
            1 for i in range(len(changes)-1)
            if changes[i] * changes[i+1] < 0
            and abs(changes[i]) > 150  # 150枚以上の反転のみカウント
        )
        # 最大振れ幅
        amp = max(diff_list) - min(diff_list)

        if reversals >= 6 and amp >= 800:
            zigzag_score = 3
            reasons.append(f"大きなジグザグあり（反転{reversals}回, 振れ幅{amp:.0f}枚）")
        elif reversals >= 4 and amp >= 500:
            zigzag_score = 2
            reasons.append(f"ジグザグあり（反転{reversals}回, 振れ幅{amp:.0f}枚）")
        elif reversals >= 2:
            zigzag_score = 1
        score += zigzag_score

    # --- 4. 連チャン中の出玉増加量（250G以降当選後の増加を推定）---
    # historyのgames>=250かつ次の数回で大きく増加しているかを特賞回数から推定
    big_streaks_after_250 = []
    i = 0
    while i < len(history):
        if history[i]["games"] >= 250:
            # 連チャンの開始
            streak = []
            j = i + 1
            while j < len(history) and history[j]["games"] <= 20:
                streak.append(history[j])
                j += 1
            if len(streak) >= 2:
                big_streaks_after_250.append(len(streak))
            i = j
        else:
            i += 1

    if big_streaks_after_250:
        avg_streak = sum(big_streaks_after_250) / len(big_streaks_after_250)
        if avg_streak >= 4:
            score += 2
            reasons.append(f"250G以降当選後の平均連チャン{avg_streak:.1f}回（優遇の波）")
        elif avg_streak >= 2.5:
            score += 1
            reasons.append(f"250G以降当選後の平均連チャン{avg_streak:.1f}回")

    label = "🔴 設定6有力" if score >= 6 else "🟡 要注目" if score >= 3 else "⚪ 低設定の可能性"
    return {"score": score, "label": label, "reasons": reasons}


def analyze_hyena(history: list[dict], diff_list: list[float]) -> dict:
    """
    ハイエナ狙い目を判定。
    条件（すろらぼ基準）:
      A. 前回1000G以上当選 かつ 駆け抜け後（出玉100枚以下 ≒ REG or 少ない連チャン）→ 0Gから打てる
      B. 前回出玉が100枚以下（駆け抜け）→ 優遇状態で次当選後に出やすい
      C. 有利区間差枚が大きくマイナス → 次回AT性能が優遇される
    """
    if not history:
        return {"target": False, "reason": "データなし"}

    latest = history[-1]  # 最新の当選
    prev_games = latest["games"]
    prev_type = latest["type"]
    current_diff = diff_list[-1] if diff_list else None

    reasons = []
    target = False

    # A: 前回1000G以上当選（天井）＋駆け抜け（連チャン少ない）
    if prev_games >= 1000:
        # 連チャン数を確認（最新当選の直前の連チャン）
        # historyは昇順なので最後の要素の前の連チャンをカウント
        streak = 0
        for i in range(len(history)-2, -1, -1):
            if history[i]["games"] <= 20:
                streak += 1
            else:
                break
        if streak <= 1:
            target = True
            reasons.append(f"✅ 前回天井({prev_games}G)かつ駆け抜け → 0Gから狙える")
        else:
            reasons.append(f"前回天井({prev_games}G)だが連チャン{streak}回あり（冷遇気味）")

    # B: 差枚がマイナス（優遇状態）
    if current_diff is not None and current_diff <= -500:
        target = True
        reasons.append(f"✅ 有利区間差枚 {current_diff:.0f}枚（優遇状態）")
    elif current_diff is not None and current_diff <= -200:
        reasons.append(f"△ 有利区間差枚 {current_diff:.0f}枚（やや優遇）")

    # C: 前回出玉が少ない（駆け抜け）→ 次回優遇
    if prev_type == "REG" or (len(history) >= 2 and history[-2]["games"] > 100):
        # 最後がREGで終わりか、直前が100G以上で当たっている（連チャン終了後）
        pass  # Aで既にカバー

    if not reasons:
        reasons.append("現時点では狙い目なし")

    return {"target": target, "reasons": reasons}


# ============================================================
# メイン処理
# ============================================================

def scrape_all() -> list[dict]:
    results = []
    for dai_no in DAI_RANGE:
        print(f"取得中: 台{dai_no}...")
        html = fetch_page(dai_no)
        if not html:
            results.append({"dai": dai_no, "error": True})
            time.sleep(1)
            continue

        history = parse_history(html)
        diff_list = parse_slump_graph(html)
        counts = parse_bonus_count(html)

        s6 = analyze_setting6(history, diff_list)
        hyena = analyze_hyena(history, diff_list)

        results.append({
            "dai": dai_no,
            "error": False,
            "history_count": len(history),
            "counts": counts,
            "current_diff": diff_list[-1] if diff_list else None,
            "setting6": s6,
            "hyena": hyena,
            "block": "A" if dai_no in BLOCK_A else "B",
        })
        time.sleep(0.8)  # サーバー負荷軽減

    return results


def save_json(results: list[dict], path: str = "docs/data.json"):
    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "machines": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"JSONを保存: {path}")


if __name__ == "__main__":
    results = scrape_all()
    save_json(results)
    print("完了！")
