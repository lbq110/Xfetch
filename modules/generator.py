"""生成模块 - 生成 Markdown 文件"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import BaseModule

CATEGORY_EMOJI = {
    '时闻': '\U0001F525',
    '深度解析': '\U0001F4A1',
    '技术技巧': '\U0001F6E0',
    '学术研究': '\U0001F4DA',
    '产品应用': '\U0001F3AF',
    '商业洞察': '\U0001F4BC',
}

CATEGORY_ORDER = ['时闻', '深度解析', '技术技巧', '学术研究', '产品应用', '商业洞察']


class Generator(BaseModule):
    """Markdown 生成模块"""

    def __init__(self, config_path: str = "config/generator.yaml") -> None:
        super().__init__(config_path)
        self.include_metadata = self.config.get('include_metadata', True)
        self.include_links = self.config.get('include_links', True)

    def _group_by_category(self, tweets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """按分类分组"""
        grouped = defaultdict(list)
        for tweet in tweets:
            grouped[tweet['classification']['category']].append(tweet)
        return dict(grouped)

    def _generate_tweet_section(self, tweet: dict[str, Any], index: int) -> str:
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
            lines.extend(f"  - {point}" for point in cls['key_points'])

        lines.extend([
            "\n<details>",
            "<summary>查看原文</summary>\n",
            f"{tweet['content']}\n",
            "</details>\n"
        ])

        return "\n".join(lines)

    def _generate_markdown(self, data: dict[str, Any]) -> str:
        """生成完整的 Markdown"""
        tweets = data['tweets']
        fetch_time = data.get('fetch_time', datetime.now().isoformat())

        lines = []

        if self.include_metadata:
            lines.extend([
                "---",
                f"generated_at: {datetime.now().isoformat()}",
                "source_list: MY AI LIST",
                f"tweet_count: {len(tweets)}",
                f"period: {fetch_time[:13]}:00 - {fetch_time[:13]}:59",
                "---\n",
            ])

        period_str = fetch_time[:13].replace('T', ' ')
        lines.append(f"# AI 资讯摘要 ({period_str}:00)\n")

        if data.get('category_stats'):
            lines.append("## \U0001F4CA 本期统计\n")
            for cat, count in data['category_stats'].items():
                emoji = CATEGORY_EMOJI.get(cat, '\U0001F4CC')
                lines.append(f"- {emoji} {cat}: {count} 条")
            lines.append("")

        grouped = self._group_by_category(tweets)

        for category in CATEGORY_ORDER:
            if category not in grouped:
                continue

            cat_tweets = grouped[category]
            emoji = CATEGORY_EMOJI.get(category, '\U0001F4CC')

            lines.append(f"\n## {emoji} {category} ({len(cat_tweets)}条)\n")

            sorted_tweets = sorted(cat_tweets, key=lambda t: t['value']['score'], reverse=True)
            for i, tweet in enumerate(sorted_tweets, 1):
                lines.append(self._generate_tweet_section(tweet, i))

        lines.extend([
            "\n---",
            "\n\U0001F916 本文由 AI 推文抓取系统自动生成",
            f"\n\U0001F4C5 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])

        return "\n".join(lines)

    def run(self, input_file: str) -> Optional[str]:
        """运行生成"""
        data = self.load_json(input_file)
        if not data or 'tweets' not in data:
            self.logger.error("无效的输入文件")
            return None

        self.logger.info(f"开始生成 Markdown，共 {len(data['tweets'])} 条推文")

        markdown = self._generate_markdown(data)

        output_file = input_file.replace('/classified/', '/output/').replace('.json', '.md')
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        self.logger.info(f"Markdown 已生成: {output_file}")
        return output_file
