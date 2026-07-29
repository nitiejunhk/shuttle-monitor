import json
import os
import requests

# -------------------------------------------------------------------
# 1. 监控配置
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
    # 🚨 请注意：如果你们团队有真实的 Parks Canada 接口 URL，请替换掉下面的伪地址
    api_url = "https://reservation.pc.gc.ca/api/availability"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(
        f"🔍 正在检索 Lake Louise & Moraine Lake [{START_DATE} 至 {END_DATE} {TIME_WINDOW_START} - {TIME_WINDOW_END}] 的常规预订车位..."
    )

    try:
        # 1. 发起真实请求 (取消了注释)
        response = requests.get(api_url, headers=headers, timeout=15)

        # ---------------------------------------------------------------
        # 🚨 DEBUG 打印：查看接口实际返回了什么
        # ---------------------------------------------------------------
        print("\n================ DEBUG Raw Data 开始 ================")
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            data = {}
            print("返回内容非标准 JSON：")
            print(response.text[:2000])
        print("================ DEBUG Raw Data 结束 ================\n")

        # ---------------------------------------------------------------
        # 2. 核心解析与判定逻辑
        # ---------------------------------------------------------------
        found_available_tickets = []

        # 遍历 API 返回的 slots 数据 (取消了注释)
        slots = data.get("slots", []) if isinstance(data, dict) else []

        for slot in slots:
            slot_date = str(slot.get("date", ""))
            slot_time = str(slot.get("time", ""))
            location = str(slot.get("location", ""))
            category = str(slot.get("category", "Regular"))
            status = str(slot.get("status", "")).lower()

            # 关键点 1：只筛选常规票 (排除 Last Minute)
            if "last minute" in category.lower():
                continue

            # 关键点 2：只要单条线路有票、且在设定的日期窗口内，即视为找到可用票
            is_available = status in ["available", "a", "ok"] or slot.get(
                "available"
            ) is True
            if is_available and (START_DATE <= slot_date <= END_DATE):
                found_available_tickets.append(
                    f"📅 {slot_date} | 📍 {location} | ⏰ {slot_time} ({category})"
                )

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
