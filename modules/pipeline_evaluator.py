"""
Pipeline评估模块 - 评估Filter和Evaluator的准确性
"""

import json
import random
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime
from google import genai
from google.genai import types

from .base import BaseModule


class PipelineEvaluator(BaseModule):
    """Pipeline质量评估模块"""

    def __init__(self, config_path: str = "config/pipeline_evaluator.yaml"):
        super().__init__(config_path)
        self.sample_size = self.config.get('sample_size', 20)
        self.review_model = self.config.get('review_model', 'gemini-2.5-pro')

        # 使用更强的模型进行审查
        self.client = genai.Client(api_key=self.config['gemini_api_key'])

    def _re_evaluate_filter(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        用更强的模型重新评估Filter决策

        Returns:
            {
                'should_pass': bool,
                'confidence': int (0-100),
                'reason': str
            }
        """
        content = tweet['content']

        prompt = f"""请作为一个严格的AI内容审查专家，判断这条推文是否与人工智能相关。

推文内容：
{content}

评估标准：
- 必须明确讨论 AI、机器学习、大模型、或相关技术
- 仅仅提到AI产品名称（如ChatGPT）但不讨论技术内容的，不算相关
- 需要有实质性的AI相关信息，不是简单提及

请以JSON格式回复：
{{
  "should_pass": true/false,
  "confidence": 0-100的置信度,
  "reason": "判断理由（1句话）"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.review_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type='application/json'
                )
            )
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            self.logger.error(f"重新评估失败: {e}")
            return {'should_pass': False, 'confidence': 0, 'reason': f'Error: {str(e)}'}

    def _re_evaluate_evaluator(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """
        用更强的模型重新评估Evaluator决策

        Returns:
            {
                'should_pass': bool,
                'score': int (1-10),
                'reason': str
            }
        """
        content = tweet['content']
        user = tweet['user']

        prompt = f"""请作为一个严格的内容价值评估专家，评估这条AI推文的价值。

作者: @{user['username']} (粉丝: {user['followers']})
内容：
{content}

互动数据：
- 回复: {tweet['replyCount']}
- 转发: {tweet['retweetCount']}
- 点赞: {tweet['likeCount']}

评分标准（1-10分）：
- 8-10分: 高价值（原创深度分析、重要新闻、实用技巧）
- 5-7分: 中等价值（有一定信息量）
- 1-4分: 低价值（纯转发、无实质内容）

阈值：5分
- ≥5分：应该通过
- <5分：应该拒绝

请以JSON格式回复：
{{
  "should_pass": true/false,
  "score": 1-10的评分,
  "reason": "评分理由（1句话）"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.review_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type='application/json'
                )
            )
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            self.logger.error(f"重新评估失败: {e}")
            return {'should_pass': False, 'score': 0, 'reason': f'Error: {str(e)}'}

    def evaluate_filter_stage(self,
                              filter_rejected_file: str,
                              filter_passed_file: str) -> Dict[str, Any]:
        """
        评估Filter阶段的准确性

        Args:
            filter_rejected_file: 被Filter拒绝的推文文件
            filter_passed_file: 通过Filter的推文文件

        Returns:
            评估报告
        """
        self.logger.info("=" * 60)
        self.logger.info("开始评估 Filter 阶段")
        self.logger.info("=" * 60)

        # 加载数据
        rejected_data = self.load_json(filter_rejected_file)
        passed_data = self.load_json(filter_passed_file)

        if not rejected_data or not passed_data:
            self.logger.error("无法加载数据")
            return {}

        rejected_tweets = rejected_data['tweets']
        passed_tweets = passed_data['tweets']

        self.logger.info(f"Filter拒绝: {len(rejected_tweets)} 条")
        self.logger.info(f"Filter通过: {len(passed_tweets)} 条")

        # 抽样检查被拒绝的（查找假阴性）
        sample_size = min(self.sample_size, len(rejected_tweets))
        rejected_sample = random.sample(rejected_tweets, sample_size)

        self.logger.info(f"\n抽样检查被拒绝的推文（样本量: {sample_size}）...")

        false_negatives = []
        for i, tweet in enumerate(rejected_sample, 1):
            self.logger.info(f"  审查进度: {i}/{sample_size}")
            result = self._re_evaluate_filter(tweet)

            if result['should_pass']:
                false_negatives.append({
                    'tweet_id': tweet['id_str'],
                    'content': tweet['content'][:100] + '...',
                    'original_decision': 'REJECT',
                    'review_decision': 'PASS',
                    'confidence': result['confidence'],
                    'reason': result['reason']
                })

        # 抽样检查通过的（查找假阳性）
        sample_size_passed = min(self.sample_size, len(passed_tweets))
        passed_sample = random.sample(passed_tweets, sample_size_passed)

        self.logger.info(f"\n抽样检查通过的推文（样本量: {sample_size_passed}）...")

        false_positives = []
        for i, tweet in enumerate(passed_sample, 1):
            self.logger.info(f"  审查进度: {i}/{sample_size_passed}")
            result = self._re_evaluate_filter(tweet)

            if not result['should_pass']:
                false_positives.append({
                    'tweet_id': tweet['id_str'],
                    'content': tweet['content'][:100] + '...',
                    'original_decision': 'PASS',
                    'review_decision': 'REJECT',
                    'confidence': result['confidence'],
                    'reason': result['reason']
                })

        # 计算准确率
        false_negative_rate = len(false_negatives) / sample_size if sample_size > 0 else 0
        false_positive_rate = len(false_positives) / sample_size_passed if sample_size_passed > 0 else 0

        report = {
            'stage': 'Filter',
            'total_rejected': len(rejected_tweets),
            'total_passed': len(passed_tweets),
            'pass_rate': len(passed_tweets) / (len(rejected_tweets) + len(passed_tweets)),
            'sample_size_rejected': sample_size,
            'sample_size_passed': sample_size_passed,
            'false_negatives': {
                'count': len(false_negatives),
                'rate': false_negative_rate,
                'examples': false_negatives[:5]  # 只保存前5个例子
            },
            'false_positives': {
                'count': len(false_positives),
                'rate': false_positive_rate,
                'examples': false_positives[:5]
            },
            'estimated_accuracy': 1 - (false_negative_rate + false_positive_rate) / 2
        }

        return report

    def evaluate_evaluator_stage(self,
                                  evaluator_rejected_file: str,
                                  evaluator_passed_file: str) -> Dict[str, Any]:
        """
        评估Evaluator阶段的准确性

        Args:
            evaluator_rejected_file: 被Evaluator拒绝的推文文件
            evaluator_passed_file: 通过Evaluator的推文文件

        Returns:
            评估报告
        """
        self.logger.info("=" * 60)
        self.logger.info("开始评估 Evaluator 阶段")
        self.logger.info("=" * 60)

        # 加载数据
        rejected_data = self.load_json(evaluator_rejected_file)
        passed_data = self.load_json(evaluator_passed_file)

        if not rejected_data or not passed_data:
            self.logger.error("无法加载数据")
            return {}

        rejected_tweets = rejected_data['tweets']
        passed_tweets = passed_data['tweets']

        self.logger.info(f"Evaluator拒绝: {len(rejected_tweets)} 条")
        self.logger.info(f"Evaluator通过: {len(passed_tweets)} 条")

        # 收集原始评分分布
        rejected_scores = [t.get('value', {}).get('score', 0) for t in rejected_tweets]
        passed_scores = [t.get('value', {}).get('score', 0) for t in passed_tweets]

        # 抽样检查被拒绝的
        sample_size = min(self.sample_size, len(rejected_tweets))
        rejected_sample = random.sample(rejected_tweets, sample_size)

        self.logger.info(f"\n抽样检查被拒绝的推文（样本量: {sample_size}）...")

        false_negatives = []
        score_differences = []

        for i, tweet in enumerate(rejected_sample, 1):
            self.logger.info(f"  审查进度: {i}/{sample_size}")
            result = self._re_evaluate_evaluator(tweet)

            original_score = tweet.get('value', {}).get('score', 0)
            review_score = result['score']
            score_diff = review_score - original_score
            score_differences.append(score_diff)

            if result['should_pass']:
                false_negatives.append({
                    'tweet_id': tweet['id_str'],
                    'content': tweet['content'][:100] + '...',
                    'original_score': original_score,
                    'review_score': review_score,
                    'score_diff': score_diff,
                    'reason': result['reason']
                })

        # 抽样检查通过的
        sample_size_passed = min(self.sample_size, len(passed_tweets))
        passed_sample = random.sample(passed_tweets, sample_size_passed)

        self.logger.info(f"\n抽样检查通过的推文（样本量: {sample_size_passed}）...")

        false_positives = []

        for i, tweet in enumerate(passed_sample, 1):
            self.logger.info(f"  审查进度: {i}/{sample_size_passed}")
            result = self._re_evaluate_evaluator(tweet)

            original_score = tweet.get('value', {}).get('score', 0)
            review_score = result['score']
            score_diff = review_score - original_score
            score_differences.append(score_diff)

            if not result['should_pass']:
                false_positives.append({
                    'tweet_id': tweet['id_str'],
                    'content': tweet['content'][:100] + '...',
                    'original_score': original_score,
                    'review_score': review_score,
                    'score_diff': score_diff,
                    'reason': result['reason']
                })

        # 计算准确率
        false_negative_rate = len(false_negatives) / sample_size if sample_size > 0 else 0
        false_positive_rate = len(false_positives) / sample_size_passed if sample_size_passed > 0 else 0

        # 计算评分偏差
        avg_score_diff = sum(score_differences) / len(score_differences) if score_differences else 0

        report = {
            'stage': 'Evaluator',
            'total_rejected': len(rejected_tweets),
            'total_passed': len(passed_tweets),
            'pass_rate': len(passed_tweets) / (len(rejected_tweets) + len(passed_tweets)),
            'sample_size_rejected': sample_size,
            'sample_size_passed': sample_size_passed,
            'false_negatives': {
                'count': len(false_negatives),
                'rate': false_negative_rate,
                'examples': false_negatives[:5]
            },
            'false_positives': {
                'count': len(false_positives),
                'rate': false_positive_rate,
                'examples': false_positives[:5]
            },
            'estimated_accuracy': 1 - (false_negative_rate + false_positive_rate) / 2,
            'score_analysis': {
                'avg_score_diff': avg_score_diff,
                'interpretation': 'Pro审查模型平均给分更高' if avg_score_diff > 0 else 'Pro审查模型平均给分更低'
            }
        }

        return report

    def generate_optimization_suggestions(self,
                                         filter_report: Dict[str, Any],
                                         evaluator_report: Dict[str, Any]) -> List[str]:
        """
        基于评估报告生成优化建议
        """
        suggestions = []

        # Filter阶段建议
        filter_fn_rate = filter_report['false_negatives']['rate']
        filter_fp_rate = filter_report['false_positives']['rate']

        if filter_fn_rate > 0.3:
            suggestions.append(
                f"⚠️ Filter假阴性率过高({filter_fn_rate:.1%})：建议降低relevance_threshold阈值（当前60）或优化关键词列表"
            )

        if filter_fp_rate > 0.3:
            suggestions.append(
                f"⚠️ Filter假阳性率过高({filter_fp_rate:.1%})：建议提高relevance_threshold阈值或增强LLM判断prompt"
            )

        # Evaluator阶段建议
        eval_fn_rate = evaluator_report['false_negatives']['rate']
        eval_fp_rate = evaluator_report['false_positives']['rate']

        if eval_fn_rate > 0.3:
            suggestions.append(
                f"⚠️ Evaluator假阴性率过高({eval_fn_rate:.1%})：建议降低value_threshold阈值（当前5）"
            )

        if eval_fp_rate > 0.3:
            suggestions.append(
                f"⚠️ Evaluator假阳性率过高({eval_fp_rate:.1%})：建议提高value_threshold阈值或优化评估维度"
            )

        # 评分偏差建议
        score_diff = evaluator_report['score_analysis']['avg_score_diff']
        if abs(score_diff) > 1.5:
            suggestions.append(
                f"⚠️ 评分存在系统性偏差(平均差{score_diff:+.1f}分)：建议调整Evaluator的temperature参数或优化prompt"
            )

        # 流程优化建议
        filter_pass_rate = filter_report['pass_rate']
        eval_pass_rate = evaluator_report['pass_rate']
        total_pass_rate = filter_pass_rate * eval_pass_rate

        if filter_pass_rate < 0.2:
            suggestions.append(
                f"💡 Filter通过率过低({filter_pass_rate:.1%})：考虑放宽Filter条件，让更多内容进入Evaluator阶段"
            )

        if filter_pass_rate > 0.8 and eval_pass_rate < 0.3:
            suggestions.append(
                f"💡 Filter通过率高({filter_pass_rate:.1%})但Evaluator通过率低({eval_pass_rate:.1%})：建议加强Filter筛选，减少LLM成本"
            )

        if filter_fn_rate < 0.1 and eval_fn_rate < 0.1:
            suggestions.append(
                f"✅ 两阶段准确率都很高！考虑合并Filter和Evaluator为单一LLM调用，节省50%成本"
            )

        suggestions.append(
            f"📊 整体数据：最终通过率 {total_pass_rate:.1%}（Filter {filter_pass_rate:.1%} × Evaluator {eval_pass_rate:.1%}）"
        )

        return suggestions

    def run(self, raw_data_file: str) -> str:
        """
        运行完整的Pipeline评估

        Args:
            raw_data_file: 原始数据文件路径

        Returns:
            评估报告文件路径
        """
        from modules.filter import Filter
        from modules.evaluator import Evaluator

        self.logger.info("=" * 60)
        self.logger.info("Pipeline 评估开始")
        self.logger.info("=" * 60)

        # 第一步：运行Filter
        self.logger.info("\n第一步：运行 Filter 模块...")
        filter_module = Filter()
        filtered_file = filter_module.run(raw_data_file)

        if not filtered_file:
            self.logger.error("Filter阶段无输出，评估终止")
            return None

        # 第二步：运行Evaluator
        self.logger.info("\n第二步：运行 Evaluator 模块...")
        evaluator_module = Evaluator()
        evaluated_file = evaluator_module.run(filtered_file)

        if not evaluated_file:
            self.logger.error("Evaluator阶段无输出，评估终止")
            return None

        # 第三步：评估Filter
        filter_rejected_file = raw_data_file.replace('/raw/', '/rejected/filter_')
        filter_report = self.evaluate_filter_stage(filter_rejected_file, filtered_file)

        # 第四步：评估Evaluator
        evaluator_rejected_file = filtered_file.replace('/filtered/', '/rejected/evaluator_')
        evaluator_report = self.evaluate_evaluator_stage(evaluator_rejected_file, evaluated_file)

        # 第五步：生成优化建议
        self.logger.info("=" * 60)
        self.logger.info("生成优化建议")
        self.logger.info("=" * 60)
        suggestions = self.generate_optimization_suggestions(filter_report, evaluator_report)

        # 保存完整报告
        report = {
            'evaluation_time': datetime.now().isoformat(),
            'raw_data_file': raw_data_file,
            'filter_report': filter_report,
            'evaluator_report': evaluator_report,
            'optimization_suggestions': suggestions
        }

        output_file = raw_data_file.replace('/raw/', '/analysis/evaluation_')
        self.save_json(report, output_file)

        # 打印报告
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 评估报告摘要")
        self.logger.info("=" * 60)

        self.logger.info(f"\n【Filter 阶段】")
        self.logger.info(f"  总计: {filter_report['total_rejected'] + filter_report['total_passed']} 条")
        self.logger.info(f"  通过: {filter_report['total_passed']} 条 ({filter_report['pass_rate']:.1%})")
        self.logger.info(f"  拒绝: {filter_report['total_rejected']} 条")
        self.logger.info(f"  假阴性率: {filter_report['false_negatives']['rate']:.1%} ({filter_report['false_negatives']['count']}/{filter_report['sample_size_rejected']} 样本)")
        self.logger.info(f"  假阳性率: {filter_report['false_positives']['rate']:.1%} ({filter_report['false_positives']['count']}/{filter_report['sample_size_passed']} 样本)")
        self.logger.info(f"  估计准确率: {filter_report['estimated_accuracy']:.1%}")

        self.logger.info(f"\n【Evaluator 阶段】")
        self.logger.info(f"  总计: {evaluator_report['total_rejected'] + evaluator_report['total_passed']} 条")
        self.logger.info(f"  通过: {evaluator_report['total_passed']} 条 ({evaluator_report['pass_rate']:.1%})")
        self.logger.info(f"  拒绝: {evaluator_report['total_rejected']} 条")
        self.logger.info(f"  假阴性率: {evaluator_report['false_negatives']['rate']:.1%} ({evaluator_report['false_negatives']['count']}/{evaluator_report['sample_size_rejected']} 样本)")
        self.logger.info(f"  假阳性率: {evaluator_report['false_positives']['rate']:.1%} ({evaluator_report['false_positives']['count']}/{evaluator_report['sample_size_passed']} 样本)")
        self.logger.info(f"  估计准确率: {evaluator_report['estimated_accuracy']:.1%}")
        self.logger.info(f"  评分偏差: {evaluator_report['score_analysis']['interpretation']}")

        self.logger.info(f"\n【优化建议】")
        for suggestion in suggestions:
            self.logger.info(f"  {suggestion}")

        self.logger.info(f"\n完整报告已保存: {output_file}")

        return output_file
