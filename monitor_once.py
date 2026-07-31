import os
import sys
import logging
from datetime import datetime, time
import requests

# ---------------------------------------------------------------------------
# 配置项
# ---------------------------------------------------------------------------
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")

# 监控目标日期范围 (2026年 8月1日 - 8月26日)
TARGET_START_DATE = datetime.now().strftime("%Y-%m-%d")
TARGET_END_DATE = "2026-08-26"

# 监控目标时段 (06:00 - 11:00)
TIME_START = time(6, 0)
TIME_END = time(11, 0)

# 更新后的 Parks Canada 查询接口
PARKS_CANADA_API = "https://reservation.pc.gc.ca/api/availability/map"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://reservation.pc.gc.ca/banff/lakelouise",
    "Origin": "https://reservation.pc.gc.ca"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ---------------------------------------------------------------------------
# 功能函数
# ---------------------------------------------------------------------------
def send_feishu_message(title: str, content: str):
    """通过飞书 Webhook 发送通知"""
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
    
    # Banff Shuttle 常用资源 Map ID
    params = {
        "mapId": -2147483348,
        "bookingCategoryId": 1,
        "startDate": "2026-07-31",
        "endDate": TARGET_END_DATE,
        "isDayUse": "true"
    }

    try:
        response = requests.get(PARKS_CANADA_API, headers=HEADERS, params=params, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"接口响应异常，HTTP 状态码: {response.status_code}")
            return available_slots

        data = response.json()
        # 兼容不同的 API 格式解析
        resources = data.get("resourceAvailabilities") or data.get("gridData", {})
        
        if isinstance(resources, dict):
            for res_id, days in resources.items():
                if not isinstance(days, list):
                    continue
                for day in days:
                    date_str = day.get("date")
                    if not date_str or not (TARGET_START_DATE <= date_str <= TARGET_END_DATE):
                        continue

                    slices = day.get("slices", []) or day.get("availabilities", [])
                    for s in slices:
                        slot_time = s.get("startTime", "") or s.get("time", "")
                        status = s.get("status", 0) or s.get("available", False)
                        
                        if (status == 1 or status is True) and is_time_in_range(str(slot_time)):
                            available_slots.append({
                                "date": date_str,
                                "time": str(slot_time),
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

    is_daily_report_time = (current_time_str == "08:00")
    found_slots = fetch_availability()

    if found_slots:
        title = "🚨 [Banff Shuttle] 刷到目标车票！"
        lines = [f"• {item['date']} 【{item['time']}】 - {item['info']}" for item in found_slots]
        content = "检测到 8月1日-26日 (06:00-11:00) 范围内有票：\n\n" + "\n".join(lines) + "\n\n请速前往官网抢票：https://reservation.pc.gc.ca/"
        
        logging.info("发现目标余票，准备发送飞书通知...")
        send_feishu_message(title, content)

    elif is_daily_report_time:
        title = "☀️ [Banff Shuttle] 每日运行状态汇报"
        content = f"汇报时间: {now.strftime('%Y-%m-%d 08:00')}\n\n监控系统正常工作。\n目前 8月1日-26日 (06:00-11:00) 暂无放票。"
        
        logging.info("触发 08:00 心跳推送...")
        send_feishu_message(title, content)

    else:
        logging.info("暂未发现目标时段余票，按规则静默，不发通知。")

    logging.info("=== 任务正常结束 ===")


if __name__ == "__main__":
    main()
