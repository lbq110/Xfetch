#!/usr/bin/env python3
import asyncio
import sys
import json
sys.path.insert(0, '/Users/lubinquan/Desktop/study/Xfetch/twscrape')

from twscrape import API, AccountsPool
from twscrape.db import execute

DB_PATH = "/Users/lubinquan/Desktop/study/Xfetch/accounts.db"

RAW_COOKIES = "night_mode=2; auth_token=f08e72fae5ef76909dc0fb434d63d0a61ca1c19d; twid=u%3D2011190561584390144; ct0=03d05a8960d26b74cb2ebcd34560c8f006ee11fb83f1d29a37680ac0ff39fa8a02e4d3a315655e2cdb4f092ff00d941ea4bd0102b5a1050f0131b09ef0fa1e1fc08ba6f564803ae71ea8df1592ef4bc7; lang=en; guest_id=v1%3A176843672923485753; personalization_id=\"v1_KdAGLyS8I7NozmeqlmMo2Q==\""


def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key] = value
    return cookies


async def setup():
    pool = AccountsPool(DB_PATH)

    try:
        await pool.add_account(
            username="roger2862541",
            password="binbin110110",
            email="lubinquan110@gmail.com",
            email_password="binbin110110"
        )
    except:
        pass

    cookies = parse_cookies(RAW_COOKIES)
    cookies_json = json.dumps(cookies)
    headers_json = json.dumps({"x-csrf-token": cookies.get("ct0", "")})

    sql = """
        UPDATE accounts
        SET cookies = ?, headers = ?, active = 1, error_msg = NULL
        WHERE username = ?
    """
    await execute(DB_PATH, sql, [cookies_json, headers_json, "roger2862541"])


async def debug_raw():
    api = API(DB_PATH, debug=True)

    user = await api.user_by_login("roger2862541")
    print(f"用户 ID: {user.id}")

    print("\n获取原始 Lists 响应...")

    # 获取原始响应
    async for rep in api.user_lists_raw(user.id, limit=10):
        data = rep.json()

        # 保存到文件
        with open("/tmp/lists_debug.json", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"状态码: {rep.status_code}")
        print(f"响应已保存到 /tmp/lists_debug.json")

        # 打印部分响应内容
        print("\n响应结构:")
        print(json.dumps(list(data.keys()), indent=2))

        if "data" in data:
            print("\ndata 结构:")
            print(json.dumps(list(data["data"].keys()) if isinstance(data["data"], dict) else type(data["data"]).__name__, indent=2))

        if "errors" in data:
            print("\n错误信息:")
            print(json.dumps(data["errors"], indent=2))

        break


if __name__ == "__main__":
    asyncio.run(setup())
    asyncio.run(debug_raw())
