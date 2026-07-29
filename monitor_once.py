import datetime
import requests
from bs4 import BeautifulSoup

# ==================== 🛠️ 配置信息 ====================
# 1. 飞书 Webhook 链接
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/14306dcb-6db8-45a0-8107-147f7a339fd1"

# 2. Parks Canada 预订页面的真实 URL
BUS_URL = "https://example.com/shuttle-booking"

# 3. 监控目标设置
START_DATE = datetime.date(2026, 7, 30)
END_DATE = datetime.date(2026, 8, 26)
DATE_RANGE_STR = "2026-07-30 至 2026-08-26"

# 涵盖 8am 到 11am 之间的所有可能时段关键词
TIME_SLOTS = ["8am", "9am", "10am", "11am", "8:00", "9:00", "10:00", "11:00"]
REQUIRED_SEATS = 1             # 人数改为 1 张
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
    """解析 Parks Canada 表格，过滤 Last Minute，仅检查 7/30-8/26 期间 8:00 - 11:00 的常规提前预订车位"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(BUS_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = soup.find_all('tr')
        available_slots = []
        detail_msg = f"{DATE_RANGE_STR} (8:00 AM - 11:00 AM) 之间的常规预订仍处于售罄/不可选状态"

        for row in rows:
            text_content = row.get_text(strip=True)
            text_lower = text_content.lower()
            
            # 过滤掉带有 (Last Minute) 的干扰行
            if "last minute" in text_lower:
                continue

            # 判断该行是否匹配 8am - 11am 范围内的任意时段
            matches_time = any(slot in text_lower for slot in TIME_SLOTS)
            
            if matches_time:
                # 判断该常规行是否有“不可用/售罄”标识
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
    print(f"🔍 正在检查 Parks Canada [{DATE_RANGE_STR} 8:00 AM - 11:00 AM] 常规预订车位...")
    has_seats, info = check_seats()
    
    # 获取当前的 UTC 小时
    utc_now = datetime.datetime.utcnow()
    
    # 1. 🚨 情况一：一旦发现 7/30 - 8/26 期间 8:00 - 11:00 有常规预订空位，无论何时都触发【橙色抢票卡片】
    if has_seats:
        print(f"🎉【重要提醒】{info}")
        send_feishu_card(
            "🚨【常规票空位提醒】Louis Shuttle 发现空位！",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**目标时段**：8:00 AM - 11:00 AM",
                f"**需求人数**：{REQUIRED_SEATS} 人",
                f"**最新状态**：🎉 **{info}**",
                "这是提前预订的常规座位！请点击下方按钮立即锁定！"
            ],
            BUS_URL,
            card_color="orange"
        )
    # 2. ☀️ 情况二：在 UTC 12 点整点内（即 EDT 8:00 AM - 8:59 AM 之间），只要无空位，就触发【每日巡检日报】
    elif utc_now.hour == 12:
        print(f"☀️ 发送每日巡检日报...")
        send_feishu_card(
            "☀️【每日巡检日报】Louis Shuttle 车位监控运行中",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**目标时段**：8:00 AM - 11:00 AM",
                f"**巡检状态**：监控正常运行中",
                f"**最新车位情况**：{info}"
            ],
            BUS_URL,
            card_color="blue"
        )
    else:
        print(f"ℹ️ 扫描正常: {info}（未触发表格推送）")
