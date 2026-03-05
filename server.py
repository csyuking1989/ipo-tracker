#!/usr/bin/env python3
"""
IPO Tracker 本地服务器

功能：
  - 提供 index.html 静态页面
  - /api/update 接口：手动触发数据更新

启动：
  cd ~/ipo-tracker && python3 server.py

访问：
  http://localhost:8686
"""

import http.server
import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timedelta

PORT = 8686
DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_eastmoney_new_stocks():
    """从东方财富网获取新股申购数据"""
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        "sortColumns=APPLY_DATE&sortTypes=-1&pageSize=50&pageNumber=1"
        "&reportName=RPTA_APP_IPOAPPLY"
        "&columns=ALL&quoteColumns=&quoteType=0&source=WEB&client=WEB"
        "&filter=(APPLY_DATE>='{}')".format(
            (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        )
    )
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Referer": "https://data.eastmoney.com/",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success") and data.get("result", {}).get("data"):
            return data["result"]["data"]
    except Exception as e:
        print(f"[WARN] 东方财富数据获取失败: {e}")
    return []


def do_update():
    """执行数据更新，返回结果摘要"""
    html_path = os.path.join(DIR, "index.html")
    now = datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M")

    # 1. 尝试获取新股数据
    stocks = fetch_eastmoney_new_stocks()
    fetched_count = len(stocks)
    stock_names = [s.get("SECURITY_NAME", "") for s in stocks[:10]]

    # 2. 更新 HTML 中的日期
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'updateDate:\s*"[^"]*"',
        f'updateDate: "{today}"',
        content
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "time": today,
        "fetched": fetched_count,
        "samples": stock_names,
        "message": f"更新完成，获取到 {fetched_count} 条新股数据" if fetched_count else "更新完成，东方财富API暂无返回数据，页面日期已更新"
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/update":
            self.handle_update()
        elif self.path == "/" or self.path == "":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def handle_update(self):
        try:
            result = do_update()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False, "message": str(e)
            }, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    print(f"IPO Tracker 服务已启动")
    print(f"访问地址: http://localhost:{PORT}")
    print(f"手动更新: http://localhost:{PORT}/api/update")
    print(f"按 Ctrl+C 停止\n")
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
