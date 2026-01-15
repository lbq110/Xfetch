#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/Users/lubinquan/Desktop/study/Xfetch/twscrape')

from twscrape import API, AccountsPool


async def setup_and_scrape():
    # 初始化账户池
    pool = AccountsPool("/Users/lubinquan/Desktop/study/Xfetch/accounts.db")

    # 添加账户
    print("正在添加账户...")
    await pool.add_account(
        username="roger2862541",
        password="binbin110110",
        email="lubinquan110@gmail.com",
        email_password="binbin110110"
    )

    print("正在登录账户...")
    await pool.login_all()

    # 查看账户状态
    stats = await pool.stats()
    print(f"账户状态: {stats}")

    # 初始化 API
    api = API(pool=pool, debug=True)

    # 获取当前用户信息
    print("\n获取用户 roger2862541 的 Lists...")

    user = await api.user_by_login("roger2862541")
    if not user:
        print("无法获取用户信息")
        return

    print(f"用户 ID: {user.id}")
    print(f"用户名: @{user.username}")

    # 获取用户的 Lists
    print("\n正在获取 Lists...")
    count = 0
    target_list = None

    async for twitter_list in api.user_lists(user.id, limit=100):
        count += 1
        print(f"\n--- List #{count} ---")
        print(f"  ID: {twitter_list.id}")
        print(f"  名称: {twitter_list.name}")
        print(f"  描述: {twitter_list.description or 'N/A'}")
        print(f"  成员数: {twitter_list.memberCount}")
        print(f"  订阅者数: {twitter_list.subscriberCount}")

        # 查找 MY AI LIST
        if "AI" in twitter_list.name.upper():
            target_list = twitter_list

    print(f"\n共找到 {count} 个 Lists")

    if target_list:
        print(f"\n找到目标 List: {target_list.name} (ID: {target_list.id})")


if __name__ == "__main__":
    asyncio.run(setup_and_scrape())
