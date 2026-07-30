import os
import sys
import json
import logging
from datetime import datetime, time
import requests

# ---------------------------------------------------------------------------
# 配置项
# ---------------------------------------------------------------------------
# 飞书 Custom Bot Webhook 地址 (请替换为你自己的 Webhook)
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN")

# 监控目标时间范围 (月-日)
DATE_START = "08-01"
DATE_END = "08-26"

# 监控目标时段 (06:00 - 11:00)
TIME_START = time(6, 0)
TIME_END = time(11, 0)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

# 监控目标页面/API URL（请根据实际调用的 API endpoint 填入）
PARKS_CANADA_API_URL = "https://res.pc.gc.ca/api/availability" 

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[sys.stdout.stream if hasattr(sys.stdout, 'stream') else logging.StreamHandler(sys.stdout)]
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def send_feishu_message(title: str, content: str):
    """通过飞书 Webhook 发送卡片消息"""
    if "YOUR_WEBHOOK_TOKEN" in FEISHU_WEBHOOK_URL:
        logging.warning("飞书 Webhook 地址未设置，跳过推送！")
        return

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [[{"tag": "text", "text": content}]]
                }
            }
        }
    }
    
    try:
        res = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
        logging.info("飞书消息推送成功。")
    except Exception as e:
        logging.error(f"飞书消息推送失败: {e}")


def is_in_target_window(slot_time_str: str, slot_date_str: str) -> bool:
    """判断槽位时间是否符合：8月1日-8月26日 06:00-11:00"""
    try:
        # 校验日期范围 (格式 MM-DD)
        if not (DATE_START <= slot_date_str <= DATE_END):
            return False

        # 校验时间范围 (格式 HH:MM)
        t = datetime.strptime(slot_time_str, "%H:%M").time()
        return TIME_START <= t <= TIME_END
    except ValueError:
        return False


def fetch_availability() -> list:
    """
    发送 API 请求获取 Banff Shuttle 余票数据。
    返回解析后的符合条件的余票列表：[{"date": "08-10", "time": "07:15", "slots": 2, "location": "Lake Louise"}, ...]
    """
    available_slots = []
    
    try:
        # NOTE: 此处需填入 Banff 官方预订系统的查询参数（如 date range, location id）
        response = requests.get(PARKS_CANADA_API_URL, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logging.error(f"请求失败，状态码: {response.status_code}")
            return available_slots

        data = response.json()

        # 模拟/通用 JSON 结构解析逻辑（根据实际 API 调整）
        for item in data.get("slots", []):
            slot_date = item.get("date")  # e.g. "08-05"
            slot_time = item.get("time")  # e.g. "07:30"
            count = item.get("available_count", 0)
            location = item.get("location_name", "Lake Louise / Moraine Lake Shuttle")

            if count > 0 and is_in_target_window(slot_time, slot_date):
                available_slots.append({
                    "date": slot_date,
                    "time": slot_time,
                    "slots": count,
                    "location": location
                })

    except Exception as e:
        logging.error(f"查询余票时出错: {e}")
        
    return available_slots


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    logging.info(f"=== 开始监控 Banff Shuttle (当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}) ===")

    # 1. 检查是否到达每日 08:00 心跳推送时间
    is_daily_report_time = (current_time_str == "08:00")

    # 2. 获取余票
    found_slots = fetch_availability()

    # 3. 逻辑判断与推送
    if found_slots:
        # 发现有票，立刻推送警报
        title = "🚨 [Banff Shuttle] 发现可用车票！"
        details = "\n".join([f"• {s['date']} {s['time']} - {s['location']} (余票: {s['slots']})" for s in found_slots])
        content = f"检测到 8月1日-26日 (06:00-11:00) 目标时段有票：\n\n{details}\n\n请尽快前往官网抢票！"
        
        logging.info("发现目标余票，触发即时推送。")
        send_feishu_message(title, content)

    elif is_daily_report_time:
        # 刚好处于早上 08:00 且没票，发送每日例行汇报
        title = "☀️ [Banff Shuttle] 每日运行状态汇报"
        content = f"汇报时间: {now.strftime('%Y-%m-%d 08:00')}\n\n监控系统运行正常。\n目前 8月1日-26日 (06:00-11:00) 暂无可用余票。"
        
        logging.info("到达 08:00 汇报节点，触发每日状态推送。")
        send_feishu_message(title, content)

    else:
        # 既没有余票，也不是 08:00 点，静默退出
        logging.info("未发现可用余票，无需推送。")

    logging.info("=== 本次监控完成 ===")


if __name__ == "__main__":
    main()
