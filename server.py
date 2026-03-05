#!/usr/bin/env python3
"""
IPO Tracker 本地服务器

功能：
  - 提供 index.html 静态页面
  - /api/data 接口：返回A股、港股、美股IPO数据
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
import urllib.request
import urllib.error
from datetime import datetime, timedelta

PORT = 8686
DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}


def _request_json(url, timeout=15):
    """通用请求函数"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── A股新股 ──────────────────────────────────────────────

def fetch_a_share_ipo():
    """从东方财富获取A股新股申购数据"""
    since = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        "sortColumns=APPLY_DATE&sortTypes=-1&pageSize=50&pageNumber=1"
        "&reportName=RPTA_APP_IPOAPPLY"
        "&columns=ALL&quoteColumns=&quoteType=0&source=WEB&client=WEB"
        f"&filter=(APPLY_DATE>='{since}')"
    )
    try:
        data = _request_json(url)
        if not (data.get("success") and data.get("result", {}).get("data")):
            return []
        results = []
        for item in data["result"]["data"]:
            board = item.get("MARKET", "")
            if "北" in board:
                market = "北交所"
            elif "科创" in board:
                market = "科创板"
            elif "创业" in board:
                market = "创业板"
            elif "沪" in board:
                market = "沪市主板"
            elif "深" in board:
                market = "深市主板"
            else:
                market = board or "A股"

            list_date = item.get("LIST_DATE") or ""
            apply_date = item.get("APPLY_DATE") or ""
            date_str = ""
            if list_date:
                date_str = list_date[:10]
            elif apply_date:
                date_str = apply_date[:10]

            price = item.get("ISSUE_PRICE")
            results.append({
                "name": item.get("SECURITY_NAME", ""),
                "code": item.get("SECURITY_CODE", ""),
                "market": market,
                "industry": item.get("INDUSTRY_PE_NEW", {}).get("INDUSTRY_NAME", "") if isinstance(item.get("INDUSTRY_PE_NEW"), dict) else "",
                "grossMargin": None,
                "grossMarginHistory": "",
                "revenue": None,
                "revenueYear": None,
                "netProfit": None,
                "issuePrice": f"{price}元" if price else None,
                "pe": item.get("PE_RATIO"),
                "status": "已上市" if list_date else "申购中",
                "ipoDate": date_str,
                "募资": None,
                "description": "",
                "highlight": False,
                "source": "eastmoney_a",
            })
        return results
    except Exception as e:
        print(f"[WARN] A股数据获取失败: {e}")
        return []


# ── 港股新股 ──────────────────────────────────────────────

def fetch_hk_ipo():
    """从东方财富获取港股IPO数据"""
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        "sortColumns=APPLY_END_DATE&sortTypes=-1&pageSize=50&pageNumber=1"
        "&reportName=RPT_HKIPO_BASICINFO"
        "&columns=ALL&quoteColumns=&quoteType=0&source=WEB&client=WEB"
    )
    try:
        data = _request_json(url)
        if not (data.get("success") and data.get("result", {}).get("data")):
            return []
        results = []
        for item in data["result"]["data"]:
            list_date = item.get("LIST_DATE") or ""
            apply_end = item.get("APPLY_END_DATE") or ""
            date_str = ""
            if list_date:
                date_str = list_date[:10]
            elif apply_end:
                date_str = apply_end[:10]

            price_low = item.get("ISSUE_PRICE_LOW")
            price_high = item.get("ISSUE_PRICE_HIGH")
            issue_price_val = item.get("ISSUE_PRICE")
            if issue_price_val:
                price_str = f"HK${issue_price_val}"
            elif price_low and price_high:
                price_str = f"HK${price_low}-{price_high}"
            else:
                price_str = None

            total_raise = item.get("TOTAL_RAISE")
            raise_str = None
            if total_raise:
                if total_raise >= 100000000:
                    raise_str = f"{total_raise / 100000000:.1f}亿港元"
                else:
                    raise_str = f"{total_raise / 10000:.0f}万港元"

            status = "已上市" if list_date else "招股中"

            results.append({
                "name": item.get("SECURITY_NAME_ABBR", "") or item.get("SECURITY_NAME", ""),
                "code": item.get("SECURITY_CODE", ""),
                "market": "港股",
                "industry": item.get("INDUSTRY", "") or "",
                "grossMargin": None,
                "grossMarginHistory": "",
                "revenue": None,
                "revenueYear": None,
                "netProfit": None,
                "issuePrice": price_str,
                "pe": item.get("PE_RATIO"),
                "status": status,
                "ipoDate": date_str,
                "募资": raise_str,
                "description": "",
                "highlight": False,
                "source": "eastmoney_hk",
            })
        return results
    except Exception as e:
        print(f"[WARN] 港股数据获取失败: {e}")
        return []


# ── 美股IPO ──────────────────────────────────────────────

