"""
生成模块 - 生成 Markdown 文件
"""

from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

from .base import BaseModule


class Generator(BaseModule):
    """Markdown 生成模块"""

    def __init__(self, config_path: str = "config/generator.yaml"):
        super().__init__(config_path)
        self.include_metadata = self.config.get('include_metadata', True)
        self.include_links = self.config.get('include_links', True)

    def _group_by_category(self, tweets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按分类分组"""
        grouped = defaultdict(list)
        for tweet in tweets:
            category = tweet['classification']['category']
            grouped[category].append(tweet)
        return dict(grouped)

    def _get_category_emoji(self, category: str) -> str:
        """获取分类 emoji"""
        emoji_map = {
            '时闻': '🔥',
            '深度解析': '💡',
            '技术技巧': '🛠',
            '学术研究': '📚',
            '产品应用': '🎯',
            '商业洞察': '💼',
        }
        return emoji_map.get(category, '📌')

    def _generate_tweet_section(self, tweet: Dict[str, Any], index: int) -> str:
        """生成单条推文的 Markdown 片段"""
        cls = tweet['classification']
        value = tweet['value']
        user = tweet['user']

        lines = [
            f"### {index}. {cls['summary']}\n",
            f"- **来源**: [@{user['username']}]({tweet['url']}) ({user['displayname']})",
            f"- **时间**: {tweet['date'][:19].replace('T', ' ')}",
            f"- **价值评分**: {value['score']}/10",
        ]

        if self.include_links:
            lines.append(f"- **原文**: {tweet['url']}")

        if cls.get('key_points'):
            lines.append("\n**要点**:")
            for point in cls['key_points']:
                lines.append(f"  - {point}")

        # 原文内容（折叠）
        lines.append("\n<details>")
        lines.append("<summary>查看原文</summary>\n")
        lines.append(f"{tweet['content']}\n")
        lines.append("</details>\n")

        return "\n".join(lines)

    def _generate_markdown(self, data: Dict[str, Any]) -> str:
        """生成完整的 Markdown"""
        tweets = data['tweets']
        fetch_time = data.get('fetch_time', datetime.now().isoformat())

        # 元数据
        lines = []
        if self.include_metadata:
            lines.extend([
                "---",
                f"generated_at: {datetime.now().isoformat()}",
                f"source_list: MY AI LIST",
                f"tweet_count: {len(tweets)}",
                f"period: {fetch_time[:13]}:00 - {fetch_time[:13]}:59",
                "---\n",
            ])

        # 标题
        period_str = fetch_time[:13].replace('T', ' ')
        lines.append(f"# AI 资讯摘要 ({period_str}:00)\n")

        # 统计信息
        if data.get('category_stats'):
            lines.append("## 📊 本期统计\n")
            for cat, count in data['category_stats'].items():
                emoji = self._get_category_emoji(cat)
                lines.append(f"- {emoji} {cat}: {count} 条")
            lines.append("")

        # 按分类组织内容
        grouped = self._group_by_category(tweets)

        for category in ['时闻', '深度解析', '技术技巧', '学术研究', '产品应用', '商业洞察']:
            if category not in grouped:
                continue

            cat_tweets = grouped[category]
            emoji = self._get_category_emoji(category)

            lines.append(f"\n## {emoji} {category} ({len(cat_tweets)}条)\n")

            # 按价值分数排序
            sorted_tweets = sorted(
                cat_tweets,
                key=lambda t: t['value']['score'],
                reverse=True
            )

            for i, tweet in enumerate(sorted_tweets, 1):
                lines.append(self._generate_tweet_section(tweet, i))

        # 页脚
        lines.extend([
            "\n---",
            "\n🤖 本文由 AI 推文抓取系统自动生成",
            f"\n📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])

        return "\n".join(lines)

    def run(self, input_file: str) -> str:
        """
        运行生成

        Args:
            input_file: 输入文件路径 (data/classified/xxx.json)

        Returns:
            输出文件路径
        """
        # 加载输入数据
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        self.logger.info(f"开始生成 Markdown，共 {len(data['tweets'])} 条推文")

        # 生成 Markdown
        markdown = self._generate_markdown(data)

        # 保存文件
        output_file = input_file.replace('/classified/', '/output/').replace('.json', '.md')

        from pathlib import Path
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        self.logger.info(f"Markdown 已生成: {output_file}")
        return output_file
