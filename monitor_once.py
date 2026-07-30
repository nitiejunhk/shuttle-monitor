import base64
import hashlib
import hmac
import os
import time
import requests


def send_feishu_notification(title, message, webhook_url=None, secret=None):
    """发送飞书自定义机器人消息（支持卡片/富文本/纯文本，内置签名与错误排查）"""
    # 优先从环境变量读取配置
    url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
    secret_key = secret or os.getenv("FEISHU_SECRET")

    if not url:
        print("❌ [推送失败] 未配置 FEISHU_WEBHOOK_URL 环境变量！")
        return False

    # 1. 构造基础 Payload (富文本/卡片样式，视觉更清晰)
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [
                        [{"tag": "text", "text": message}],
                        [
                            {
                                "tag": "a",
                                "text": "👉 点击立即前往官网抢票",
                                "href": "https://reservation.pc.gc.ca/",
                            }
                        ],
                    ],
                }
            }
        },
    }

    # 2. 如果飞书后台开启了“签名校验”，自动计算签名
    if secret_key:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret_key}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")

        payload["timestamp"] = timestamp
        payload["sign"] = sign

    # 3. 发送请求并打印详细响应日志
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        res_data = response.json()

        # 飞书 API 返回 code 为 0 代表成功
        if res_data.get("code") == 0:
            print("✅ [飞书推送成功] 消息已成功送达！")
            return True
        else:
            print(f"❌ [飞书拒绝接收] 状态码: {res_data.get('code')}")
            print(f"👉 错误原因提示: {res_data.get('msg')}")
            return False

    except Exception as e:
        print(f"💥 [网络请求异常] 发送飞书消息时抛出异常: {e}")
        return False


# ==================== 测试调用示例 ====================
if __name__ == "__main__":
    # 测试运行（如果你在 GitHub Actions 里运行，会在日志里直接打印排查结果）
    test_title = "🚨 Banff 车票常规票放票啦！"
    test_msg = "📅 日期: 2026-07-30 | 📍 线路: Moraine Lake (梦莲湖) | 状态: 有票"

    send_feishu_notification(test_title, test_msg)
