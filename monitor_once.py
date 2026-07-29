import datetime
import requests
from bs4 import BeautifulSoup
import re

# ==================== 🛠️ 配置信息 ====================
# 1. 飞书 Webhook 链接
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/14306dcb-6db8-45a0-8107-147f7a339fd1"

# 2. Parks Canada 预订页面的真实 URL (请务必确保这是包含你截图表格的真实页面)
# 这里仍然使用占位符，请替换为你实际监控的网址
BUS_URL = "https://example.com/shuttle-booking"

# 3. 监控目标设置
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

def check_seats_optimized():
    """优化后的解析逻辑：深入单元格判断，精准识别‘常规票’行中的个别余票"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        print(f"📡 正在请求页面: {BUS_URL}")
        response = requests.get(BUS_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return False, f"⚠️ 页面请求失败，状态码: {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 找到页面上的所有表格行
        rows = soup.find_all('tr')
        if not rows:
            return False, "⚠️ 未在页面上找到任何表格行（tr标签），可能页面结构已改变或URL错误。"

        available_slots = []
        detail_msg = f"{DATE_RANGE_STR} (6:00 AM - 11:00 AM) 的双湖车票（含常规及临期）仍处于售罄状态"

        # 售罄关键词列表（用于过滤不可用的单元格）
        UNAVAILABLE_KEYWORDS = ["unavailable", "sold out", "x", "×", "满员", "售罄"]

        print(f"🔄 开始解析，共找到 {len(rows)} 行...")

        for index, row in enumerate(rows):
            # 获取该行的所有单元格 (td)
            cells = row.find_all('td')
            if len(cells) < 2:
                continue # 跳过表头或不完整的行

            # 第一列通常是活动/时段名称
            row_header_text = cells[0].get_text(strip=True)
            row_header_lower = row_header_text.lower()
            
            # 1. 匹配路线（Lake Louise 或 Moraine Lake）
            matches_route = any(route in row_header_lower for route in TARGET_ROUTES)
            # 2. 匹配目标时段 6am - 11am
            matches_time = any(slot in row_header_lower for slot in TIME_SLOTS)

            # 如果这一行符合我们的时间和路线要求
            if matches_route and matches_time:
                # print(f"  🔍 正在检查符合条件的行: {row_header_text}")
                
                # 3. 精细检查：遍历该行除第一列外的所有数据单元格
                row_has_available_cell = False
                for cell in cells[1:]:
                    cell_text = cell.get_text(strip=True)
                    cell_text_lower = cell_text.lower()
                    
                    # 检查该单元格是否包含售罄关键词
                    is_cell_unavailable = any(kw in cell_text_lower for kw in UNAVAILABLE_KEYWORDS)
                    
                    # 关键判断：如果单元格里没有售罄关键词，并且可能有‘可用’的标识
                    # 这里使用反向判断：只要不是明确售罄，就视为可能可用。
                    # 针对截图，如果单元格包含打勾符号 ✓ (通常是图片或特殊字符)，代码通常读不到符号，但能读到 'Available' 
                    # 或者，如果单元格完全为空，也可能代表有票（取决于网站实现），我们需要一种包容性的判断
                    
                    # 针对 Parks Canada 的常见实现，我们还可以检查单元格的 HTML 属性
                    # 例如，可用单元格可能有特定的 class (如 'available')
                    # 这里我们使用一种通用的判断方式：
                    # 1. 单元格文本里没有售罄字样
                    # 2. 并且，单元格文本不为空 OR 拥有特定的 HTML 标记（如 BeautifulSoup 找到子元素）
                    
                    if not is_cell_unavailable and (cell_text or cell.find()):
                        row_has_available_cell = True
                        break # 只要这行有一个单元格可用，就整行视为可用

                if row_has_available_cell:
                    available_slots.append(row_header_text)
        
        if available_slots:
            detail_msg = f"🎉 发现可用车位 ({REQUIRED_SEATS}张)：{' | '.join(available_slots)}"
            return True, detail_msg

        return False, detail_msg

    except Exception as e:
        return False, f"⚠️ 网络请求或解析异常: {e}"

if __name__ == "__main__":
    print(f"🔍 正在深入单元格监控 Lake Louise & Moraine Lake [{DATE_RANGE_STR} 6:00 AM - 11:00 AM]...")
    has_seats, info = check_seats_optimized()
    
    # 获取当前的 UTC 小时
    utc_now = datetime.datetime.utcnow()
    
    # 1. 🚨 情况一：一旦发现空位，立即触发【橙色抢票卡片】
    if has_seats:
        print(f"🎉【重要提醒】{info}")
        send_feishu_card(
            "🚨【双湖 Shuttle 车位提醒】发现可用车位！",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**目标路线**：Lake Louise & Moraine Lake",
                f"**目标时段**：6:00 AM - 11:00 AM",
                f"**需求人数**：{REQUIRED_SEATS} 人",
                f"**最新状态**：🎉 **{info}**",
                "**重要提示**：此提醒基于对表格单元格的精细扫描。请点击下方按钮立即前往网页确认具体日期并抢票！"
            ],
            BUS_URL,
            card_color="orange"
        )
    # 2. ☀️ 情况二：每日巡检日报
    elif utc_now.hour == 12:
        print(f"☀️ 发送每日巡检日报...")
        send_feishu_card(
            "☀️【每日巡检日报】双湖 Shuttle 车位监控运行中",
            [
                f"**目标日期范围**：{DATE_RANGE_STR}",
                f"**监控路线**：Lake Louise & Moraine Lake",
                f"**目标时段**：6:00 AM - 11:00 AM",
                f"**巡检状态**：精细化双线路监控正常运行中",
                f"**最新车位情况**：{info}"
            ],
            BUS_URL,
            card_color="blue"
        )
    else:
        print(f"ℹ️ 扫描正常: {info}（未触发表格推送）")
