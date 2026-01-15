#!/usr/bin/env python3
import asyncio
import sys
import json
sys.path.insert(0, '/Users/lubinquan/Desktop/study/Xfetch/twscrape')

from twscrape import API, AccountsPool

DB_PATH = "/Users/lubinquan/Desktop/study/Xfetch/accounts.db"

# 用户提供的 cookies (包含 auth_token)
RAW_COOKIES = "night_mode=2; auth_token=f08e72fae5ef76909dc0fb434d63d0a61ca1c19d; twid=u%3D2011190561584390144; ct0=03d05a8960d26b74cb2ebcd34560c8f006ee11fb83f1d29a37680ac0ff39fa8a02e4d3a315655e2cdb4f092ff00d941ea4bd0102b5a1050f0131b09ef0fa1e1fc08ba6f564803ae71ea8df1592ef4bc7; lang=en; guest_id=v1%3A176843672923485753; personalization_id=\"v1_KdAGLyS8I7NozmeqlmMo2Q==\""


def parse_cookies(cookie_str: str) -> dict:
    """解析 cookie 字符串为字典"""
    cookies = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key] = value
    return cookies


async def setup_account_with_cookies():
    """使用 cookies 设置账户"""
    pool = AccountsPool(DB_PATH)

    # 先添加账户（必须先有记录）
    print("创建账户记录...")
    await pool.add_account(
        username="roger2862541",
        password="binbin110110",
        email="lubinquan110@gmail.com",
        email_password="binbin110110"
    )

    # 解析 cookies
    cookies = parse_cookies(RAW_COOKIES)
    print(f"\n解析到的关键 cookies:")
    print(f"  auth_token: {cookies.get('auth_token', 'N/A')}")
    print(f"  ct0: {cookies.get('ct0', 'N/A')[:50]}...")
    print(f"  twid: {cookies.get('twid', 'N/A')}")

    # 直接通过 SQL 更新 cookies 和激活状态
    from twscrape.db import execute

    cookies_json = json.dumps(cookies)
    headers_json = json.dumps({
        "x-csrf-token": cookies.get("ct0", "")
    })

    sql = """
        UPDATE accounts
        SET cookies = ?, headers = ?, active = 1, error_msg = NULL
        WHERE username = ?
    """
    await execute(DB_PATH, sql, [cookies_json, headers_json, "roger2862541"])

    # 验证
    stats = await pool.stats()
    print(f"\n账户状态: {stats}")


async def scrape_lists():
    """抓取 Lists"""
    api = API(DB_PATH, debug=True)

    print("\n" + "="*60)
    print("获取用户 roger2862541 的信息")
    print("="*60)

    user = await api.user_by_login("roger2862541")
    if not user:
        print("无法获取用户信息")
        return

    print(f"用户 ID: {user.id}")
    print(f"用户名: @{user.username}")
    print(f"显示名: {user.displayname}")

    print("\n" + "="*60)
    print("获取用户的 Lists")
    print("="*60)

    count = 0
    async for twitter_list in api.user_lists(user.id, limit=100):
        count += 1
        print(f"\n--- List #{count} ---")
        print(f"  ID: {twitter_list.id}")
        print(f"  名称: {twitter_list.name}")
        print(f"  描述: {twitter_list.description or 'N/A'}")
        print(f"  成员数: {twitter_list.memberCount}")
        print(f"  订阅者数: {twitter_list.subscriberCount}")
        if twitter_list.creator:
            print(f"  创建者: @{twitter_list.creator.username}")

    print(f"\n{'='*60}")
    print(f"共找到 {count} 个 Lists")
    print("="*60)


async def main():
    await setup_account_with_cookies()
    await scrape_lists()


if __name__ == "__main__":
    asyncio.run(main())
