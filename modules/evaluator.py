"""评估模块 - 判断内容价值"""

import json
from typing import Any, Optional

from google import genai
from google.genai import types
from openai import OpenAI

from .base import BaseModule

DEFAULT_EVALUATION = {
    'score': 5,
    'dimensions': {},
    'reason': ''
}


class Evaluator(BaseModule):
    """内容价值评估模块"""

    def __init__(self, config_path: str = "config/evaluator.yaml") -> None:
        super().__init__(config_path)
        self.threshold = self.config['value_threshold']
        self.provider = self.config.get('llm_provider', 'openai')
        self.model = self.config['llm_model']
        self.auto_filter_config = self.config.get('auto_filter', {})

        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])
        else:
            self.client = OpenAI(api_key=self.config['openai_api_key'])

    def _auto_filter(self, tweet: dict[str, Any]) -> bool:
        """自动过滤低质量内容，True 表示需要过滤"""
        content = tweet['content']

        min_length = self.auto_filter_config.get('min_content_length', 10)
        if len(content) < min_length:
            self.logger.debug(f"内容太短: {tweet['id_str']}")
            return True

        if self.auto_filter_config.get('filter_pure_retweet', True):
            if tweet.get('isRetweet') and len(content) < 20:
                self.logger.debug(f"纯转发: {tweet['id_str']}")
                return True

        return False

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
                    {"role": "system", "content": "你是一个专业的内容价值评估专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

    def _evaluate_value(self, tweet: dict[str, Any]) -> dict[str, Any]:
        """评估内容价值"""
        user = tweet['user']

        prompt = f"""评估以下 AI 相关推文的内容价值。

作者: @{user['username']} (粉丝: {user['followers']})
内容:
{tweet['content']}

互动数据:
- 回复: {tweet['replyCount']}
- 转发: {tweet['retweetCount']}
- 点赞: {tweet['likeCount']}

请从以下5个维度评分（每个维度 1-10 分）：
1. **原创性 (Originality)**: 是原创内容还是转发/搬运？
2. **信息量 (Information)**: 是否包含实质性信息？
3. **深度 (Depth)**: 是浅层讨论还是深度分析？
4. **时效性 (Timeliness)**: 是新鲜资讯还是旧闻？
5. **可操作性 (Actionable)**: 读者能从中获得什么实用价值？

综合评分：1-10 分
- 8-10: 高价值，必须保留
- 5-7:  中等价值，值得保留
- 1-4:  低价值，可以过滤

请以 JSON 格式回复：
{{
  "score": 综合评分,
  "dimensions": {{
    "originality": 分数,
    "information": 分数,
    "depth": 分数,
    "timeliness": 分数,
    "actionable": 分数
  }},
  "reason": "简短说明评分理由"
}}"""

        try:
            return json.loads(self._call_llm(prompt))
        except Exception as e:
            self.logger.error(f"评估失败: {e}")
            return {**DEFAULT_EVALUATION, 'reason': f'Error: {e}'}

    def _evaluate_tweet(self, tweet: dict[str, Any]) -> Optional[dict[str, Any]]:
        """评估单条推文，返回添加了 value 字段的推文或 None"""
        if self._auto_filter(tweet):
            return None

        result = self._evaluate_value(tweet)

        if result['score'] < self.threshold:
            self.logger.debug(f"价值过低: {tweet['id_str']}, score={result['score']}")
            return None

        tweet['value'] = result
        return tweet

    def run(self, input_file: str) -> Optional[str]:
        """运行评估"""
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        tweets = data['tweets']
        self.logger.info(f"开始评估 {len(tweets)} 条推文")

        evaluated_tweets = []
        rejected_tweets = []

        for i, tweet in enumerate(tweets, 1):
            if i % 5 == 0:
                self.logger.info(f"处理进度: {i}/{len(tweets)}")

            evaluated = self._evaluate_tweet(tweet)
            if evaluated:
                evaluated_tweets.append(evaluated)
            else:
                rejected_tweets.append(tweet)

        self.logger.info(f"评估完成: {len(evaluated_tweets)}/{len(tweets)} 条推文通过")

        if rejected_tweets:
            rejected_file = input_file.replace('/filtered/', '/rejected/evaluator_')
            self.save_json({
                **data,
                'tweets': rejected_tweets,
                'rejection_stats': {
                    'total': len(tweets),
                    'rejected': len(rejected_tweets),
                    'stage': 'evaluator'
                }
            }, rejected_file)
            self.logger.info(f"保存被拒绝数据: {rejected_file}")

        if not evaluated_tweets:
            self.logger.info("无高价值内容")
            return None

        output_file = input_file.replace('/filtered/', '/evaluated/')
        self.save_json({
            **data,
            'tweets': evaluated_tweets,
            'eval_stats': {
                'total': len(tweets),
                'evaluated': len(evaluated_tweets),
                'rejected': len(rejected_tweets),
                'ratio': len(evaluated_tweets) / len(tweets),
                'avg_score': sum(t['value']['score'] for t in evaluated_tweets) / len(evaluated_tweets)
            }
        }, output_file)

        return output_file