def fetch_us_ipo():
    """从东方财富获取美股IPO数据"""
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        "sortColumns=DECLARE_DATE&sortTypes=-1&pageSize=50&pageNumber=1"
        "&reportName=RPT_USIPO_BASICINFO"
        "&columns=ALL&quoteColumns=&quoteType=0&source=WEB&client=WEB"
    )
    try:
        data = _request_json(url)
        if not (data.get("success") and data.get("result", {}).get("data")):
            return []
        results = []
        for item in data["result"]["data"]:
            list_date = item.get("LIST_DATE") or ""
            declare_date = item.get("DECLARE_DATE") or ""
            date_str = ""
            if list_date:
                date_str = list_date[:10]
            elif declare_date:
                date_str = declare_date[:10]

            price_low = item.get("ISSUE_PRICE_LOW")
            price_high = item.get("ISSUE_PRICE_HIGH")
            issue_price_val = item.get("ISSUE_PRICE")
            if issue_price_val:
                price_str = f"${issue_price_val}"
            elif price_low and price_high:
                price_str = f"${price_low}-{price_high}"
            else:
                price_str = None

            total_raise = item.get("TOTAL_RAISE")
            raise_str = None
            if total_raise:
                if total_raise >= 100000000:
                    raise_str = f"${total_raise / 100000000:.1f}亿"
                elif total_raise >= 10000:
                    raise_str = f"${total_raise / 10000:.0f}万"
                else:
                    raise_str = f"${total_raise:.0f}"

            status = "已上市" if list_date else "待上市"

            results.append({
                "name": item.get("SECURITY_NAME_ABBR", "") or item.get("SECURITY_NAME", ""),
                "code": item.get("SECURITY_CODE", ""),
                "market": "美股",
                "industry": item.get("INDUSTRY", "") or "",
                "grossMargin": None,
                "grossMarginHistory": "",
                "revenue": None,
                "revenueYear": None,
                "netProfit": None,
                "issuePrice": price_str,
                "pe": item.get("PE_RATIO"),
                "status": status,
                "ipoDate": date_str,
                "募资": raise_str,
                "description": "",
                "highlight": False,
                "source": "eastmoney_us",
            })
        return results
    except Exception as e:
        print(f"[WARN] 美股数据获取失败: {e}")
        return []


# ── 数据合并 & 更新 ──────────────────────────────────────

def fetch_all_ipo():
    """获取所有市场IPO数据"""
    a_shares = fetch_a_share_ipo()
    hk_shares = fetch_hk_ipo()
    us_shares = fetch_us_ipo()
    print(f"[INFO] 获取数据 - A股:{len(a_shares)} 港股:{len(hk_shares)} 美股:{len(us_shares)}")
    return a_shares + hk_shares + us_shares


def do_update():
    """执行数据更新，返回结果摘要"""
    html_path = os.path.join(DIR, "index.html")
    now = datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M")

    # 获取所有市场数据
    api_stocks = fetch_all_ipo()

    # 更新 HTML 中的日期
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'updateDate:\s*"[^"]*"',
        f'updateDate: "{today}"',
        content
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    counts = {}
    for s in api_stocks:
        m = s["market"]
        counts[m] = counts.get(m, 0) + 1

    return {
        "success": True,
        "time": today,
        "fetched": len(api_stocks),
        "breakdown": counts,
        "message": f"更新完成，共获取 {len(api_stocks)} 条数据 ({', '.join(f'{k}:{v}' for k, v in counts.items())})"
                   if api_stocks else "更新完成，API暂无返回数据，页面日期已更新"
    }


# ── 缓存 ──────────────────────────────────────────────

_cache = {"data": None, "time": None}
CACHE_TTL = 300  # 5分钟缓存


def get_api_data():
    """获取API数据（带缓存）"""
    now = datetime.now()
    if _cache["data"] and _cache["time"] and (now - _cache["time"]).seconds < CACHE_TTL:
        return _cache["data"]

    stocks = fetch_all_ipo()
    _cache["data"] = stocks
    _cache["time"] = now
    return stocks


# ── HTTP 服务 ──────────────────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/update":
            self.handle_update()
        elif self.path == "/api/data":
            self.handle_data()
        elif self.path == "/" or self.path == "":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def handle_update(self):
        try:
            # 清除缓存以强制刷新
            _cache["data"] = None
            _cache["time"] = None
            result = do_update()
            self._json_response(200, result)
        except Exception as e:
            self._json_response(500, {"success": False, "message": str(e)})

    def handle_data(self):
        try:
            stocks = get_api_data()
            self._json_response(200, {
                "success": True,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "total": len(stocks),
                "companies": stocks,
            })
        except Exception as e:
            self._json_response(500, {"success": False, "message": str(e), "companies": []})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    print(f"IPO Tracker 服务已启动（支持A股/港股/美股）")
    print(f"访问地址: http://localhost:{PORT}")
    print(f"数据接口: http://localhost:{PORT}/api/data")
    print(f"手动更新: http://localhost:{PORT}/api/update")
    print(f"按 Ctrl+C 停止\n")
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
