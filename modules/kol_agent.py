"""KOL识别Agent - 自动识别重要KOL，避免误判"""

import json
from typing import Any, Optional

from google import genai
from google.genai import types

from .base import BaseModule

DEFAULT_KOL_RESULT = {
    'is_important_kol': False,
    'confidence': 0,
    'reason': '',
    'background': '',
    'recommendation': 'watch'
}


class KOLAgent(BaseModule):
    """
    KOL识别Agent

    触发条件：高粉丝(10万+) + 低通过率(<30%) + 样本不足
    功能：通过搜索调研博主背景，判断是否为重要KOL
    """

    def __init__(self, config_path: str = "config/kol_agent.yaml") -> None:
        super().__init__(config_path)
        self.provider = self.config.get('llm_provider', 'gemini')
        self.model = self.config.get('llm_model', 'gemini-2.5-flash')

        self.min_followers = self.config.get('min_followers', 100000)
        self.max_pass_rate = self.config.get('max_pass_rate', 0.3)
        self.max_tweets = self.config.get('max_tweets', 10)

        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])

    def should_check(self, author_stats: dict[str, Any]) -> bool:
        """判断是否需要检查该博主（高粉丝 + 低通过率 + 样本不足）"""
        followers = author_stats.get('followers', 0)
        total_tweets = author_stats.get('total_tweets', 0)
        passed_tweets = author_stats.get('passed_tweets', 0)
        pass_rate = passed_tweets / total_tweets if total_tweets > 0 else 0

        return (
            followers >= self.min_followers and
            pass_rate <= self.max_pass_rate and
            total_tweets <= self.max_tweets
        )

    def identify(self, username: str, displayname: str, followers: int) -> dict[str, Any]:
        """识别博主是否为重要KOL"""
        prompt = f"""你是一个AI/科技领域的KOL识别专家。请分析以下Twitter用户是否为重要的AI/科技领域KOL。

用户信息：
- 用户名: @{username}
- 显示名: {displayname}
- 粉丝数: {followers:,}

请基于你的知识判断这个用户：
1. 是否是AI/科技领域的重要人物（如公司创始人、核心开发者、知名研究员、投资人等）
2. 他们的主要身份和成就
3. 是否应该保留在AI资讯关注列表中

已知的重要KOL示例：
- @bchesky (Airbnb CEO)
- @elonmusk (Tesla/SpaceX/xAI CEO)
- @sama (OpenAI CEO)
- @ClementDelangue (Hugging Face CEO)
- @kaborez (AI研究员)

请返回JSON格式：
{{
  "is_important_kol": true/false,
  "confidence": 0.0-1.0,
  "reason": "判断理由（1-2句话）",
  "background": "用户背景简介",
  "recommendation": "keep/watch/remove"
}}

recommendation说明：
- keep: 确定是重要KOL，应保留
- watch: 可能重要但不确定，继续观察
- remove: 确定不是重要KOL，可考虑移除"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type='application/json'
                )
            )
            result = json.loads(response.text.strip())
            self.logger.info(
                f"KOL识别 @{username}: {result.get('recommendation')} - {result.get('reason')}"
            )
            return result

        except Exception as e:
            self.logger.error(f"KOL识别失败 @{username}: {e}")
            return {**DEFAULT_KOL_RESULT, 'reason': f'识别失败: {e}'}

    def batch_identify(self, authors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """批量识别多个可疑博主"""
        results = {}
        for author in authors:
            if not self.should_check(author):
                continue

            results[author['username']] = self.identify(
                username=author['username'],
                displayname=author.get('displayname', ''),
                followers=author.get('followers', 0)
            )
        return results

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """Agent不需要文件输入输出，请使用 identify() 或 batch_identify()"""
        self.logger.info("KOLAgent 不支持 run() 方法，请使用 identify() 或 batch_identify()")
        return None
