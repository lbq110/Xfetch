"""内容分析模块 - 批量判断AI相关性和内容价值，追踪博主质量评分"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from .base import BaseModule
from .kol_agent import KOLAgent

DEFAULT_ANALYSIS_RESULT = {
    'is_ai_related': False,
    'relevance_score': 0,
    'value_score': 1,
    'reason': '',
    'is_fake_news': False,
    'fake_reason': ''
}


class ContentAnalyzer(BaseModule):
    """
    内容分析模块 - 批量判断AI相关性和内容价值

    优势：
    1. 批量LLM调用，大幅节省API成本（约60%）
    2. 使用便宜小模型，进一步降低成本
    3. 不依赖关键词列表，不会遗漏内容
    4. 同时评估RT转发的原内容价值
    5. 追踪博主质量评分
    """

    def __init__(self, config_path: str = "config/content_analyzer.yaml") -> None:
        super().__init__(config_path)
        self.value_threshold = self.config.get('value_threshold', 5)
        self.provider = self.config.get('llm_provider', 'gemini')
        self.model = self.config.get('llm_model', 'gemini-2.0-flash-lite')
        self.batch_size = self.config.get('batch_size', 5)

        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])

        self.author_stats_file = Path("data/author_stats.json")
        self.author_stats = self._load_author_stats()

        self.processed_ids_file = Path("data/processed_ids.json")
        self.processed_ids = self._load_processed_ids()

        self.kol_agent = KOLAgent()

    def _load_author_stats(self) -> dict[str, Any]:
        """加载博主统计数据"""
        if self.author_stats_file.exists():
            try:
                with open(self.author_stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {'authors': {}, 'last_updated': None}

    def _load_processed_ids(self) -> set:
        """加载已处理的推文ID集合"""
        if self.processed_ids_file.exists():
            try:
                with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f).get('ids', []))
            except (json.JSONDecodeError, IOError):
                pass
        return set()

    def _save_processed_ids(self) -> None:
        """保存已处理的推文ID（保留最近10000个）"""
        ids_list = list(self.processed_ids)
        if len(ids_list) > 10000:
            ids_list = ids_list[-10000:]
            self.processed_ids = set(ids_list)

        self.processed_ids_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.processed_ids_file, 'w', encoding='utf-8') as f:
            json.dump({
                'ids': ids_list,
                'count': len(ids_list),
                'last_updated': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def _save_author_stats(self) -> None:
        """保存博主统计数据"""
        self.author_stats['last_updated'] = datetime.now().isoformat()
        self.author_stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.author_stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.author_stats, f, ensure_ascii=False, indent=2)

    def _update_author_stats(
        self,
        username: str,
        displayname: str,
        followers: int,
        passed: bool,
        score: int
    ) -> None:
        """更新博主统计数据"""
        authors = self.author_stats['authors']
        now = datetime.now().isoformat()

        if username not in authors:
            authors[username] = {
                'displayname': displayname,
                'followers': followers,
                'total_tweets': 0,
                'passed_tweets': 0,
                'rejected_tweets': 0,
                'total_score': 0,
                'scores': [],
                'first_seen': now,
                'last_seen': None
            }

        author = authors[username]
        author['total_tweets'] += 1
        author['last_seen'] = now
        author['displayname'] = displayname
        author['followers'] = followers
        author['total_score'] += score

        if passed:
            author['passed_tweets'] += 1
        else:
            author['rejected_tweets'] += 1

        author['scores'].append(score)
        if len(author['scores']) > 20:
            author['scores'] = author['scores'][-20:]

    def _extract_rt_content(self, content: str) -> tuple[bool, str, str]:
        """提取RT转发的原始内容，返回 (is_rt, original_author, original_content)"""
        rt_match = re.match(r'^RT @(\w+):\s*(.+)$', content, re.DOTALL)
        if rt_match:
            return True, rt_match.group(1), rt_match.group(2)
        return False, '', content

    def _analyze_batch(self, tweets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量分析多条推文"""
        if not tweets:
            return []

        tweets_text = []
        for i, tweet in enumerate(tweets, 1):
            user = tweet['user']
            is_rt, rt_author, _ = self._extract_rt_content(tweet['content'])
            rt_note = f" [转发自@{rt_author}]" if is_rt else ""

            tweets_text.append(
                f"【推文{i}】{rt_note}\n"
                f"作者: @{user['username']} ({user['displayname']}) | 粉丝: {user['followers']}\n"
                f"互动: 回复{tweet['replyCount']} 转发{tweet['retweetCount']} 点赞{tweet['likeCount']}\n"
                f"内容: {tweet['content'][:500]}"
            )

        prompt = f"""请批量分析以下{len(tweets)}条推文的AI相关性和内容价值。

{chr(10).join(tweets_text)}

评估标准：
1. AI相关性(0-100): 必须明确讨论AI/ML/大模型技术。仅有#AI标签无实质内容<50分
2. 内容价值(1-10): 8-10高价值(原创深度/重要发布) | 5-7中等 | 1-4低价值
3. 虚假信息: 检查是否提到不存在的AI模型(如GPT-5/Claude-4等)

重要：转发(RT)内容应评估原内容价值，不因转发降分。高粉丝作者的内容可能更权威。

请返回JSON数组，每条对应一个结果：
[
  {{"id": 1, "is_ai_related": true/false, "relevance_score": 0-100, "value_score": 1-10, "reason": "简短理由", "is_fake_news": false, "fake_reason": ""}},
  ...
]"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type='application/json'
                )
            )
            results = json.loads(response.text.strip())

            while len(results) < len(tweets):
                self.logger.warning(
                    f"批量结果数量不匹配: 期望{len(tweets)}, 得到{len(results)}"
                )
                results.append({**DEFAULT_ANALYSIS_RESULT, 'reason': '分析结果缺失'})

            for result in results:
                if result.get('is_fake_news', False):
                    result['value_score'] = min(result['value_score'], 2)

            return results

        except Exception as e:
            self.logger.error(f"批量分析失败: {e}")
            return [{**DEFAULT_ANALYSIS_RESULT, 'reason': f'Error: {e}'} for _ in tweets]

    def _is_tweet_passed(self, analysis: dict[str, Any]) -> bool:
        """判断推文是否通过筛选"""
        return (
            analysis['is_ai_related'] and
            analysis['relevance_score'] >= 50 and
            analysis['value_score'] >= self.value_threshold
        )

    def _enrich_tweet_with_analysis(
        self,
        tweet: dict[str, Any],
        analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """为通过的推文添加分析结果"""
        tweet['analysis'] = {
            'relevance_score': analysis['relevance_score'],
            'value_score': analysis['value_score'],
            'reason': analysis['reason'],
            'is_fake_news': analysis.get('is_fake_news', False),
            'fake_reason': analysis.get('fake_reason', '')
        }
        tweet['filter'] = {
            'is_relevant': True,
            'score': analysis['relevance_score'],
            'reason': analysis['reason']
        }
        tweet['value'] = {
            'score': analysis['value_score'],
            'reason': analysis['reason']
        }
        return tweet

    def get_author_report(
        self,
        min_tweets: int = 5,
        enable_kol_check: bool = True
    ) -> dict[str, Any]:
        """生成博主质量报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'high_quality_authors': [],
            'low_quality_authors': [],
            'recommend_remove': [],
            'identified_kols': [],
            'all_authors': []
        }

        authors_data = []
        suspicious_authors = []

        for username, stats in self.author_stats['authors'].items():
            followers = stats['followers']
            total_tweets = stats['total_tweets']
            passed_tweets = stats['passed_tweets']
            pass_rate = passed_tweets / total_tweets if total_tweets > 0 else 0

            if enable_kol_check and self.kol_agent.should_check(stats):
                suspicious_authors.append({
                    'username': username,
                    'displayname': stats['displayname'],
                    'followers': followers,
                    'total_tweets': total_tweets,
                    'passed_tweets': passed_tweets,
                    'pass_rate': pass_rate
                })

            required_tweets = 10 if followers >= 100000 else min_tweets
            if total_tweets < required_tweets:
                continue

            avg_score = stats['total_score'] / total_tweets
            recent_avg = (
                sum(stats['scores']) / len(stats['scores'])
                if stats['scores'] else 0
            )

            author_info = {
                'username': username,
                'displayname': stats['displayname'],
                'followers': followers,
                'total_tweets': total_tweets,
                'passed_tweets': passed_tweets,
                'rejected_tweets': stats['rejected_tweets'],
                'pass_rate': round(pass_rate, 2),
                'avg_score': round(avg_score, 2),
                'recent_avg_score': round(recent_avg, 2),
                'first_seen': stats['first_seen'],
                'last_seen': stats['last_seen']
            }
            authors_data.append(author_info)

            if pass_rate >= 0.7:
                report['high_quality_authors'].append(author_info)
            elif pass_rate <= 0.3:
                report['low_quality_authors'].append(author_info)
                remove_threshold = 15 if followers >= 100000 else 8
                score_threshold = 2 if followers >= 100000 else 3
                if total_tweets >= remove_threshold and recent_avg < score_threshold:
                    report['recommend_remove'].append(author_info)

        if enable_kol_check and suspicious_authors:
            self.logger.info(f"检测到 {len(suspicious_authors)} 个可疑博主，启动KOL识别...")
            kol_results = self.kol_agent.batch_identify(suspicious_authors)

            for username, result in kol_results.items():
                report['identified_kols'].append({
                    'username': username,
                    'is_important_kol': result.get('is_important_kol', False),
                    'confidence': result.get('confidence', 0),
                    'reason': result.get('reason', ''),
                    'background': result.get('background', ''),
                    'recommendation': result.get('recommendation', 'watch')
                })

                if result.get('is_important_kol') or result.get('recommendation') == 'keep':
                    report['recommend_remove'] = [
                        a for a in report['recommend_remove']
                        if a['username'] != username
                    ]

        report['high_quality_authors'].sort(key=lambda x: x['pass_rate'], reverse=True)
        report['low_quality_authors'].sort(key=lambda x: x['pass_rate'])
        report['recommend_remove'].sort(key=lambda x: x['recent_avg_score'])
        authors_data.sort(key=lambda x: x['pass_rate'], reverse=True)
        report['all_authors'] = authors_data

        report['summary'] = {
            'total_authors': len(authors_data),
            'high_quality_count': len(report['high_quality_authors']),
            'low_quality_count': len(report['low_quality_authors']),
            'recommend_remove_count': len(report['recommend_remove']),
            'identified_kols_count': len(report['identified_kols'])
        }

        return report

    def run(self, input_file: str) -> Optional[str]:
        """运行内容分析"""
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        all_tweets = data['tweets']
        tweets = [t for t in all_tweets if t['id'] not in self.processed_ids]
        skipped_count = len(all_tweets) - len(tweets)

        if skipped_count > 0:
            self.logger.info(f"跳过 {skipped_count} 条已处理的推文")

        if not tweets:
            self.logger.info("所有推文都已处理过，无新内容")
            return None

        self.logger.info(f"开始分析 {len(tweets)} 条新推文 (批量大小: {self.batch_size})")

        passed_tweets = []
        rejected_tweets = []

        for batch_start in range(0, len(tweets), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(tweets))
            batch = tweets[batch_start:batch_end]

            self.logger.info(f"处理批次: {batch_start + 1}-{batch_end}/{len(tweets)}")
            results = self._analyze_batch(batch)

            for tweet, analysis in zip(batch, results):
                user = tweet['user']
                passed = self._is_tweet_passed(analysis)

                self._update_author_stats(
                    user['username'],
                    user['displayname'],
                    user['followers'],
                    passed=passed,
                    score=analysis['value_score']
                )

                if passed:
                    passed_tweets.append(self._enrich_tweet_with_analysis(tweet, analysis))
                else:
                    rejected_tweets.append(tweet)

        for tweet in tweets:
            self.processed_ids.add(tweet['id'])
        self._save_processed_ids()
        self._save_author_stats()

        self.logger.info(f"分析完成: {len(passed_tweets)}/{len(tweets)} 条推文通过")

        if rejected_tweets:
            rejected_file = input_file.replace('/raw/', '/rejected/analyzer_')
            self.save_json({
                **data,
                'tweets': rejected_tweets,
                'rejection_stats': {
                    'total': len(tweets),
                    'rejected': len(rejected_tweets),
                    'stage': 'content_analyzer'
                }
            }, rejected_file)
            self.logger.info(f"保存被拒绝数据: {rejected_file}")

        if not passed_tweets:
            self.logger.info("无高价值AI内容")
            return None

        output_file = input_file.replace('/raw/', '/evaluated/')
        self.save_json({
            **data,
            'tweets': passed_tweets,
            'analysis_stats': {
                'total': len(tweets),
                'passed': len(passed_tweets),
                'rejected': len(rejected_tweets),
                'pass_rate': len(passed_tweets) / len(tweets),
                'avg_value_score': sum(t['value']['score'] for t in passed_tweets) / len(passed_tweets)
            }
        }, output_file)

        return output_file
