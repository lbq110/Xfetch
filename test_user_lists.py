#!/usr/bin/env python3
"""
测试脚本：获取用户关注的 Lists

使用方法：
1. 先运行 add_account_example() 添加 Twitter 账户
2. 然后运行 main() 测试抓取功能

运行命令：
    /opt/anaconda3/bin/python test_user_lists.py
"""

import asyncio
import sys
import json
sys.path.insert(0, '/Users/lubinquan/Desktop/study/Xfetch/twscrape')

from twscrape import API, AccountsPool


async def main():
    """测试获取用户的 Lists"""
    # 初始化 API（开启调试模式查看详细信息）
    api = API(debug=True)

    # 目标用户名（可以修改为你想要查询的用户）
    target_username = "elonmusk"  # 示例

    print(f"\n{'='*60}")
    print(f"获取用户 @{target_username} 的信息")
    print('='*60)

    # 先获取用户 ID
    try:
        user = await api.user_by_login(target_username)
        if not user:
            print(f"无法找到用户 @{target_username}")
            print("请确保已添加并登录 Twitter 账户")
            return

        print(f"用户 ID: {user.id}")
        print(f"用户名: @{user.username}")
        print(f"显示名: {user.displayname}")
        print(f"粉丝数: {user.followersCount:,}")
        print(f"关注数: {user.friendsCount:,}")

        print(f"\n{'='*60}")
        print(f"获取用户 @{target_username} 的 Lists")
        print('='*60)

        # 获取用户的 Lists
        count = 0
        async for twitter_list in api.user_lists(user.id, limit=50):
            count += 1
            print(f"\n--- List #{count} ---")
            print(f"  ID: {twitter_list.id}")
            print(f"  名称: {twitter_list.name}")
            desc = twitter_list.description[:80] + "..." if len(twitter_list.description or "") > 80 else twitter_list.description
            print(f"  描述: {desc or 'N/A'}")
            print(f"  成员数: {twitter_list.memberCount}")
            print(f"  订阅者数: {twitter_list.subscriberCount}")
            print(f"  模式: {twitter_list.mode}")
            print(f"  正在关注: {twitter_list.isFollowing}")
            if twitter_list.creator:
                print(f"  创建者: @{twitter_list.creator.username}")

        print(f"\n{'='*60}")
        print(f"共找到 {count} 个 Lists")
        print('='*60)

    except Exception as e:
        print(f"发生错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_raw_api():
    """测试原始 API 响应（用于调试）"""
    api = API(debug=True)

    target_username = "elonmusk"

    user = await api.user_by_login(target_username)
    if not user:
        print(f"无法找到用户 @{target_username}")
        return

    print(f"用户 ID: {user.id}")

    # 获取原始响应
    print("\n获取原始 Lists 响应...")
    async for rep in api.user_lists_raw(user.id, limit=5):
        data = rep.json()
        # 保存到文件以便分析
        with open("/tmp/lists_response.json", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"响应已保存到 /tmp/lists_response.json")
        print(f"响应状态码: {rep.status_code}")
        break


async def add_account_example():
    """
    添加 Twitter 账户示例

    注意：需要替换为真实的账户信息！
    """
    pool = AccountsPool()

    # 添加账户（请替换为真实的账户信息）
    await pool.add_account(
        username="your_twitter_username",      # Twitter 用户名
        password="your_twitter_password",      # Twitter 密码
        email="your_email@example.com",        # 注册邮箱
        email_password="your_email_password"   # 邮箱密码（用于获取验证码）
    )

    print("账户已添加，正在登录...")

    # 登录所有账户
    await pool.login_all()

    print("登录成功！")

    # 查看账户状态
    stats = await pool.stats()
    print(f"\n账户统计: {stats}")


async def check_accounts():
    """检查已添加的账户状态"""
    pool = AccountsPool()
    stats = await pool.stats()
    print(f"账户统计: {stats}")

    # 列出所有账户
    accounts = await pool.accounts_info()
    for acc in accounts:
        print(f"  - {acc['username']}: active={acc['active']}, last_used={acc.get('last_used', 'N/A')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Twitter Lists 抓取测试")
    parser.add_argument("--add", action="store_true", help="添加账户")
    parser.add_argument("--check", action="store_true", help="检查账户状态")
    parser.add_argument("--raw", action="store_true", help="测试原始 API")
    parser.add_argument("--user", type=str, default="elonmusk", help="目标用户名")

    args = parser.parse_args()

    if args.add:
        asyncio.run(add_account_example())
    elif args.check:
        asyncio.run(check_accounts())
    elif args.raw:
        asyncio.run(test_raw_api())
    else:
        asyncio.run(main())
