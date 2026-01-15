"""
分类模块 - 对内容进行分类
"""

from typing import Dict, Any, List
from openai import OpenAI
from google import genai
from google.genai import types

from .base import BaseModule


class Classifier(BaseModule):
    """内容分类模块"""

    def __init__(self, config_path: str = "config/classifier.yaml"):
        super().__init__(config_path)
        self.categories = self.config['categories']
        self.provider = self.config.get('llm_provider', 'openai')
        self.model = self.config['llm_model']

        # 初始化 LLM 客户端
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

    def _classify_tweet(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        分类单条推文

        Returns:
            {
                'category': str,
                'sub_category': str,
                'summary': str,
                'key_points': List[str]
            }
        """
        content = tweet['content']
        user = tweet['user']

        category_info = self._build_category_prompt()

        prompt = f"""对以下 AI 推文进行分类和摘要。

{category_info}

作者: @{user['username']}
内容:
{content}

任务：
1. 选择最合适的**主分类**和**子分类**
2. 生成简洁的**摘要**（50-100字）
3. 提取 **2-4 个关键要点**

请以 JSON 格式回复：
{{
  "category": "分类名称（仅填写名称，不要包含emoji，如：时闻、深度解析、技术技巧等）",
  "sub_category": "子分类名称",
  "summary": "内容摘要",
  "key_points": ["要点1", "要点2", "要点3"]
}}"""

        try:
            import json

            if self.provider == 'gemini':
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type='application/json'
                    )
                )
                text = response.text.strip()
                result = json.loads(text)
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的 AI 内容分类专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)

            return result

        except Exception as e:
            self.logger.error(f"分类失败: {e}")
            return {
                'category': '其他',
                'sub_category': '未分类',
                'summary': content[:100],
                'key_points': []
            }

    def run(self, input_file: str) -> str:
        """
        运行分类

        Args:
            input_file: 输入文件路径 (data/evaluated/xxx.json)

        Returns:
            输出文件路径
        """
        # 加载输入数据
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        tweets = data['tweets']
        self.logger.info(f"开始分类 {len(tweets)} 条推文")

        # 分类推文
        for i, tweet in enumerate(tweets, 1):
            if i % 5 == 0:
                self.logger.info(f"处理进度: {i}/{len(tweets)}")

            classification = self._classify_tweet(tweet)
            tweet['classification'] = classification

        self.logger.info("分类完成")

        # 统计各分类数量
        category_counts = {}
        for tweet in tweets:
            cat = tweet['classification']['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        self.logger.info(f"分类统计: {category_counts}")

        # 保存结果
        output_file = input_file.replace('/evaluated/', '/classified/')
        output_data = {
            **data,
            'tweets': tweets,
            'category_stats': category_counts
        }

        self.save_json(output_data, output_file)
        return output_file
