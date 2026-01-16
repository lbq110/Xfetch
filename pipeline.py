"""管道调度器 - 协调各个模块运行 (v2 - 使用ContentAnalyzer)"""

import argparse
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Optional

from modules import Fetcher, Classifier, Generator
from modules.content_analyzer import ContentAnalyzer


class Pipeline:
    """
    管道调度器 (v2)

    流程:
    1. Fetcher - 抓取推文
    2. ContentAnalyzer - 分析内容（合并Filter+Evaluator，一次LLM调用）
    3. Classifier - 内容分类
    4. Generator - 生成Markdown

    相比v1的优势:
    - 4步流程替代5步
    - 单次LLM判断相关性+价值，节省API成本
    - 不依赖关键词列表，不会遗漏内容
    - 追踪博主质量评分
    """

    def __init__(self, emit_events: bool = False) -> None:
        self.logger = self._setup_logger()
        self.fetcher = Fetcher()
        self.analyzer = ContentAnalyzer()
        self.classifier = Classifier()
        self.generator = Generator()

        # 可视化事件发射器（可选）
        self.emitter = None
        if emit_events:
            from modules.event_emitter import EventEmitter, EventType
            self.emitter = EventEmitter()
            self.EventType = EventType

    def _emit(self, event_type: str, data: Optional[dict] = None) -> None:
        """安全地发射事件，emitter 不存在时什么都不做"""
        if self.emitter:
            self.emitter.emit(event_type, data)

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("Pipeline")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)

        return logger

    def _log_step(self, step: int, total: int, message: str) -> None:
        """记录步骤日志"""
        self.logger.info(f"\n[{step}/{total}] {message}")

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """运行完整管道"""
        start_time = datetime.now()
        separator = "=" * 70

        self.logger.info(separator)
        self.logger.info(f"管道启动 (v2): {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(separator)

        # 发射管道启动事件
        self._emit("pipeline_start", {
            "run_id": self.emitter.get_run_id() if self.emitter else None,
            "start_time": start_time.isoformat(),
            "analyzer_model": self.analyzer.config.get("llm_model", "unknown"),
            "classifier_model": self.classifier.config.get("llm_model", "unknown")
        })

        try:
            # 1. 抓取（或使用指定文件）
            self._emit("fetch_start", {"input_file": input_file})

            if input_file:
                self._log_step(1, 4, f"使用指定文件: {input_file}")
                raw_file = input_file
            else:
                self._log_step(1, 4, "抓取推文...")
                raw_file = self.fetcher.run()
                if not raw_file:
                    self.logger.info(">> 无新推文，流程结束")
                    self._emit("pipeline_done", {"status": "no_new_tweets"})
                    return None
            self.logger.info(f">> 数据文件: {raw_file}")

            # 读取原始推文数据用于事件
            tweets_data = self._load_tweets_for_events(raw_file)
            self._emit("fetch_done", {
                "file": raw_file,
                "count": len(tweets_data),
                "tweets": tweets_data
            })

            # 2. 内容分析
            self._log_step(2, 4, "分析内容（AI相关性 + 价值评估）...")
            self._emit("review_batch_start", {
                "total": len(tweets_data),
                "model": self.analyzer.config.get("llm_model", "unknown")
            })

            analyzed_file = self.analyzer.run(raw_file)
            if not analyzed_file:
                self.logger.info(">> 无高价值AI内容，流程结束")
                self._emit("pipeline_done", {"status": "no_valuable_content"})
                return None
            self.logger.info(f">> 分析完成: {analyzed_file}")

            # 读取分析结果，发送每条推文的审核事件
            analyzed_data = self._load_json(analyzed_file)
            passed_tweets = [t for t in analyzed_data.get("tweets", [])
                           if t.get("filter", {}).get("is_relevant", False)]

            # 为每条推文发送审核结果事件
            analyzed_tweet_ids = {str(t.get("id", "")) for t in analyzed_data.get("tweets", [])}
            passenger_count = 0
            for tweet_info in tweets_data:
                tweet_id = tweet_info["id"]
                is_passed = tweet_id in analyzed_tweet_ids

                # 查找分析结果
                analysis_result = {}
                for t in analyzed_data.get("tweets", []):
                    if str(t.get("id", "")) == tweet_id:
                        analysis_result = t.get("analysis", {})
                        break

                self._emit("review_result", {
                    "tweet_id": tweet_id,
                    "username": tweet_info["username"],
                    "passed": is_passed,
                    "score": analysis_result.get("value_score", 0),
                    "relevance_score": analysis_result.get("relevance_score", 0),
                    "reason": analysis_result.get("reason", "")
                })

                # 通过的推文上车
                if is_passed:
                    passenger_count += 1
                    self._emit("bus_boarding", {
                        "tweet_id": tweet_id,
                        "username": tweet_info["username"],
                        "passenger_count": passenger_count
                    })

            self._emit("review_done", {
                "total": len(tweets_data),
                "passed": len(passed_tweets),
                "rejected": len(tweets_data) - len(passed_tweets)
            })

            # 大巴出发
            self._emit("bus_depart", {
                "passenger_count": len(passed_tweets),
                "model": self.classifier.config.get("llm_model", "unknown")
            })

            # 3. 分类
            self._log_step(3, 4, "内容分类...")
            self._emit("classify_start", {
                "count": len(passed_tweets),
                "model": self.classifier.config.get("llm_model", "unknown")
            })

            classified_file = self.classifier.run(analyzed_file)
            if not classified_file:
                self.logger.info(">> 分类失败")
                self._emit("pipeline_error", {"stage": "classify", "error": "Classification failed"})
                return None
            self.logger.info(f">> 分类完成: {classified_file}")

            # 大巴到站
            self._emit("bus_arrive", {})

            # 读取分类结果，为每条推文发送分类事件
            classified_data = self._load_json(classified_file)
            category_map = {
                "时闻": {"id": "news", "color": "#ff6b6b"},
                "深度解析": {"id": "analysis", "color": "#ffd93d"},
                "技术技巧": {"id": "tips", "color": "#6bcb77"},
                "学术研究": {"id": "research", "color": "#4d96ff"},
                "产品应用": {"id": "product", "color": "#9d4edd"},
                "商业洞察": {"id": "business", "color": "#ff8c42"}
            }

            for tweet in classified_data.get("tweets", []):
                classification = tweet.get("classification", {})
                category = classification.get("category", "其他")
                cat_info = category_map.get(category, {"id": "other", "color": "#888888"})

                self._emit("classify_result", {
                    "tweet_id": str(tweet.get("id", "")),
                    "username": tweet.get("user", {}).get("username", "unknown"),
                    "category": category,
                    "sub_category": classification.get("sub_category", ""),
                    "building_id": cat_info["id"],
                    "building_color": cat_info["color"],
                    "summary": classification.get("summary", "")
                })

            self._emit("classify_done", {
                "category_stats": classified_data.get("category_stats", {})
            })

            # 4. 生成
            self._log_step(4, 4, "生成 Markdown...")
            self._emit("generate_start", {})

            output_file = self.generator.run(classified_file)
            if not output_file:
                self.logger.info(">> 生成失败")
                self._emit("pipeline_error", {"stage": "generate", "error": "Generation failed"})
                return None
            self.logger.info(f">> 生成完成: {output_file}")

            self._emit("generate_done", {"file": output_file})

            # 完成
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"\n{separator}")
            self.logger.info(f">> 管道完成！耗时: {duration:.1f} 秒")
            self.logger.info(f">> 输出文件: {output_file}")
            self.logger.info(separator)

            # 发射完成事件
            self._emit("pipeline_done", {
                "status": "success",
                "duration_ms": int(duration * 1000),
                "output_file": output_file,
                "stats": {
                    "total_tweets": len(tweets_data),
                    "passed_tweets": len(passed_tweets),
                    "category_stats": classified_data.get("category_stats", {})
                }
            })

            # 打印事件文件位置
            if self.emitter:
                self.logger.info(f">> 事件文件: {self.emitter.get_event_file()}")

            return output_file

        except Exception as e:
            self.logger.error(f"\n>> 管道执行失败: {e}")
            traceback.print_exc()
            self._emit("pipeline_error", {"error": str(e)})
            return None

    def _load_tweets_for_events(self, raw_file: str) -> list:
        """加载推文数据用于事件（只保留必要字段）"""
        try:
            data = self._load_json(raw_file)
            tweets = []
            for t in data.get("tweets", []):
                user = t.get("user", {})
                tweets.append({
                    "id": str(t.get("id", "")),
                    "username": user.get("username", "unknown"),
                    "displayname": user.get("displayname", ""),
                    "avatar": user.get("profileImageUrl", ""),
                    "content": t.get("content", "")[:100],  # 截断内容
                    "followers": user.get("followers", 0)
                })
            return tweets
        except Exception:
            return []

    def _load_json(self, file_path: str) -> dict:
        """加载 JSON 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def get_author_report(self, min_tweets: int = 3) -> dict:
        """获取博主质量报告"""
        return self.analyzer.get_author_report(min_tweets)

    def print_author_report(self, min_tweets: int = 5) -> None:
        """打印博主质量报告"""
        report = self.get_author_report(min_tweets)
        summary = report['summary']
        separator = "=" * 70

        print(f"\n{separator}")
        print("\U0001F4CA 博主质量报告")
        print(separator)

        print(f"\n统计摘要:")
        print(f"  总博主数: {summary['total_authors']}")
        print(f"  高质量博主: {summary['high_quality_count']}")
        print(f"  低质量博主: {summary['low_quality_count']}")
        print(f"  KOL识别数: {summary.get('identified_kols_count', 0)}")
        print(f"  建议移除: {summary['recommend_remove_count']}")

        if report['high_quality_authors']:
            print(f"\n>> 高质量博主 (通过率>=70%):")
            for author in report['high_quality_authors'][:10]:
                print(
                    f"  @{author['username']:20} 通过率:{author['pass_rate']:.0%} "
                    f"平均分:{author['avg_score']:.1f} ({author['total_tweets']}条)"
                )

        if report.get('identified_kols'):
            print(f"\n>> KOL识别结果:")
            for kol in report['identified_kols']:
                status = ">> 重要KOL" if kol['is_important_kol'] else "? 待观察"
                print(f"  @{kol['username']:20} [{status}] {kol['reason']}")
                if kol['background']:
                    print(f"    背景: {kol['background'][:60]}...")

        if report['recommend_remove']:
            print(f"\n>> 建议移除的博主 (通过率<=30% 且近期评分低):")
            for author in report['recommend_remove']:
                print(
                    f"  @{author['username']:20} 通过率:{author['pass_rate']:.0%} "
                    f"近期平均:{author['recent_avg_score']:.1f} ({author['total_tweets']}条)"
                )

        print(f"\n{separator}")


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description='AI Tweet Pipeline v2')
    parser.add_argument('--run', action='store_true', help='运行完整管道')
    parser.add_argument('--input', type=str, help='使用指定的原始数据文件')
    parser.add_argument('--author-report', action='store_true', help='生成博主质量报告')
    parser.add_argument('--min-tweets', type=int, default=3, help='博主报告的最小推文数')

    args = parser.parse_args()
    pipeline = Pipeline()

    if args.author_report:
        pipeline.print_author_report(args.min_tweets)
    elif args.run or args.input:
        result = pipeline.run(input_file=args.input)
        if result:
            print(f"\n>> 成功生成报告: {result}")
        else:
            print("\n>> 本次运行未生成报告")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
