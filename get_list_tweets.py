#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/Users/lubinquan/Desktop/study/Xfetch/twscrape')

from twscrape import API
from twscrape.db import execute

DB_PATH = "/Users/lubinquan/Desktop/study/Xfetch/accounts.db"
LIST_ID = 2010759492212760999  # MY AI LIST


async def reset_locks():
    await execute(DB_PATH, 'UPDATE accounts SET locks = "{}"')


async def get_list_timeline():
    api = API(DB_PATH, debug=False)

    print(f"\n{'='*70}")
    print(f"获取 MY AI LIST (ID: {LIST_ID}) 的最新 10 条推文")
    print('='*70)

    count = 0
    async for tweet in api.list_timeline(LIST_ID, limit=10):
        count += 1
        print(f"\n{'─'*70}")
        print(f"📝 推文 #{count}")
        print(f"{'─'*70}")
        print(f"  作者: @{tweet.user.username} ({tweet.user.displayname})")
        print(f"  时间: {tweet.date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  链接: {tweet.url}")
        print(f"\n  内容:")
        # 格式化内容，每行最多 60 字符
        content = tweet.rawContent
        for i in range(0, len(content), 60):
            print(f"    {content[i:i+60]}")
        print(f"\n  💬 回复: {tweet.replyCount}  🔄 转发: {tweet.retweetCount}  ❤️ 点赞: {tweet.likeCount}")

        if tweet.media and (tweet.media.photos or tweet.media.videos):
            media_count = len(tweet.media.photos) + len(tweet.media.videos)
            print(f"  📷 媒体: {media_count} 个")

    print(f"\n{'='*70}")
    print(f"共获取 {count} 条推文")
    print('='*70)


async def main():
    await reset_locks()
    await get_list_timeline()


if __name__ == "__main__":
    asyncio.run(main())
