import requests
from bs4 import BeautifulSoup

# ==================== 🛠️ 配置信息 ====================
# 1. 飞书 Webhook 链接
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/14306dcb-6db8-45a0-8107-147f7a339fd1"

# 2. Parks Canada 预订页面的真实 URL (请确保是选中目标日期后的网址)
BUS_URL = "https://example.com/shuttle-booking/2026-08-29"

# 3. 监控目标设置
TARGET_DATE = "2026-08-29"
TIME_WINDOW = "8am-9am"        # 目标时段
REQUIRED_SEATS = 2             # 人数
# ===================================================

def send_feishu_card(title, content_list, btn_url, card_color="orange"):
    """向飞书群推送高亮警告卡片"""
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
        print(f"飞书卡片推送结果: {response.status_code}")
    except Exception as e:
        print(f"飞书推送异常: {e}")

def check_seats():
    """解析 Parks Canada 表格，过滤 Last Minute，仅检查常规提前预订车位"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(BUS_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找表格中的行
        rows = soup.find_all('tr')
        regular_seats_found = False
        detail_msg = "常规预订行仍处于售罄/不可选状态"

        for row in rows:
            text_content = row.get_text(strip=True)
            
            # 精准匹配目标时段，且过滤掉带有 (Last Minute) 的干扰行
            if TIME_WINDOW.lower() in text_content.lower() and "last minute" not in text_content.lower():
                # 判断该常规行是否有“不可用/售罄”标识
                is_unavailable = any(kw in text_content.lower() for kw in ["unavailable", "sold out", "x", "满员", "售罄"])
                
                if not is_unavailable:
                    regular_seats_found = True
                    detail_msg = f"在常规预订通道 ({TIME_WINDOW}) 发现可用车位！"
                    break
        
        # 备用容错：如果解析不到 <tr>，做全文本过滤匹配
        if not rows and "last minute" in response.text.lower():
            cleaned_html = "\n".join([line for line in response.text.splitlines() if "last minute" not in line.lower()])
            if TIME_WINDOW.lower() in cleaned_html.lower() and not any(kw in cleaned_html.lower() for kw in ["sold out", "unavailable"]):
                regular_seats_found = True
                detail_msg = f"检测到常规 {TIME_WINDOW} 区域状态已更新为可预订！"

        return regular_seats_found, detail_msg

    except Exception as e:
        return False, f"网络请求或解析异常: {e}"

if __name__ == "__main__":
    print(f"🔍 正在检查 Parks Canada [{TARGET_DATE} {TIME_WINDOW}] 常规预订车位...")
    has_seats, info = check_seats()
    
    # 只要检测到常规通道有票，就触发飞书橙色卡片提醒
    if has_seats:
        print(f"🎉【重要提醒】{info}")
        send_feishu_card(
            "🚨【常规票空位提醒】Louis Shuttle 8/29 有常规预订车位了！",
            [
                f"**目标日期**：{TARGET_DATE} ({TIME_WINDOW})",
                f"**需求人数**：{REQUIRED_SEATS} 人",
                f"**最新状态**：🎉 **{info}**",
                "这是提前预订的常规座位！请点击下方按钮立即锁定！"
            ],
            BUS_URL,
            card_color="orange"
        )
    else:
        print(f"ℹ️ 状态正常: {info}")
