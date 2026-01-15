"""抓取模块 - 从 Twitter List 抓取推文"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / 'twscrape'))
from twscrape import API

from .base import BaseModule


class Fetcher(BaseModule):
    """推文抓取模块"""

    def __init__(self, config_path: str = "config/fetcher.yaml") -> None:
        super().__init__(config_path)
        self.api = API(self.config['db_path'], debug=False)
        self.list_id = self.config['list_id']
        self.max_tweets = self.config['max_tweets_per_run']

    def _load_state(self) -> dict[str, Any]:
        """加载状态文件"""
        return self.load_json("data/state.json") or {
            "last_fetch_time": None,
            "last_tweet_id": None,
            "total_fetched": 0
        }

    def _save_state(self, state: dict[str, Any]) -> None:
        """保存状态文件"""
        self.save_json(state, "data/state.json")

    def _extract_tweet_data(self, tweet: Any) -> dict[str, Any]:
        """从推文对象提取需要的字段"""
        return {
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

    async def _fetch_tweets(self, since_id: Optional[int] = None) -> list[dict[str, Any]]:
        """抓取推文（增量抓取，只获取新推文）"""
        tweets = []
        skipped = 0

        self.logger.info(f"开始抓取 List {self.list_id}")
        self.logger.info(f"最大抓取数: {self.max_tweets} 条")

        if since_id:
            self.logger.info(f"增量模式: 只抓取 ID > {since_id} 的新推文")
        else:
            self.logger.info("全量模式: 首次抓取或无历史记录")

        try:
            async for tweet in self.api.list_timeline(self.list_id, limit=self.max_tweets * 2):
                if since_id and tweet.id <= since_id:
                    if skipped == 0:
                        self.logger.info(f"遇到已抓取推文 (ID: {tweet.id})，跳过后续旧推文")
                    skipped += 1
                    continue

                tweets.append(self._extract_tweet_data(tweet))

                if len(tweets) % 10 == 0:
                    self.logger.info(f"已抓取 {len(tweets)} 条新推文...")

                if len(tweets) >= self.max_tweets:
                    self.logger.info(f"已达到最大抓取数 {self.max_tweets}，停止")
                    break

        except Exception as e:
            self.logger.error(f"抓取出错: {e}")

        skip_msg = f"，跳过 {skipped} 条旧推文" if skipped > 0 else ""
        self.logger.info(f"抓取完成: {len(tweets)} 条新推文{skip_msg}")

        return tweets

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """运行抓取"""
        state = self._load_state()

        since_id = state.get('last_tweet_id')
        if since_id and isinstance(since_id, str):
            since_id = int(since_id)

        tweets = asyncio.run(self._fetch_tweets(since_id))

        if not tweets:
            self.logger.info("无新推文")
            return None

        output_file = f"data/raw/{self.get_timestamp_filename()}"
        self.save_json({
            'fetch_time': datetime.now().isoformat(),
            'list_id': self.list_id,
            'count': len(tweets),
            'since_id': since_id,
            'newest_id': tweets[0]['id'],
            'oldest_id': tweets[-1]['id'],
            'tweets': tweets
        }, output_file)

        state['last_fetch_time'] = datetime.now().isoformat()
        state['last_tweet_id'] = tweets[0]['id']
        state['total_fetched'] = state.get('total_fetched', 0) + len(tweets)
        self._save_state(state)

        self.logger.info(f"状态已更新: last_tweet_id = {tweets[0]['id']}")

        return output_file
