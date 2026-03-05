#!/usr/bin/env python3
"""
定时抓取 IPO 数据，生成 data.json 供静态页面加载。
由 GitHub Actions 定时调用，无需人工维护。
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}


def _request_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_a_share_ipo():
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
            date_str = (list_date or apply_date)[:10] if (list_date or apply_date) else ""

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
            })
        return results
    except Exception as e:
        print(f"[WARN] A股数据获取失败: {e}")
        return []


def fetch_hk_ipo():
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
            date_str = (list_date or apply_end)[:10] if (list_date or apply_end) else ""

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
                "status": "已上市" if list_date else "招股中",
                "ipoDate": date_str,
                "募资": raise_str,
                "description": "",
                "highlight": False,
            })
        return results
    except Exception as e:
        print(f"[WARN] 港股数据获取失败: {e}")
        return []


def fetch_us_ipo():
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
            date_str = (list_date or declare_date)[:10] if (list_date or declare_date) else ""

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
                "status": "已上市" if list_date else "待上市",
                "ipoDate": date_str,
                "募资": raise_str,
                "description": "",
                "highlight": False,
            })
        return results
    except Exception as e:
        print(f"[WARN] 美股数据获取失败: {e}")
        return []


if __name__ == "__main__":
    a_shares = fetch_a_share_ipo()
    hk_shares = fetch_hk_ipo()
    us_shares = fetch_us_ipo()
    all_data = a_shares + hk_shares + us_shares
    print(f"[INFO] A股:{len(a_shares)} 港股:{len(hk_shares)} 美股:{len(us_shares)} 总计:{len(all_data)}")

    output = {
        "success": True,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(all_data),
        "companies": all_data,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] data.json 已生成 ({len(all_data)} 条记录)")
