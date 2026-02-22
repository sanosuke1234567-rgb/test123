from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from main import build_default_rule_config
from models import VictoryConfig
from web_game import WebGame

RULE = build_default_rule_config(debug_ai_reason=False)
VICTORY = VictoryConfig(
    emperor_side_win_if_any_first_and_teammate_top_n=3,
    du_bao_mode_rule="default",
)
GAME = WebGame(RULE, VICTORY, seed=42)
GAME.new_game()


class Handler(BaseHTTPRequestHandler):
    def _redirect(self, path: str = "/") -> None:
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/state":
            vm = GAME.view_model()
            data = json.dumps(vm, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        vm = GAME.view_model()
        msg = ""
        if "?msg=" in self.path:
            msg = self.path.split("?msg=", 1)[1]
        body = self.render_html(vm, msg)
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length).decode("utf-8")
        form = parse_qs(data)
        if self.path == "/new":
            GAME.new_game()
            self._redirect("/")
            return
        if self.path == "/action":
            action = form.get("action", [""])[0]
            indexes_raw = form.get("indexes", [""])[0].replace(",", " ").strip()
            idxs = [int(x) for x in indexes_raw.split()] if indexes_raw else []
            res = GAME.human_action(action, idxs)
            self._redirect(f"/?msg={html.escape(res.message)}")
            return
        self.send_error(404)

    def log_message(self, format, *args):
        return

    def render_html(self, vm: dict, msg: str) -> str:
        hand_html = " ".join(html.escape(x) for x in vm.get("my_hand", []))
        logs = "\n".join(html.escape(l) for l in vm.get("logs", []))
        result_block = ""
        if vm.get("result"):
            r = vm["result"]
            result_block = f"""
            <div class='card'>
              <h3>对局结果</h3>
              <p>胜方: {html.escape(r['winner'])}</p>
              <p>名次: {' -> '.join('P'+str(i) for i in r['finish_order'])}</p>
              <p>{html.escape(r['explanation'])}</p>
            </div>
            """
        return f"""
<!doctype html>
<html lang='zh'>
<head>
<meta charset='utf-8'>
<title>山东保皇 Web 原型</title>
<style>
body{{font-family:Arial, sans-serif;max-width:1000px;margin:20px auto;}}
.card{{border:1px solid #ccc;border-radius:8px;padding:12px;margin-bottom:12px;}}
pre{{background:#111;color:#0f0;padding:10px;max-height:280px;overflow:auto;}}
input[type=text]{{width:240px;}}
</style>
</head>
<body>
<h1>山东保皇 Web 原型（1人+4AI）</h1>
<div class='card'>
  <p>皇帝: P{vm.get('emperor')} | 侍卫: {vm.get('guard')} | 当前轮到: P{vm.get('turn')}</p>
  <p>桌面待压牌: {html.escape(str(vm.get('last_play')))} | 当前领出: {vm.get('leader')}</p>
  <p>你的手牌({vm.get('my_hand_count')}张):<br>{hand_html}</p>
  <p>AI手牌数: {html.escape(str(vm.get('ai_hand_counts')))}</p>
  <p>完成名次: {html.escape(str(vm.get('finish_order')))}</p>
  <p style='color:#c00;'>{msg}</p>
</div>
<div class='card'>
  <form method='post' action='/action'>
    <input type='hidden' name='action' value='play'>
    <label>出牌索引(空格/逗号分隔): <input type='text' name='indexes' placeholder='例如: 0 1 2'></label>
    <button type='submit'>出牌</button>
  </form>
  <form method='post' action='/action' style='margin-top:8px;'>
    <input type='hidden' name='action' value='pass'>
    <button type='submit'>过牌</button>
  </form>
  <form method='post' action='/new' style='margin-top:8px;'>
    <button type='submit'>新开一局</button>
  </form>
</div>
{result_block}
<div class='card'>
  <h3>最近日志</h3>
  <pre>{logs}</pre>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Web server running on http://127.0.0.1:8000")
    server.serve_forever()
