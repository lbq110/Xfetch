"""分类模块 - 对内容进行分类"""

import json
from typing import Any, Optional

from google import genai
from google.genai import types
from openai import OpenAI

from .base import BaseModule

DEFAULT_CLASSIFICATION = {
    'category': '其他',
    'sub_category': '未分类',
    'summary': '',
    'key_points': []
}


class Classifier(BaseModule):
    """内容分类模块 - 支持批量处理"""

    def __init__(self, config_path: str = "config/classifier.yaml") -> None:
        super().__init__(config_path)
        self.categories = self.config['categories']
        self.provider = self.config.get('llm_provider', 'openai')
        self.model = self.config['llm_model']
        self.batch_size = self.config.get('batch_size', 5)

        if self.provider == 'gemini':
            self.client = genai.Client(api_key=self.config['gemini_api_key'])
        else:
            self.client = OpenAI(api_key=self.config['openai_api_key'])

    def _build_category_prompt(self) -> str:
        """构建分类体系描述"""
        lines = ["分类体系：\n"]
        for cat in self.categories:
            lines.append(f"{cat['emoji']} **{cat['name']}**: {cat['description']}")
            lines.append(f"  子分类: {', '.join(cat['sub_categories'])}\n")
        return "\n".join(lines)

    def _call_llm(self, prompt: str, system_prompt: str = "你是一个专业的AI内容分类专家。") -> str:
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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

    def _classify_batch(self, tweets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量分类多条推文"""
        if not tweets:
            return []

        category_info = self._build_category_prompt()

        tweets_text = []
        for i, tweet in enumerate(tweets, 1):
            user = tweet['user']
            tweets_text.append(
                f"【推文{i}】\n作者: @{user['username']}\n内容: {tweet['content'][:500]}"
            )

        prompt = f"""对以下{len(tweets)}条AI推文进行批量分类和摘要。

{category_info}

{chr(10).join(tweets_text)}

任务：
1. 为每条推文选择最合适的**主分类**和**子分类**
2. 生成简洁的**摘要**（50-100字）
3. 提取**2-4个关键要点**

请返回JSON数组，每条对应一个结果：
[
  {{"id": 1, "category": "分类名称", "sub_category": "子分类", "summary": "摘要", "key_points": ["要点1", "要点2"]}},
  ...
]

注意：category只填写名称，不要包含emoji（如：时闻、深度解析、技术技巧等）"""

        try:
            results = json.loads(self._call_llm(prompt))

            while len(results) < len(tweets):
                self.logger.warning(
                    f"批量结果数量不匹配: 期望{len(tweets)}, 得到{len(results)}"
                )
                results.append({
                    **DEFAULT_CLASSIFICATION,
                    'summary': tweets[len(results)]['content'][:100]
                })

            return results

        except Exception as e:
            self.logger.error(f"批量分类失败: {e}")
            return [
                {**DEFAULT_CLASSIFICATION, 'summary': tweet['content'][:100]}
                for tweet in tweets
            ]

    def run(self, input_file: str) -> Optional[str]:
        """运行分类（批量处理）"""
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        tweets = data['tweets']
        self.logger.info(f"开始分类 {len(tweets)} 条推文 (批量大小: {self.batch_size})")

        for batch_start in range(0, len(tweets), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(tweets))
            batch = tweets[batch_start:batch_end]

            self.logger.info(f"处理批次: {batch_start + 1}-{batch_end}/{len(tweets)}")
            results = self._classify_batch(batch)

            for tweet, classification in zip(batch, results):
                tweet['classification'] = classification

        self.logger.info("分类完成")

        category_counts = {}
        for tweet in tweets:
            cat = tweet['classification']['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        self.logger.info(f"分类统计: {category_counts}")

        output_file = input_file.replace('/evaluated/', '/classified/')
        self.save_json({**data, 'tweets': tweets, 'category_stats': category_counts}, output_file)

        return output_file
