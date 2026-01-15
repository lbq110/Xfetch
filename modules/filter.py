"""过滤模块 - 判断推文是否与 AI 相关"""

import json
from typing import Any, Optional

from google import genai
from google.genai import types
from openai import OpenAI

from .base import BaseModule

DEFAULT_FILTER_RESULT = {
    'is_relevant': False,
    'score': 0,
    'reason': ''
}


class Filter(BaseModule):
    """AI 相关性过滤模块"""

    def __init__(self, config_path: str = "config/filter.yaml") -> None:
        super().__init__(config_path)
        self.keywords = self.config['keywords']
        self.threshold = self.config['relevance_threshold']
        self.provider = self.config.get('llm_provider', 'openai')
        self.model = self.config['llm_model']

        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])
        else:
            self.client = OpenAI(api_key=self.config['openai_api_key'])

    def _keyword_filter(self, content: str) -> bool:
        """第一层：关键词快速过滤，True 表示可能相关"""
        content_lower = content.lower()
        return any(kw.lower() in content_lower for kw in self.keywords)

    def _call_llm(self, prompt: str) -> str:
        """调用LLM获取JSON响应"""
        if self.provider == 'gemini':
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type='application/json'
                )
            )
            return response.text.strip()
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的 AI 内容分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

    def _llm_filter(self, content: str) -> dict[str, Any]:
        """第二层：LLM 判断相关性"""
        prompt = f"""判断以下推文内容是否与人工智能(AI)相关。

推文内容:
{content}

请分析：
1. 这条推文是否讨论 AI、机器学习、大模型、或相关技术？
2. 相关性评分 (0-100分，0表示完全无关，100表示高度相关)
3. 简短说明判断理由

请以 JSON 格式回复：
{{
  "is_relevant": true/false,
  "score": 分数,
  "reason": "理由"
}}"""

        try:
            return json.loads(self._call_llm(prompt))
        except Exception as e:
            self.logger.error(f"LLM 调用失败: {e}")
            return {**DEFAULT_FILTER_RESULT, 'reason': f'Error: {e}'}

    def _filter_tweet(self, tweet: dict[str, Any]) -> Optional[dict[str, Any]]:
        """过滤单条推文，返回添加了 relevance 字段的推文或 None"""
        content = tweet['content']

        if not self._keyword_filter(content):
            self.logger.debug(f"关键词过滤: {tweet['id_str']}")
            return None

        result = self._llm_filter(content)

        if not result['is_relevant'] or result['score'] < self.threshold:
            self.logger.debug(f"LLM 过滤: {tweet['id_str']}, score={result['score']}")
            return None

        tweet['relevance'] = {'score': result['score'], 'reason': result['reason']}
        return tweet

    def run(self, input_file: str) -> Optional[str]:
        """运行过滤"""
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        tweets = data['tweets']
        self.logger.info(f"开始过滤 {len(tweets)} 条推文")

        filtered_tweets = []
        rejected_tweets = []

        for i, tweet in enumerate(tweets, 1):
            if i % 10 == 0:
                self.logger.info(f"处理进度: {i}/{len(tweets)}")

            filtered = self._filter_tweet(tweet)
            if filtered:
                filtered_tweets.append(filtered)
            else:
                rejected_tweets.append(tweet)

        self.logger.info(f"过滤完成: {len(filtered_tweets)}/{len(tweets)} 条推文通过")

        if rejected_tweets:
            rejected_file = input_file.replace('/raw/', '/rejected/filter_')
            self.save_json({
                **data,
                'tweets': rejected_tweets,
                'rejection_stats': {
                    'total': len(tweets),
                    'rejected': len(rejected_tweets),
                    'stage': 'filter'
                }
            }, rejected_file)
            self.logger.info(f"保存被拒绝数据: {rejected_file}")

        if not filtered_tweets:
            self.logger.info("无相关推文")
            return None

        output_file = input_file.replace('/raw/', '/filtered/')
        self.save_json({
            **data,
            'tweets': filtered_tweets,
            'filter_stats': {
                'total': len(tweets),
                'filtered': len(filtered_tweets),
                'rejected': len(rejected_tweets),
                'ratio': len(filtered_tweets) / len(tweets)
            }
        }, output_file)

        return output_file
