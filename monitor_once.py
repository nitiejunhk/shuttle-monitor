import datetime
import requests
from bs4 import BeautifulSoup

# ==================== 🛠️ 配置信息 ====================
# 1. 飞书 Webhook 链接
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/14306dcb-6db8-45a0-8107-147f7a339fd1"

# 2. Parks Canada 预订页面的真实 URL
BUS_URL = "https://example.com/shuttle-booking"

# 3. 监控目标设置
START_DATE = datetime.date(2026, 7, 29)
END_DATE = datetime.date(2026, 8, 7)
DATE_RANGE_STR = "2026-07-29 至 2026-08-07"

# 涵盖 6am 到 11am 之间的所有可能时段关键词
TIME_SLOTS = [
    "6am", "7am", "8am", "9am", "10am", "11am",
    "6:00", "7:00", "8:00", "9:00", "10:00", "11:00"
]

# 双湖路线关键词（包含 Lake Louise 或 Moraine Lake）
TARGET_ROUTES = ["lake louise", "moraine lake", "moraine"]

REQUIRED_SEATS = 1             # 1 张票
# ===================================================

def send_feishu_card(title, content_list, btn_url, card_color="orange"):
    """向飞书群推送格式化卡片"""
    elements = []
    
    for text in content_list:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": text
            }
        })
    
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "👉 立即前往网页抢票"
                },
                "type": "primary",
                "url": btn_url
            }
        ]
    })

    card_payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": card_color
            },
            "elements": elements
        }
    }

    try:
        response = requests.post(FEISHU_WEBHOOK, json=card_payload, timeout=10)
        print(f"飞书卡片推送结果状态码: {response.status_code}")
    except Exception as e:
        print(f"飞书推送异常: {e}")

def check_seats():
    """同时监控 Lake Louise 和 Moraine Lake 预订通道 (7/29-8/7 6:00 - 11:00)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(BUS_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = soup.find_all('tr')
        available_slots = []
        detail_msg = f"{DATE_RANGE_STR} (6:00 AM - 11:00 AM) 的 Lake Louise 及 Moraine Lake 路线常规车票仍售罄"

        for row in rows:
            text_content = row.get_text(strip=True)
            text_lower = text_content.lower()
            
            # 过滤掉带有 (Last Minute) 的干扰行
            if "last minute" in text_lower:
                continue

            # 1. 匹配目标时段 6am - 11am
            matches_time = any(slot in text_lower for slot in TIME_SLOTS)
            
            # 2. 匹配路线（Lake Louise 或 Moraine Lake 均可）
            matches_route = any(route in text_lower for route in TARGET_ROUTES) or len(TARGET_ROUTES) == 0

            if matches_time and matches_route:
                # 判断该行是否有“不可用/售罄”标识
                is_unavailable = any(kw in text_lower for kw in ["unavailable", "sold out", "x", "满员", "售罄"])
                
                if not is_unavailable:
                    available_slots.append(text_content)
        
        if available_slots:
            detail_msg = f"在常规预订通道发现可用车位 ({REQUIRED_SEATS}张)：{' | '.join(available_slots)}"
            return True, detail_msg

        return False, detail_msg

    except Exception as e:
        return False, f"网络请求或解析异常: {e}"

if __name__ == "__main__":
    print(f"🔍 正在双向监控 Lake Louise & Moraine Lake [{DATE_RANGE_STR} 6:00 AM - 11:00 AM] 常规预订车位...")
    has_seats, info = check_seats()
    
    # 获取当前的 UTC 小时
    utc_now = datetime.datetime.utcnow()
    
    # 1. 🚨 情况一：只要任意一条线路在目标时段刷出票，立即触发【橙色抢票卡片】
    if has_seats:
        print(f"🎉【重要提醒】{info}")
        send_feishu_card(
            "🚨【双湖常规票空位提醒】Shuttle 发现空位！",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**目标路线**：Lake Louise & Moraine Lake",
                f"**目标时段**：6:00 AM - 11:00 AM",
                f"**需求人数**：{REQUIRED_SEATS} 人",
                f"**最新状态**：🎉 **{info}**",
                "提示：凭任意一湖的 Shuttle 车票，均可免费搭乘 Connector 巴士游览另一个湖！"
            ],
            BUS_URL,
            card_color="orange"
        )
    # 2. ☀️ 情况二：在 UTC 12 点整点内（EDT 8:00 AM），触发【每日巡检日报】
    elif utc_now.hour == 12:
        print(f"☀️ 发送每日巡检日报...")
        send_feishu_card(
            "☀️【每日巡检日报】双湖 Shuttle 车位监控运行中",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**监控路线**：Lake Louise & Moraine Lake",
                f"**目标时段**：6:00 AM - 11:00 AM",
                f"**巡检状态**：双线路监控正常运行中",
                f"**最新车位情况**：{info}"
            ],
            BUS_URL,
            card_color="blue"
        )
    else:
        print(f"ℹ️ 扫描正常: {info}（未触发表格推送）")
