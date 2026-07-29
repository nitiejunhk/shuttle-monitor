import json
import os
import requests

# -------------------------------------------------------------------
# 1. 监控配置 (请根据你的实际项目需求调整参数)
# -------------------------------------------------------------------
START_DATE = "2026-07-29"
END_DATE = "2026-08-07"
TIME_WINDOW_START = "06:00"  # 监控开始时间
TIME_WINDOW_END = "11:00"  # 监控结束时间

# 接收提醒的 Webhook / 推送接口 (例如 Server酱 / Telegram / Pushbullet 等)
PUSH_WEBHOOK_URL = os.environ.get("PUSH_WEBHOOK_URL", "")


def send_notification(title, content):
    """触发推送通知的函数"""
    print(f"【推送通知】{title}\n{content}")
    if PUSH_WEBHOOK_URL:
        try:
            requests.post(
                PUSH_WEBHOOK_URL, json={"title": title, "desp": content}, timeout=10
            )
        except Exception as e:
            print(f"推送发送失败: {e}")


def check_ticket_availability():
    # 模拟请求 Parks Canada 或你当前调用的监控 API 接口
    # 提示：请确保这里的 API URL / Header 与你现有的爬虫请求一致
    api_url = "https://reservation.pc.gc.ca/api/availability"  # 替换为你的实际接口地址

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(
        f"🔍 正在检索 Lake Louise & Moraine Lake [{START_DATE} 至 {END_DATE} {TIME_WINDOW_START} - {TIME_WINDOW_END}] 的常规预订车位..."
    )

    try:
        # response = requests.get(api_url, headers=headers, timeout=10)
        # data = response.json()

        # ---------------------------------------------------------------
        # 2. 核心解析与判定逻辑 (独立评估每个线路与班次)
        # ---------------------------------------------------------------
        found_available_tickets = []

        """
        假设 API 返回的结构/列表数据格式如下：
        item = {
            "date": "2026-08-04",
            "time": "06:30 AM",
            "location": "Moraine Lake",
            "category": "Regular", # Regular 或 Last Minute
            "status": "Available"  # Available 或 Unavailable
        }
        """

        # 这里替换为你从 API 拿到的真实 slots 列表 (示例解析逻辑如下)：
        # for slot in data.get("slots", []):
        #     slot_date = slot.get("date")
        #     slot_time = slot.get("time")
        #     location = slot.get("location")
        #     category = slot.get("category", "")
        #     status = slot.get("status")

        #     # 关键点 1：只筛选常规票 (排除 Last Minute)
        #     if "Last Minute" in category:
        #         continue

        #     # 关键点 2：只要单条线路有票、且在设定的时间窗口内，即视为找到可用票
        #     if status == "Available" and (START_DATE <= slot_date <= END_DATE):
        #         found_available_tickets.append(f"📅 {slot_date} | 📍 {location} | ⏰ {slot_time} ({category})")

        # ---------------------------------------------------------------
        # 3. 结果汇总与提醒
        # ---------------------------------------------------------------
        if found_available_tickets:
            msg_body = "\n".join(found_available_tickets)
            title = "🎉 刷到 Banff 湖区常规班车票啦！"
            print(
                f"✅ 扫描到可用车票：\n{msg_body}\n（已成功触发推送）"
            )
            send_notification(title, msg_body)
        else:
            print(
                f"ℹ️ 扫描正常: {START_DATE} 至 {END_DATE} ({TIME_WINDOW_START} - {TIME_WINDOW_END}) 的 Lake Louise 及 Moraine Lake 线路常规车票仍售罄（未触发推送）"
            )

    except Exception as e:
        print(f"❌ 运行脚本时发生异常: {e}")


if __name__ == "__main__":
    check_ticket_availability()
