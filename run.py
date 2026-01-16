#!/usr/bin/env python3
"""
AI 推文抓取系统 - 入口脚本 (v2)
"""

import argparse
from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(
        description='AI 推文抓取与处理系统 (v2)'
    )
    parser.add_argument(
        '--run',
        action='store_true',
        help='运行完整管道'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='使用指定的原始数据文件（跳过抓取）'
    )
    parser.add_argument(
        '--author-report',
        action='store_true',
        help='生成博主质量报告'
    )
    parser.add_argument(
        '--min-tweets',
        type=int,
        default=3,
        help='博主报告的最小推文数（默认3）'
    )
    parser.add_argument(
        '--emit-events',
        action='store_true',
        help='启用事件输出（用于可视化前端）'
    )

    args = parser.parse_args()

    # 创建 Pipeline，传入 emit_events 参数
    pipeline = Pipeline(emit_events=args.emit_events)

    if args.author_report:
        pipeline.print_author_report(args.min_tweets)
    elif args.run or args.input:
        result = pipeline.run(input_file=args.input)
        if result:
            print(f"\n✓ 报告已生成: {result}")
        else:
            print("\n✗ 本次运行未生成报告")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
