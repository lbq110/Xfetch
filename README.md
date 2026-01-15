# Xfetch

AI 推文抓取与分析系统 - 从 Twitter List 抓取推文，自动筛选 AI 相关高价值内容，生成结构化报告。

## 功能特点

- **增量抓取**: 只抓取新推文，避免重复处理
- **智能分析**: 一次 LLM 调用同时判断 AI 相关性和内容价值
- **虚假信息检测**: 自动识别不存在的 AI 模型等可疑内容
- **博主质量追踪**: 记录博主通过率，识别低质量信息源
- **自动分类**: 将内容分类为时闻、技术技巧、深度解析等类别
- **Markdown 报告**: 生成结构化的 Markdown 文件

## 系统架构

```
Pipeline v2:
┌─────────┐    ┌──────────────────┐    ┌────────────┐    ┌───────────┐
│ Fetcher │ -> │ ContentAnalyzer  │ -> │ Classifier │ -> │ Generator │
└─────────┘    └──────────────────┘    └────────────┘    └───────────┘
     │                  │
     v                  v
 state.json      processed_ids.json
                 author_stats.json
```

## 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/Xfetch.git
cd Xfetch

# 安装依赖
pip install -r requirements.txt

# 复制配置文件模板
cp config/fetcher.yaml.example config/fetcher.yaml
cp config/content_analyzer.yaml.example config/content_analyzer.yaml
cp config/classifier.yaml.example config/classifier.yaml
cp config/generator.yaml.example config/generator.yaml

# 编辑配置文件，填入你的 API Key 和 Twitter List ID
```

## 配置

### Twitter 账户设置

使用 [twscrape](https://github.com/vladkens/twscrape) 进行推文抓取，需要配置 Twitter 账户:

```bash
# 添加账户（推荐使用 cookies 方式）
python -c "
import asyncio
from twscrape import API
api = API('accounts.db')
asyncio.run(api.pool.add_account('username', 'password', 'email', 'email_password'))
asyncio.run(api.pool.login_all())
"
```

### API Key 配置

在 `config/content_analyzer.yaml` 和 `config/classifier.yaml` 中配置 Gemini API Key:

```yaml
gemini_api_key: YOUR_GEMINI_API_KEY
```

## 使用

```bash
# 运行完整管道
python run.py --run

# 使用指定数据文件（跳过抓取）
python run.py --input data/raw/xxx.json

# 查看博主质量报告
python run.py --author-report

# 指定最小推文数
python run.py --author-report --min-tweets 5
```

## 目录结构

```
Xfetch/
├── config/                 # 配置文件
│   ├── *.yaml.example     # 配置模板
│   └── *.yaml             # 实际配置（不提交）
├── data/                   # 数据目录
│   ├── raw/               # 原始推文
│   ├── evaluated/         # 分析后的推文
│   ├── classified/        # 分类后的推文
│   ├── rejected/          # 被过滤的推文
│   ├── output/            # 生成的 Markdown
│   ├── state.json         # 抓取状态
│   ├── author_stats.json  # 博主统计
│   └── processed_ids.json # 已处理推文ID
├── modules/               # 核心模块
│   ├── base.py           # 基类
│   ├── fetcher.py        # 抓取模块
│   ├── content_analyzer.py # 内容分析（合并 Filter + Evaluator）
│   ├── classifier.py     # 分类模块
│   └── generator.py      # 报告生成
├── twscrape/             # Twitter 抓取库
├── pipeline.py           # 管道调度器
├── run.py               # 入口脚本
└── requirements.txt     # 依赖
```

## 博主质量报告示例

```
📊 博主质量报告
======================================================================
统计摘要:
  总博主数: 14
  高质量博主: 8
  低质量博主: 5
  建议移除: 2

✅ 高质量博主 (通过率≥70%):
  @minchoi       通过率:100%  平均分:9.0
  @huggingface   通过率:100%  平均分:8.0

⚠️ 建议移除的博主:
  @spammer123    通过率:0%   近期平均:1.0
```

## License

MIT
