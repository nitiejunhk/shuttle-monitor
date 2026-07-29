import json
import os
import requests

# -------------------------------------------------------------------
# 1. 监控配置
# -------------------------------------------------------------------
START_DATE = "2026-07-29"
END_DATE = "2026-08-07"

# 接收提醒的 Webhook / 推送接口 (系统环境变量)
PUSH_WEBHOOK_URL = os.environ.get("PUSH_WEBHOOK_URL", "")


def send_notification(title, content):
    """触发推送通知"""
    print(f"\n🔔 【推送通知】{title}\n{content}\n")
    if PUSH_WEBHOOK_URL:
        try:
            requests.post(
                PUSH_WEBHOOK_URL, json={"title": title, "desp": content}, timeout=10
            )
        except Exception as e:
            print(f"推送发送失败: {e}")


def check_ticket_availability():
    # 真实 API 基础 URL (根据你提取的真实接口调整)
    base_url = "https://reservation.pc.gc.ca/api/availability/resourcedailyavailability"

    # 请求头（模拟标准浏览器，避开简单的防爬拦截）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://reservation.pc.gc.ca/",
    }

    # 提取出的真实查询参数
    params = {
        "cartUid": "ed4c6dc6-96b4-49e2-a971-36b8cb9736a4",
        "resourceId": "-2147476638",
        "bookingCategoryId": "9",
        "startDate": START_DATE,
        "endDate": END_DATE,
        "isReserving": "true",
        "equipmentCategoryId": "",
        "subEquipmentCategoryId": "",
        "boatLength": "0",
        "boatDraft": "0",
        "boatWidth": "0",
        "peopleCapacityCategoryCounts": '[{"capacityCategoryId":-32767,"subCapacityCategoryId":null,"count":1}]',
        "numEquipment": "0",
        "filterData": "[]",
        "groupHoldUid": "",
        "bookingUid": "cefea66e-d39a-4295-a9c7-1fec0e09bff1",
    }

    print(
        f"🔍 正在从 Parks Canada 真实接口查询 [{START_DATE} 至 {END_DATE}] 车位信息..."
    )

    try:
        response = requests.get(
            base_url, headers=headers, params=params, timeout=15
        )

        # ---------------------------------------------------------------
        # 打印 DEBUG 日志以便排查
        # ---------------------------------------------------------------
        print("\n================ DEBUG Raw Data 开始 ================")
        print(f"HTTP 状态码: {response.status_code}")

        try:
            data = response.json()
            # 格式化输出前 1000 个字符，防止日志过长
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            print(
                json_str[:1000] + ("\n... (后续截断)" if len(json_str) > 1000 else "")
            )
        except Exception:
            data = None
            print("返回内容非 JSON 格式：")
            print(response.text[:1000])
        print("================ DEBUG Raw Data 结束 ================\n")

        # ---------------------------------------------------------------
        # 2. 余票解析逻辑
        # ---------------------------------------------------------------
        found_tickets = []

        if isinstance(data, dict):
            # Parks Canada 接口返回的结构通常在 resourceDailyAvailabilities 或类似列表中
            availabilities = (
                data.get("resourceDailyAvailabilities")
                or data.get("availabilities")
                or []
            )

            for item in availabilities:
                date_str = item.get("date") or item.get("startDate")
                # 检查状态是否为可预订 (通常值为 0/Available/True)
                status = item.get("status")
                is_available = item.get("isAvailable") or status in [
                    0,
                    "Available",
                    "A",
                ]

                if is_available:
                    found_tickets.append(f"📅 日期: {date_str} | 状态: 有票/可预订")

        # 如果返回的是列表格式
        elif isinstance(data, list):
            for item in data:
                date_str = item.get("date")
                if item.get("isAvailable") or item.get("status") in [
                    0,
                    "Available",
                    "A",
                ]:
                    found_tickets.append(f"📅 日期: {date_str} | 状态: 有票/可预订")

        # ---------------------------------------------------------------
        # 3. 结果判断与推送
        # ---------------------------------------------------------------
        if found_tickets:
            msg_body = "\n".join(found_tickets)
            title = "🎉 刷到 Banff 班车票啦！"
            print(
                f"✅ 成功找到可用车票：\n{msg_body}"
            )
            send_notification(title, msg_body)
        else:
            print(
                f"ℹ️ 扫描完成：[{START_DATE} 至 {END_DATE}] 指定范围内暂无可用车票。"
            )

    except Exception as e:
        print(f"❌ 运行脚本时发生异常: {e}")


if __name__ == "__main__":
    check_ticket_availability()
