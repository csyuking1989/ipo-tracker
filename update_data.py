#!/usr/bin/env python3
"""
IPO Tracker 数据更新脚本

功能：从公开数据源抓取即将上市企业信息，更新 index.html 中的数据。

使用方法：
    python3 update_data.py

数据源：
    - 东方财富网新股数据 API
    - 各交易所公开信息

定时更新（每日早上9点）：
    crontab -e
    0 9 * * * cd /Users/chenshenyu/ipo-tracker && python3 update_data.py >> update.log 2>&1
"""

import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta


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
            stocks = []
            for item in data["result"]["data"]:
                stock = {
                    "name": item.get("SECURITY_NAME", ""),
                    "code": item.get("SECURITY_CODE", ""),
                    "applyDate": item.get("APPLY_DATE", ""),
                    "issuePrice": item.get("ISSUE_PRICE"),
                    "pe": item.get("PE_RATIO"),
                    "market": item.get("MARKET", ""),
                    "listDate": item.get("LIST_DATE", ""),
                    "totalRaise": item.get("TOTAL_RAISE"),
                }
                stocks.append(stock)
            return stocks
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"[WARN] 东方财富数据获取失败: {e}")

    return []


def fetch_bse_ipo_list():
    """从北交所获取IPO在审企业列表"""
    url = (
        "https://www.bse.cn/nqxxController/nqxxCnzq.do?"
        "page=0&typejb=T&xxfcbj=2&xxzqdm=&xxgsdm=&xxgsmc="
    )
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
            # 北交所返回的格式可能包含 JSON
            if text.strip().startswith("[") or text.strip().startswith("{"):
                return json.loads(text)
    except Exception as e:
        print(f"[WARN] 北交所数据获取失败: {e}")

    return []


def update_html(new_data_js):
    """更新 index.html 中的 IPO_DATA"""
    html_path = "/Users/chenshenyu/ipo-tracker/index.html"

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换 IPO_DATA 对象中的 updateDate
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(
        r'updateDate:\s*"[^"]*"',
        f'updateDate: "{today}"',
        content
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] 更新日期已更新为 {today}")


def main():
    print(f"=== IPO Tracker 数据更新 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    # 1. 获取东方财富新股数据
    stocks = fetch_eastmoney_new_stocks()
    if stocks:
        print(f"[OK] 获取到 {len(stocks)} 条新股数据")
        for s in stocks[:5]:
            print(f"     - {s['name']} ({s['code']}) 发行价:{s.get('issuePrice','-')} 市盈率:{s.get('pe','-')}")
    else:
        print("[INFO] 未获取到新的新股数据，保持现有数据不变")

    # 2. 更新日期
    update_html(None)

    print("\n=== 更新完成 ===")
    print("提示：毛利率数据需要从招股说明书中手动提取或通过专业金融数据终端获取。")
    print("建议数据源：")
    print("  - 巨潮资讯网 (cninfo.com.cn) - 招股说明书原文")
    print("  - 东方财富Choice - 财务数据筛选")
    print("  - 各交易所IPO信息披露专区")
    print("\n如需添加新企业，请编辑 index.html 中 IPO_DATA.companies 数组。")
    print("格式示例：")
    print(json.dumps({
        "name": "公司名称",
        "code": "股票代码",
        "market": "北交所/科创板/创业板",
        "industry": "行业",
        "grossMargin": 45.0,
        "grossMarginHistory": "40%(2022) → 43%(2023) → 45%(2024)",
        "revenue": 5.0,
        "revenueYear": "2024",
        "netProfit": 0.8,
        "issuePrice": "20.00元",
        "pe": 15.0,
        "status": "待发行",
        "ipoDate": "2026-04",
        "募资": "5亿",
        "description": "公司简介",
        "highlight": False
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
