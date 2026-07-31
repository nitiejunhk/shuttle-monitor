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


def is_time_in_range(slot_time_str: str) -> bool:
    """检查时间字符串是否在 06:00 - 11:00 范围内，若解析失败则默认不过滤"""
    if not slot_time_str:
        return True
    formats = ["%H:%M", "%I:%M %p", "%H:%M:%S", "%g:%i%a"]
    for fmt in formats:
        try:
            t = datetime.strptime(slot_time_str.strip(), fmt).time()
            return TIME_START <= t <= TIME_END
        except ValueError:
            continue
    return True


def fetch_availability() -> list:
    """拉取 Banff Shuttle 预订系统数据"""
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
        
        # 打印调试日志
        if isinstance(data, dict):
            logging.info(f"🔍 API 返回数据 Key: {list(data.keys())}")
            logging.info(f"🔍 API 样例数据: {str(data)[:300]}")
        
        # 兼容多种数据层级结构
        resources = []
        if isinstance(data, dict):
            resources = data.get("resourceAvailabilities") or data.get("gridData") or data.get("availabilities") or [data]
        elif isinstance(data, list):
            resources = data

        # 解析数据
        if isinstance(resources, dict):
            resources = list(resources.values())

        for res in resources:
            if isinstance(res, list):
                day_list = res
            elif isinstance(res, dict):
                day_list = res.get("days") or res.get("availabilities") or [res]
            else:
                continue

            for day in day_list:
                if not isinstance(day, dict):
                    continue
                date_str = day.get("date") or day.get("d") or TARGET_START_DATE
                
                # 时间切片/班次列表
                slices = day.get("slices") or day.get("availabilities") or day.get("slots") or [day]
                for s in slices:
                    if not isinstance(s, dict):
                        continue
                    
                    status = s.get("status") or s.get("available") or s.get("a")
                    slot_time = s.get("startTime") or s.get("time") or s.get("t") or ""
                    
                    # 状态判断 (1 代表有票，True 代表有票)
                    is_available = (status == 1 or status is True or str(status).lower() in ["available", "1", "true"])
                    
                    if is_available and is_time_in_range(str(slot_time)):
                        info_name = s.get("name") or s.get("resourceName") or "Banff Shuttle 班车"
                        logging.info(f"🎯 成功识别到余票！日期: {date_str}, 时间: {slot_time}, 名称: {info_name}")
                        available_slots.append({
                            "date": str(date_str),
                            "time": str(slot_time) if slot_time else "全天/具体班次",
                            "info": str(info_name)
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
        logging.info("ℹ️ 暂未发现目标时段余票，按规则静默，不发通知。")

    logging.info("=== 任务正常结束 ===")


if __name__ == "__main__":
    main()
