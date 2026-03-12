"""
data.json からスマホ向けHTMLを生成して docs/index.html に保存
"""
import json
from datetime import datetime

def load_data(path="docs/data.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def machine_card(m: dict) -> str:
    if m.get("error"):
        return f'<div class="card error">台{m["dai"]}: 取得失敗</div>'

    dai = m["dai"]
    block = m["block"]
    diff = m.get("current_diff")
    diff_str = f"{diff:+.0f}枚" if diff is not None else "—"
    diff_cls = "plus" if diff and diff > 0 else "minus" if diff and diff < 0 else ""

    s6 = m["setting6"]
    hyena = m["hyena"]
    counts = m["counts"]

    # 設定6スコアバー（最大8点）
    score = s6["score"]
    bar_pct = min(100, int(score / 8 * 100))
    bar_color = "#e74c3c" if score >= 6 else "#f39c12" if score >= 3 else "#95a5a6"

    s6_reasons_html = "".join(f"<li>{r}</li>" for r in s6["reasons"]) if s6["reasons"] else "<li>—</li>"
    hyena_reasons_html = "".join(f"<li>{r}</li>" for r in hyena["reasons"])

    hyena_badge = '<span class="badge hyena">🎯 ハイエナ狙い目</span>' if hyena["target"] else ""
    s6_badge = f'<span class="badge s6">{s6["label"]}</span>'

    bonus_info = f'BONUS {counts["bonus"]}回 (BIG {counts["big"]} / REG {counts["reg"]})'

    return f"""
<div class="card block-{block.lower()}">
  <div class="card-header">
    <span class="dai-no">台 {dai}</span>
    <span class="block-tag">ブロック{block}</span>
    {hyena_badge}
  </div>
  <div class="diff {diff_cls}">差枚: {diff_str}</div>
  <div class="bonus-info">{bonus_info}</div>

  <div class="section">
    <div class="section-title">設定6候補度</div>
    {s6_badge}
    <div class="score-bar-wrap">
      <div class="score-bar" style="width:{bar_pct}%;background:{bar_color}"></div>
    </div>
    <div class="score-num">スコア: {score}/8</div>
    <ul class="reasons">{s6_reasons_html}</ul>
  </div>

  <div class="section">
    <div class="section-title">ハイエナ判定</div>
    <ul class="reasons">{hyena_reasons_html}</ul>
  </div>
</div>
"""


def generate_html(data: dict) -> str:
    updated = data.get("updated", "—")
    machines = data.get("machines", [])

    # ブロック別に分割
    block_a = [m for m in machines if m.get("block") == "A"]
    block_b = [m for m in machines if m.get("block") == "B"]

    # ハイエナ狙い目台（全台）
    hyena_targets = [m for m in machines if not m.get("error") and m.get("hyena", {}).get("target")]

    # 設定6有力台
    s6_candidates = [m for m in machines if not m.get("error") and m.get("setting6", {}).get("score", 0) >= 6]

    # サマリー
    summary_items = ""
    if s6_candidates:
        for m in s6_candidates:
            summary_items += f'<li>🔴 台{m["dai"]}（ブロック{m["block"]}）— {m["setting6"]["label"]}</li>'
    else:
        summary_items += "<li>現時点で設定6有力台なし</li>"

    if hyena_targets:
        for m in hyena_targets:
            diff = m.get("current_diff")
            diff_str = f"{diff:+.0f}枚" if diff is not None else "—"
            summary_items += f'<li>🎯 台{m["dai"]}（ブロック{m["block"]}）差枚{diff_str}</li>'
    else:
        summary_items += "<li>現時点でハイエナ狙い目なし</li>"

    cards_a = "".join(machine_card(m) for m in block_a)
    cards_b = "".join(machine_card(m) for m in block_b)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ToLOVEる 設定6 & ハイエナチェッカー</title>
<script>
(function() {{
  var PASS = "7144";
  var key = "tlv_auth";
  if (sessionStorage.getItem(key) !== "ok") {{
    var input = prompt("パスワードを入力してください");
    if (input !== PASS) {{
      document.documentElement.innerHTML = "<body style='background:#000;color:#fff;font-family:sans-serif;padding:40px;text-align:center'><h2>認証失敗</h2><p>ページを再読み込みして再試行してください</p></body>";
      throw new Error("auth failed");
    }}
    sessionStorage.setItem(key, "ok");
  }}
}})();
</script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
  background: #1a1a2e;
  color: #eee;
  padding: 12px;
  font-size: 14px;
}}
h1 {{ font-size: 16px; color: #e94560; margin-bottom: 4px; }}
.updated {{ font-size: 11px; color: #888; margin-bottom: 12px; }}
.summary {{
  background: #16213e;
  border: 1px solid #e94560;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}}
.summary h2 {{ font-size: 14px; color: #e94560; margin-bottom: 8px; }}
.summary ul {{ padding-left: 16px; }}
.summary li {{ margin-bottom: 4px; font-size: 13px; }}

.block-title {{
  font-size: 15px;
  font-weight: bold;
  color: #0f3460;
  background: #e94560;
  padding: 6px 12px;
  border-radius: 8px;
  margin: 16px 0 8px;
}}
.card {{
  background: #16213e;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  border-left: 4px solid #444;
}}
.card.block-a {{ border-left-color: #e94560; }}
.card.block-b {{ border-left-color: #0f3460; }}
.card.error {{ opacity: 0.5; }}

.card-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}}
.dai-no {{ font-size: 18px; font-weight: bold; color: #fff; }}
.block-tag {{
  font-size: 11px;
  background: #333;
  padding: 2px 6px;
  border-radius: 4px;
  color: #aaa;
}}
.badge {{
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: bold;
}}
.badge.hyena {{ background: #27ae60; color: #fff; }}
.badge.s6 {{ background: #c0392b; color: #fff; }}

.diff {{
  font-size: 20px;
  font-weight: bold;
  margin: 4px 0;
}}
.diff.plus {{ color: #2ecc71; }}
.diff.minus {{ color: #e74c3c; }}

.bonus-info {{ font-size: 11px; color: #888; margin-bottom: 8px; }}

.section {{ margin-top: 10px; }}
.section-title {{
  font-size: 12px;
  color: #aaa;
  font-weight: bold;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
.score-bar-wrap {{
  background: #333;
  border-radius: 4px;
  height: 8px;
  margin: 4px 0;
  overflow: hidden;
}}
.score-bar {{
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}}
.score-num {{ font-size: 11px; color: #888; margin-bottom: 4px; }}
.reasons {{
  padding-left: 16px;
  font-size: 12px;
  color: #ccc;
}}
.reasons li {{ margin-bottom: 2px; }}

.reload-btn {{
  display: block;
  width: 100%;
  padding: 12px;
  background: #e94560;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 16px;
  text-align: center;
  text-decoration: none;
}}
</style>
</head>
<body>
<h1>🎰 ToLOVEる チェッカー</h1>
<div class="updated">最終更新: {updated}（約30分遅れ）</div>

<div class="summary">
  <h2>📋 注目台まとめ</h2>
  <ul>{summary_items}</ul>
</div>

<div class="block-title">📍 ブロックA（178〜185番）</div>
{cards_a}

<div class="block-title">📍 ブロックB（186〜192番）</div>
{cards_b}

<a class="reload-btn" href="javascript:location.reload()">🔄 画面を更新</a>
</body>
</html>"""


if __name__ == "__main__":
    data = load_data()
    html = generate_html(data)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html を生成しました")
