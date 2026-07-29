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

# Parks Canada 两个景点的内部 resourceId (已为您配置好)
RESOURCES = {
    "Moraine Lake (梦莲湖)": "-2147476637",
    "Lake Louise (露易丝湖)": "-2147476638",
}


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

    found_tickets = []
    start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")

    # 循环遍历两条线路
    for res_name, res_id in RESOURCES.items():
        params = {
            "cartUid": "ed4c6dc6-96b4-49e2-a971-36b8cb9736a4",
            "resourceId": res_id,
            "bookingCategoryId": "9",
            "startDate": START_DATE_STR,
            "endDate": END_DATE_STR,
            "isReserving": "true",
            "peopleCapacityCategoryCounts": '[{"capacityCategoryId":-32767,"subCapacityCategoryId":null,"count":1}]',
            "bookingUid": "cefea66e-d39a-4295-a9c7-1fec0e09bff1",
        }

        try:
            response = requests.get(
                base_url, headers=headers, params=params, timeout=15
            )
            if response.status_code != 200:
                continue

            data = response.json()
            if isinstance(data, list):
                for index, item in enumerate(data):
                    current_date = (
                        start_date + timedelta(days=index)
                    ).strftime("%Y-%m-%d")
                    avail_status = item.get("availability")

                    # 只要 availability 不等于 1，说明该线路该日期有票！
                    if avail_status is not None and avail_status != 1:
                        found_tickets.append(
                            f"📅 日期: {current_date} | 📍 线路: {res_name} | 状态码: {avail_status} (有票)"
                        )

        except Exception as e:
            print(f"❌ 请求 {res_name} 时发生异常: {e}")

    # ---------------------------------------------------------------
    # 2. 结果汇总与提醒
    # ---------------------------------------------------------------
    if found_tickets:
        msg_body = "\n".join(found_tickets)
        title = "🎉 刷到 Banff 班车常规票啦！"
        print(f"✅ 判定成功！抓取到可用车票：\n{msg_body}")
        send_notification(title, msg_body)
    else:
        print(
            f"ℹ️ 扫描完成：[{START_DATE_STR} 至 {END_DATE_STR}] 梦莲湖与露易丝湖两条线路常规车票均无票。"
        )


if __name__ == "__main__":
    check_ticket_availability()
