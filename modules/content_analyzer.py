"""
内容分析模块 - 合并Filter和Evaluator，一次LLM调用完成判断
同时追踪博主质量评分
"""

import json
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types

from .base import BaseModule


class ContentAnalyzer(BaseModule):
    """
    内容分析模块 - 一次性判断AI相关性和内容价值

    优势：
    1. 单次LLM调用，节省API成本
    2. 不依赖关键词列表，不会遗漏内容
    3. 同时评估RT转发的原内容价值
    4. 追踪博主质量评分
    """

    def __init__(self, config_path: str = "config/content_analyzer.yaml"):
        super().__init__(config_path)
        self.value_threshold = self.config.get('value_threshold', 5)
        self.provider = self.config.get('llm_provider', 'gemini')
        self.model = self.config.get('llm_model', 'gemini-2.5-flash')

        # 初始化LLM客户端
        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])

        # 博主追踪数据
        self.author_stats_file = Path("data/author_stats.json")
        self.author_stats = self._load_author_stats()

        # 已处理推文ID记录（防止重复处理）
        self.processed_ids_file = Path("data/processed_ids.json")
        self.processed_ids = self._load_processed_ids()

    def _load_author_stats(self) -> Dict[str, Any]:
        """加载博主统计数据"""
        if self.author_stats_file.exists():
            try:
                with open(self.author_stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {'authors': {}, 'last_updated': None}

    def _load_processed_ids(self) -> set:
        """加载已处理的推文ID集合"""
        if self.processed_ids_file.exists():
            try:
                with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('ids', []))
            except:
                pass
        return set()

    def _save_processed_ids(self):
        """保存已处理的推文ID"""
        # 只保留最近的10000个ID，避免文件过大
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

    def _save_author_stats(self):
        """保存博主统计数据"""
        self.author_stats['last_updated'] = datetime.now().isoformat()
        self.author_stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.author_stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.author_stats, f, ensure_ascii=False, indent=2)

    def _update_author_stats(self, username: str, displayname: str,
                             followers: int, passed: bool, score: int):
        """更新博主统计数据"""
        if username not in self.author_stats['authors']:
            self.author_stats['authors'][username] = {
                'displayname': displayname,
                'followers': followers,
                'total_tweets': 0,
                'passed_tweets': 0,
                'rejected_tweets': 0,
                'total_score': 0,
                'scores': [],  # 最近20条的评分
                'first_seen': datetime.now().isoformat(),
                'last_seen': None
            }

        author = self.author_stats['authors'][username]
        author['total_tweets'] += 1
        author['last_seen'] = datetime.now().isoformat()
        author['displayname'] = displayname  # 更新显示名
        author['followers'] = followers  # 更新粉丝数

        if passed:
            author['passed_tweets'] += 1
        else:
            author['rejected_tweets'] += 1

        author['total_score'] += score
        author['scores'].append(score)
        # 只保留最近20条的评分
        if len(author['scores']) > 20:
            author['scores'] = author['scores'][-20:]

    def _extract_rt_content(self, content: str) -> tuple[bool, str, str]:
        """
        提取RT转发的原始内容

        Returns:
            (is_rt, original_author, original_content)
        """
        # 检测RT格式: "RT @username: content"
        rt_match = re.match(r'^RT @(\w+):\s*(.+)$', content, re.DOTALL)
        if rt_match:
            return True, rt_match.group(1), rt_match.group(2)
        return False, '', content

    def _analyze_content(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        一次性分析内容：AI相关性 + 价值评分

        Returns:
            {
                'is_ai_related': bool,
                'relevance_score': int (0-100),
                'value_score': int (1-10),
                'reason': str,
                'is_fake_news': bool,
                'fake_reason': str
            }
        """
        content = tweet['content']
        user = tweet['user']

        # 检测RT转发
        is_rt, rt_author, actual_content = self._extract_rt_content(content)

        # 构建prompt
        rt_note = ""
        if is_rt:
            rt_note = f"\n⚠️ 这是一条转发(RT)，原作者是 @{rt_author}。请评估原内容的价值，不要因为是转发就降低评分。"

        prompt = f"""请分析以下推文，判断其AI相关性和内容价值。

推文信息：
- 作者: @{user['username']} ({user['displayname']})
- 粉丝数: {user['followers']}
- 互动数据: 回复{tweet['replyCount']} | 转发{tweet['retweetCount']} | 点赞{tweet['likeCount']}
{rt_note}

推文内容：
{content}

请进行以下判断：

1. **AI相关性** (0-100分)
   - 必须明确讨论AI、机器学习、大模型、或相关技术
   - 仅使用#AI标签或简单提及"AI"但无实质内容的，相关性应低于50分
   - 讨论具体技术（如GPT、Claude、LLM、diffusion、transformer等）的，相关性应高于70分

2. **内容价值** (1-10分)
   - 8-10分: 高价值（原创深度分析、重要产品发布、实用技术技巧、权威来源的重要新闻）
   - 5-7分: 中等价值（有一定信息量、值得了解）
   - 1-4分: 低价值（无实质内容、纯营销、信息过时）

3. **虚假信息检测**
   - 检查是否提到了不存在的AI模型（如GPT-5、GPT-6、Claude-4等尚未发布的版本）
   - 检查是否有明显的误导性声明

请以JSON格式回复：
{{
  "is_ai_related": true/false,
  "relevance_score": 0-100,
  "value_score": 1-10,
  "reason": "简短说明判断理由（1-2句话）",
  "is_fake_news": true/false,
  "fake_reason": "如果是虚假信息，说明原因，否则为空字符串"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type='application/json'
                )
            )
            result = json.loads(response.text.strip())

            # 如果检测到虚假信息，大幅降低价值评分
            if result.get('is_fake_news', False):
                result['value_score'] = min(result['value_score'], 2)
                self.logger.warning(f"检测到可疑信息: {result['fake_reason']}")

            return result

        except Exception as e:
            self.logger.error(f"分析失败: {e}")
            return {
                'is_ai_related': False,
                'relevance_score': 0,
                'value_score': 1,
                'reason': f'Error: {str(e)}',
                'is_fake_news': False,
                'fake_reason': ''
            }

    def _process_tweet(self, tweet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理单条推文

        Returns:
            处理后的推文（如果通过）或 None（如果被过滤）
        """
        # 基本信息
        content = tweet['content']
        user = tweet['user']
        username = user['username']

        # 内容太短直接跳过（但仍然记录）
        if len(content.strip()) < 20:
            self._update_author_stats(
                username, user['displayname'], user['followers'],
                passed=False, score=0
            )
            return None

        # LLM分析
        analysis = self._analyze_content(tweet)

        # 记录博主统计
        passed = (analysis['is_ai_related'] and
                  analysis['relevance_score'] >= 50 and
                  analysis['value_score'] >= self.value_threshold)

        self._update_author_stats(
            username, user['displayname'], user['followers'],
            passed=passed, score=analysis['value_score']
        )

        # 判断是否通过
        if not analysis['is_ai_related']:
            return None

        if analysis['relevance_score'] < 50:
            return None

        if analysis['value_score'] < self.value_threshold:
            return None

        # 通过，添加分析结果
        tweet['analysis'] = {
            'relevance_score': analysis['relevance_score'],
            'value_score': analysis['value_score'],
            'reason': analysis['reason'],
            'is_fake_news': analysis.get('is_fake_news', False),
            'fake_reason': analysis.get('fake_reason', '')
        }

        # 兼容旧格式
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

    def get_author_report(self, min_tweets: int = 3) -> Dict[str, Any]:
        """
        生成博主质量报告

        Args:
            min_tweets: 最少推文数量才纳入统计

        Returns:
            博主质量报告
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'high_quality_authors': [],    # 高质量博主（通过率>70%）
            'low_quality_authors': [],     # 低质量博主（通过率<30%）
            'recommend_remove': [],        # 建议移除的博主
            'all_authors': []
        }

        authors_data = []

        for username, stats in self.author_stats['authors'].items():
            if stats['total_tweets'] < min_tweets:
                continue

            pass_rate = stats['passed_tweets'] / stats['total_tweets']
            avg_score = stats['total_score'] / stats['total_tweets']
            recent_avg = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0

            author_info = {
                'username': username,
                'displayname': stats['displayname'],
                'followers': stats['followers'],
                'total_tweets': stats['total_tweets'],
                'passed_tweets': stats['passed_tweets'],
                'rejected_tweets': stats['rejected_tweets'],
                'pass_rate': round(pass_rate, 2),
                'avg_score': round(avg_score, 2),
                'recent_avg_score': round(recent_avg, 2),
                'first_seen': stats['first_seen'],
                'last_seen': stats['last_seen']
            }

            authors_data.append(author_info)

            # 分类
            if pass_rate >= 0.7:
                report['high_quality_authors'].append(author_info)
            elif pass_rate <= 0.3:
                report['low_quality_authors'].append(author_info)
                # 如果最近评分也很低，建议移除
                if recent_avg < 3:
                    report['recommend_remove'].append(author_info)

        # 排序
        report['high_quality_authors'].sort(key=lambda x: x['pass_rate'], reverse=True)
        report['low_quality_authors'].sort(key=lambda x: x['pass_rate'])
        report['recommend_remove'].sort(key=lambda x: x['recent_avg_score'])

        # 按通过率排序所有博主
        authors_data.sort(key=lambda x: x['pass_rate'], reverse=True)
        report['all_authors'] = authors_data

        # 统计摘要
        report['summary'] = {
            'total_authors': len(authors_data),
            'high_quality_count': len(report['high_quality_authors']),
            'low_quality_count': len(report['low_quality_authors']),
            'recommend_remove_count': len(report['recommend_remove'])
        }

        return report

    def run(self, input_file: str) -> Optional[str]:
        """
        运行内容分析

        Args:
            input_file: 输入文件路径 (data/raw/xxx.json)

        Returns:
            输出文件路径
        """
        # 加载输入数据
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        all_tweets = data['tweets']

        # 过滤掉已处理的推文（去重）
        tweets = []
        skipped_count = 0
        for tweet in all_tweets:
            tweet_id = tweet['id']
            if tweet_id in self.processed_ids:
                skipped_count += 1
            else:
                tweets.append(tweet)

        if skipped_count > 0:
            self.logger.info(f"跳过 {skipped_count} 条已处理的推文")

        if not tweets:
            self.logger.info("所有推文都已处理过，无新内容")
            return None

        self.logger.info(f"开始分析 {len(tweets)} 条新推文")

        # 分析推文
        passed_tweets = []
        rejected_tweets = []

        for i, tweet in enumerate(tweets, 1):
            if i % 10 == 0:
                self.logger.info(f"处理进度: {i}/{len(tweets)}")

            result = self._process_tweet(tweet)
            if result:
                passed_tweets.append(result)
            else:
                rejected_tweets.append(tweet)

        # 记录已处理的推文ID（无论通过与否都记录，防止重复处理）
        for tweet in tweets:
            self.processed_ids.add(tweet['id'])
        self._save_processed_ids()

        # 保存博主统计
        self._save_author_stats()

        self.logger.info(f"分析完成: {len(passed_tweets)}/{len(tweets)} 条推文通过")

        # 保存被拒绝的推文
        if rejected_tweets:
            rejected_file = input_file.replace('/raw/', '/rejected/analyzer_')
            rejected_data = {
                **data,
                'tweets': rejected_tweets,
                'rejection_stats': {
                    'total': len(tweets),
                    'rejected': len(rejected_tweets),
                    'stage': 'content_analyzer'
                }
            }
            self.save_json(rejected_data, rejected_file)
            self.logger.info(f"保存被拒绝数据: {rejected_file}")

        if not passed_tweets:
            self.logger.info("无高价值AI内容")
            return None

        # 保存结果（直接到evaluated目录，跳过filtered）
        output_file = input_file.replace('/raw/', '/evaluated/')
        output_data = {
            **data,
            'tweets': passed_tweets,
            'analysis_stats': {
                'total': len(tweets),
                'passed': len(passed_tweets),
                'rejected': len(rejected_tweets),
                'pass_rate': len(passed_tweets) / len(tweets),
                'avg_value_score': sum(t['value']['score'] for t in passed_tweets) / len(passed_tweets)
            }
        }

        self.save_json(output_data, output_file)
        return output_file
