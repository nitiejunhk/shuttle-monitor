import os
import sys
import logging
from datetime import datetime, time
import requests

# ---------------------------------------------------------------------------
# 配置项
# ---------------------------------------------------------------------------
# 从 GitHub Secrets 读取飞书 Webhook
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")

# 监控目标日期范围 (2026年 8月1日 - 8月26日)
TARGET_START_DATE = "2026-08-01"
TARGET_END_DATE = "2026-08-26"

# 监控目标时段 (06:00 - 11:00)
TIME_START = time(6, 0)
TIME_END = time(11, 0)

# Parks Canada ReserveAmerica 查询接口 (Lake Louise / Moraine Lake Shuttle Map)
PARKS_CANADA_API = "https://reservation.pc.gc.ca/api/availability/grid"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://reservation.pc.gc.ca/",
    "Origin": "https://reservation.pc.gc.ca"
}

# 日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


# ---------------------------------------------------------------------------
# 功能函数
# ---------------------------------------------------------------------------
def send_feishu_message(title: str, content: str):
    """通过飞书 Webhook 发送卡片通知"""
    if not FEISHU_WEBHOOK_URL:
        logging.warning("⚠️ 未检测到 FEISHU_WEBHOOK_URL 环境变量，跳过推送！")
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
        logging.info("✅ 飞书消息推送成功！")
    except Exception as e:
        logging.error(f"❌ 飞书推送失败: {e}")


def is_time_in_range(slot_time_str: str) -> bool:
    """检查时间字符串是否在 06:00 - 11:00 范围内"""
    formats = ["%H:%M", "%I:%M %p", "%H:%M:%S"]
    for fmt in formats:
        try:
            t = datetime.strptime(slot_time_str.strip(), fmt).time()
            return TIME_START <= t <= TIME_END
        except ValueError:
            continue
    return False


def fetch_availability() -> list:
    """拉取 Banff Shuttle 预订系统数据"""
    available_slots = []
    
    # Banff Shuttle 对应 Map 参数
    params = {
        "mapId": -2147483348,
        "bookingCategoryId": 1,
        "startDate": TARGET_START_DATE,
        "endDate": TARGET_END_DATE,
        "getDailyAvailability": "true"
    }

    try:
        response = requests.get(PARKS_CANADA_API, headers=HEADERS, params=params, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"接口响应异常，HTTP 状态码: {response.status_code}")
            return available_slots

        data = response.json()
        resources = data.get("resourceAvailabilities", {})
        
        for res_id, days in resources.items():
            for day in days:
                date_str = day.get("date") # 格式 YYYY-MM-DD
                
                # 过滤 8月1日 - 8月26日
                if not date_str or not (TARGET_START_DATE <= date_str <= TARGET_END_DATE):
                    continue

                slices = day.get("slices", [])
                for s in slices:
                    slot_time = s.get("startTime", "")
                    status = s.get("status", 0)  # 1 代表可用
                    
                    if status == 1 and is_time_in_range(slot_time):
                        available_slots.append({
                            "date": date_str,
                            "time": slot_time,
                            "info": "路易斯湖 / 梦莲湖 Shuttle 班车"
                        })

    except Exception as e:
        logging.error(f"查询 API 失败: {e}")
        
    return available_slots


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
def main():
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    logging.info(f"=== 开启 Banff Shuttle 监控逻辑 (当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}) ===")

    # 每天早上 08:00 发送一次心跳汇报
    is_daily_report_time = (current_time_str == "08:00")

    # 执行查票
    found_slots = fetch_availability()

    if found_slots:
        # 有票：无论何时，立即触发警报推送
        title = "🚨 [Banff Shuttle] 刷到目标车票！"
        lines = [f"• {item['date']} 【{item['time']}】 - {item['info']}" for item in found_slots]
        content = "检测到 8月1日-26日 (06:00-11:00) 范围内有票：\n\n" + "\n".join(lines) + "\n\n请速前往官网抢票：https://reservation.pc.gc.ca/"
        
        logging.info("发现目标余票，准备发送飞书通知...")
        send_feishu_message(title, content)

    elif is_daily_report_time:
        # 无票但刚好是早晨 08:00：发送状态汇报
        title = "☀️ [Banff Shuttle] 每日运行状态汇报"
        content = f"汇报时间: {now.strftime('%Y-%m-%d 08:00')}\n\n监控系统正常工作。\n目前 8月1日-26日 (06:00-11:00) 暂无放票。"
        
        logging.info("触发 08:00 心跳推送...")
        send_feishu_message(title, content)

    else:
        # 无票且不是 08:00：静默退出
        logging.info("暂未发现目标时段余票，按规则静默，不发通知。")

    logging.info("=== 任务正常结束 ===")


if __name__ == "__main__":
    main()
