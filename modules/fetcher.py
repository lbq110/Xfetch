"""
抓取模块 - 从 Twitter List 抓取推文
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'twscrape'))
from twscrape import API

from .base import BaseModule


class Fetcher(BaseModule):
    """推文抓取模块"""

    def __init__(self, config_path: str = "config/fetcher.yaml"):
        super().__init__(config_path)
        self.api = API(self.config['db_path'], debug=False)
        self.list_id = self.config['list_id']
        self.max_tweets = self.config['max_tweets_per_run']

    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件"""
        state_file = Path("data/state.json")
        return self.load_json(str(state_file)) or {
            "last_fetch_time": None,
            "last_tweet_id": None,
            "total_fetched": 0
        }

    def _save_state(self, state: Dict[str, Any]):
        """保存状态文件"""
        self.save_json(state, "data/state.json")

    async def _fetch_tweets(self, since_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        抓取推文（增量抓取，只获取新推文）

        Args:
            since_id: 上次抓取的最新推文 ID（数值类型）

        Returns:
            推文列表
        """
        tweets = []
        count = 0
        skipped = 0

        self.logger.info(f"开始抓取 List {self.list_id}")
        self.logger.info(f"最大抓取数: {self.max_tweets} 条")

        if since_id:
            self.logger.info(f"增量模式: 只抓取 ID > {since_id} 的新推文")
        else:
            self.logger.info(f"全量模式: 首次抓取或无历史记录")

        try:
            async for tweet in self.api.list_timeline(self.list_id, limit=self.max_tweets * 2):
                # 使用数值比较，更可靠
                if since_id and tweet.id <= since_id:
                    skipped += 1
                    if skipped == 1:
                        self.logger.info(f"遇到已抓取推文 (ID: {tweet.id})，跳过后续旧推文")
                    continue

                # 提取需要的字段
                tweet_data = {
                    'id': tweet.id,
                    'id_str': tweet.id_str,
                    'url': tweet.url,
                    'date': tweet.date.isoformat(),
                    'user': {
                        'id': tweet.user.id,
                        'username': tweet.user.username,
                        'displayname': tweet.user.displayname,
                        'followers': tweet.user.followersCount,
                    },
                    'content': tweet.rawContent,
                    'lang': tweet.lang,
                    'replyCount': tweet.replyCount,
                    'retweetCount': tweet.retweetCount,
                    'likeCount': tweet.likeCount,
                    'quoteCount': tweet.quoteCount,
                    'viewCount': getattr(tweet, 'viewCount', 0),
                    'isReply': getattr(tweet, 'inReplyToTweetId', None) is not None,
                    'isRetweet': tweet.retweetedTweet is not None,
                    'hasMedia': bool(tweet.media and (tweet.media.photos or tweet.media.videos)),
                }

                tweets.append(tweet_data)
                count += 1

                if count % 10 == 0:
                    self.logger.info(f"已抓取 {count} 条新推文...")

                # 达到最大数量限制
                if count >= self.max_tweets:
                    self.logger.info(f"已达到最大抓取数 {self.max_tweets}，停止")
                    break

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")

        self.logger.info(f"抓取完成: {len(tweets)} 条新推文" +
                        (f"，跳过 {skipped} 条旧推文" if skipped > 0 else ""))
        return tweets

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        运行抓取

        Returns:
            输出文件路径
        """
        # 加载状态
        state = self._load_state()

        # 使用数值类型的 since_id
        since_id = state.get('last_tweet_id')
        if since_id and isinstance(since_id, str):
            since_id = int(since_id)

        # 抓取推文
        tweets = asyncio.run(self._fetch_tweets(since_id))

        if not tweets:
            self.logger.info("无新推文")
            return None

        # 生成输出文件
        output_file = f"data/raw/{self.get_timestamp_filename()}"
        output_data = {
            'fetch_time': datetime.now().isoformat(),
            'list_id': self.list_id,
            'count': len(tweets),
            'since_id': since_id,
            'newest_id': tweets[0]['id'],
            'oldest_id': tweets[-1]['id'],
            'tweets': tweets
        }

        self.save_json(output_data, output_file)

        # 更新状态 - 使用数值类型
        state['last_fetch_time'] = datetime.now().isoformat()
        state['last_tweet_id'] = tweets[0]['id']  # 最新的推文 ID（数值类型）
        state['total_fetched'] = state.get('total_fetched', 0) + len(tweets)
        self._save_state(state)

        self.logger.info(f"状态已更新: last_tweet_id = {tweets[0]['id']}")

        return output_file
