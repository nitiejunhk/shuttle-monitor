
from datetime import datetime, timedelta
import json
import os
import requests

# -------------------------------------------------------------------
# 1. 监控配置
# -------------------------------------------------------------------
START_DATE_STR = "2026-07-29"
END_DATE_STR = "2026-08-07"

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
    base_url = "https://reservation.pc.gc.ca/api/availability/resourcedailyavailability"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://reservation.pc.gc.ca/",
    }

    params = {
        "cartUid": "ed4c6dc6-96b4-49e2-a971-36b8cb9736a4",
        "resourceId": "-2147476638",
        "bookingCategoryId": "9",
        "startDate": START_DATE_STR,
        "endDate": END_DATE_STR,
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

    print(f"🔍 正在从真实接口查询 [{START_DATE_STR} 至 {END_DATE_STR}] 车位信息...")

    try:
        response = requests.get(
            base_url, headers=headers, params=params, timeout=15
        )

        if response.status_code != 200:
            print(f"❌ 请求失败，HTTP 状态码: {response.status_code}")
            return

        data = response.json()
        found_tickets = []

        start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")

        # ---------------------------------------------------------------
        # 2. 核心解析：根据数组位置映射日期，并依据 availability 判断
        # ---------------------------------------------------------------
        if isinstance(data, list):
            for index, item in enumerate(data):
                # 对应推算日期
                current_date = (start_date + timedelta(days=index)).strftime(
                    "%Y-%m-%d"
                )
                avail_status = item.get("availability")

                # 💡 核心逻辑：1 表示售罄，只要不等于 1（例如 0 或 2 等）即说明有票！
                if avail_status is not None and avail_status != 1:
                    found_tickets.append(
                        f"📅 日期: {current_date} | 状态码: {avail_status} (有票/可预订)"
                    )

        # ---------------------------------------------------------------
        # 3. 推送提醒
        # ---------------------------------------------------------------
        if found_tickets:
            msg_body = "\n".join(found_tickets)
            title = "🎉 刷到 Banff 班车常规票啦！"
            print(f"✅ 判定成功！抓取到可用车票：\n{msg_body}")
            send_notification(title, msg_body)
        else:
            print(
                f"ℹ️ 扫描正常：[{START_DATE_STR} 至 {END_DATE_STR}] 范围内常规车票依然全满（未触发推送）。"
            )

    except Exception as e:
        print(f"❌ 脚本运行异常: {e}")


if __name__ == "__main__":
    check_ticket_availability()
