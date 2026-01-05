"""
feishu_upload.py
最小可跑通：把 OCR 的 raw_text 写入飞书多维表格一条新记录

你需要填写：
- APP_ID
- APP_SECRET
- BASE_APP_TOKEN  (Base ID / app_token)
- TABLE_ID        (tblxxx)
- RAW_TEXT_FIELD  (你表里“原始OCR文本”字段的名字，必须完全一致)
"""

import requests
import os
from dotenv import load_dotenv
load_dotenv()


# ===== 1) 你只需要改这里 =====
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
BASE_APP_TOKEN = os.getenv("FEISHU_BASE_APP_TOKEN")  # Base ID / app_token
TABLE_ID = os.getenv("FEISHU_TABLE_ID")         # Table ID
RAW_TEXT_FIELD = os.getenv("FEISHU_RAW_TEXT_FIELD")          # 你的字段名（完全一致！）


def get_tenant_access_token() -> str:
    """
    向飞书获取 tenant_access_token
    这个 token 相当于“临时通行证”，拿到后才能调用表格 API
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}

    resp = requests.post(url, json=payload, timeout=15)
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败：{data}")

    return data["tenant_access_token"]


def create_record(raw_text: str) -> dict:
    """
    在多维表格里新增一条记录，只写入 raw_text 字段
    写进去后，你的 AI 字段会自动开始抽取/生成结构化字段
    """
    token = get_tenant_access_token()
    print("✅ token =", token)

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # fields 的 key 必须是你表里的字段名（或字段 ID）
    payload = {
        "fields": {
            RAW_TEXT_FIELD: raw_text
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"写入记录失败：{data}")

    return data


if __name__ == "__main__":
    # 你可以先用一个很短的测试文本，确认链路跑通
    test_text = "灯带 3.4 米\n价格 3.8 元\n你要不要"

    result = create_record(test_text)
    print("✅ 写入成功！返回：")
    print(result)