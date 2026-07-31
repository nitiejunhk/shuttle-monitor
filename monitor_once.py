import os
import sys
import logging
from datetime import datetime, time
import requests

# ---------------------------------------------------------------------------
# 配置项
# ---------------------------------------------------------------------------
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")

# 监控目标日期范围
TARGET_START_DATE = "2026-07-31"
TARGET_END_DATE = "2026-08-26"

# 监控目标时段 (06:00 - 11:00)
TIME_START = time(6, 0)
TIME_END = time(11, 0)

# Parks Canada 查询接口
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


def is_time_valid_and_in_range(date_str: str, slot_time_str: str) -> bool:
    """
    智能解析时间：
    1. 过滤已过期的班次（例如今天10点跑脚本，自动跳过当天6:30的票）
    2. 检查是否在 06:00 - 11:00 范围内
    """
    if not slot_time_str or slot_time_str.strip() == "":
        return True
        
    raw_str = slot_time_str.lower().strip()
    if "-" in raw_str:
        raw_str = raw_str.split("-")[0].strip()
        
    formats = ["%I:%M%p", "%I%p", "%I:%M %p", "%H:%M", "%H:%M:%S"]
    parsed_time = None
    
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(raw_str, fmt).time()
            break
        except ValueError:
            continue

    # 如果解析出了具体时间
    if parsed_time:
        # 1. 检查时段过滤 (06:00 - 11:00)
        if not (TIME_START <= parsed_time <= TIME_END):
            return False
            
        # 2. 检查过期过滤（如果是今天，且班车时间早于现在，过滤掉）
        today_str = datetime.now().strftime("%Y-%m-%d")
        if date_str == today_str:
            now_time = datetime.now().time()
            if parsed_time < now_time:
                logging.info(f"⏳ 跳过当天已过期的班次: {slot_time_str} (当前时间: {now_time.strftime('%H:%M')})")
                return False

    return True


def fetch_availability() -> list:
    """拉取 Banff Shuttle 预订系统数据并精准解析"""
    available_slots = []
    
    params = {
        "mapId": -2147483348,
        "bookingCategoryId": 1,
        "startDate": TARGET_START_DATE,
        "endDate": TARGET_END_DATE,
        "isDayUse": "true"
    }

    try:
        response = requests.get(PARKS_CANADA_API, headers=HEADERS, params=params, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"❌ 接口响应异常，HTTP 状态码: {response.status_code}")
            return available_slots

        data = response.json()
        res_avail = data.get("resourceAvailabilities", {})

        for res_id, slots in res_avail.items():
            if not isinstance(slots, list):
                continue
                
            for slot in slots:
                if not isinstance(slot, dict):
                    continue
                
                avail_status = slot.get("availability")
                quota = slot.get("remainingQuota")
                date_str = slot.get("date") or TARGET_START_DATE
                slot_time = slot.get("startTime") or slot.get("time") or slot.get("name") or slot.get("resourceName") or ""
                
                # 状态不是 5 (售罄) 即代表有余票
                is_available = (avail_status != 5 or (quota is not None and quota > 0))
                
                if is_available and is_time_valid_and_in_range(str(date_str), str(slot_time)):
                    res_name = slot.get("resourceName") or f"资源ID {res_id}"
                    logging.info(f"🎯 识别到未来有效余票！日期: {date_str}, 时间: {slot_time}")
                    available_slots.append({
                        "date": str(date_str),
                        "time": str(slot_time) if slot_time else "早间时段",
                        "info": f"Banff Shuttle ({res_name})"
                    })

    except Exception as e:
        logging.error(f"❌ 查询 API 出现异常: {e}")
        
    return available_slots


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
def main():
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    logging.info(f"=== 开启 Banff Shuttle 监控逻辑 (当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}) ===")

    found_slots = fetch_availability()

    if found_slots:
        title = "🚨 [Banff Shuttle] 刷到目标车票！"
        lines = [f"• {item['date']} 【{item['time']}】 - {item['info']}" for item in found_slots]
        content = "检测到目标日期范围内有票：\n\n" + "\n".join(lines) + "\n\n请速前往官网抢票：https://reservation.pc.gc.ca/"
        
        logging.info("📢 发现目标余票，准备发送飞书通知...")
        send_feishu_message(title, content)

    elif current_time_str == "08:00":
        title = "☀️ [Banff Shuttle] 每日运行状态汇报"
        content = f"汇报时间: {now.strftime('%Y-%m-%d 08:00')}\n\n监控系统正常工作。\n目前暂无目标班车余票。"
        
        logging.info("⏰ 触发 08:00 心跳推送...")
        send_feishu_message(title, content)

    else:
        logging.info("ℹ️ 暂未发现目标余票，按规则静默，不发通知。")

    logging.info("=== 任务正常结束 ===")


if __name__ == "__main__":
    main()
