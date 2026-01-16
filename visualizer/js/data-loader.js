/**
 * 数据加载器 - 读取 JSONL 事件文件
 */

class DataLoader {
    constructor() {
        this.eventsDir = '../data/events/';
        this.events = [];
    }

    // 获取可用的事件文件列表
    async getAvailableFiles() {
        // 由于浏览器安全限制，无法直接列出目录
        // 需要一个 index.json 文件或通过 API 获取
        // 这里提供一个备选方案：尝试加载最近的文件

        // 如果有 index.json
        try {
            const response = await fetch(this.eventsDir + 'index.json');
            if (response.ok) {
                const data = await response.json();
                return data.files || [];
            }
        } catch (e) {
            console.log('No index.json found, using fallback');
        }

        // 备选：返回空列表，让用户手动输入
        return [];
    }

    // 加载 JSONL 文件
    async loadEventsFile(filename) {
        try {
            const url = this.eventsDir + filename;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Failed to load ${filename}: ${response.status}`);
            }

            const text = await response.text();
            this.events = this.parseJSONL(text);

            console.log(`Loaded ${this.events.length} events from ${filename}`);
            return this.events;
        } catch (error) {
            console.error('Error loading events:', error);
            throw error;
        }
    }

    // 解析 JSONL 格式
    parseJSONL(text) {
        const lines = text.trim().split('\n');
        const events = [];

        for (const line of lines) {
            if (line.trim()) {
                try {
                    events.push(JSON.parse(line));
                } catch (e) {
                    console.warn('Failed to parse line:', line);
                }
            }
        }

        return events;
    }

    // 从文本内容加载（用于文件输入）
    loadFromText(text) {
        this.events = this.parseJSONL(text);
        return this.events;
    }

    // 获取所有事件
    getEvents() {
        return this.events;
    }

    // 获取特定类型的事件
    getEventsByType(type) {
        return this.events.filter(e => e.type === type);
    }

    // 获取时间范围
    getTimeRange() {
        if (this.events.length === 0) {
            return { start: 0, end: 0, duration: 0 };
        }

        const start = this.events[0].elapsed_ms || 0;
        const end = this.events[this.events.length - 1].elapsed_ms || 0;

        return {
            start,
            end,
            duration: end - start
        };
    }

    // 获取管道配置
    getPipelineConfig() {
        const startEvent = this.events.find(e => e.type === 'pipeline_start');
        if (startEvent) {
            return startEvent.data || {};
        }
        return {};
    }

    // 获取最终统计
    getFinalStats() {
        const doneEvent = this.events.find(e => e.type === 'pipeline_done');
        if (doneEvent) {
            return doneEvent.data || {};
        }
        return {};
    }

    // 加载 Demo 数据
    loadDemoData() {
        this.events = this.generateDemoEvents();
        return this.events;
    }

    // 生成 Demo 事件
    generateDemoEvents() {
        const demoUsers = [
            { username: 'huggingface', displayname: 'Hugging Face', followers: 606412 },
            { username: 'OpenAI', displayname: 'OpenAI', followers: 3200000 },
            { username: 'AnthropicAI', displayname: 'Anthropic', followers: 280000 },
            { username: 'GoogleAI', displayname: 'Google AI', followers: 1500000 },
            { username: 'sama', displayname: 'Sam Altman', followers: 2800000 },
            { username: 'ylecun', displayname: 'Yann LeCun', followers: 750000 },
            { username: 'kaboreeee', displayname: 'Kamui', followers: 50000 },
            { username: 'random_user', displayname: 'Random User', followers: 1000 },
        ];

        const events = [];
        let elapsed = 0;

        // pipeline_start
        events.push({
            type: 'pipeline_start',
            data: {
                run_id: 'demo_' + Date.now(),
                analyzer_model: 'gemini-2.0-flash-lite',
                classifier_model: 'gemini-2.5-flash'
            },
            elapsed_ms: elapsed
        });

        elapsed += 100;

        // fetch_done
        const tweets = demoUsers.map((user, i) => ({
            id: `tweet_${i}`,
            username: user.username,
            displayname: user.displayname,
            avatar: '',
            content: `This is a demo tweet about AI and machine learning from @${user.username}. #AI #ML`,
            followers: user.followers
        }));

        events.push({
            type: 'fetch_done',
            data: { count: tweets.length, tweets },
            elapsed_ms: elapsed
        });

        elapsed += 500;

        // review_batch_start
        events.push({
            type: 'review_batch_start',
            data: { total: tweets.length, model: 'gemini-2.0-flash-lite' },
            elapsed_ms: elapsed
        });

        // review_result for each tweet
        tweets.forEach((tweet, i) => {
            elapsed += 300 + Math.random() * 200;
            const passed = Math.random() > 0.25; // 75% pass rate
            const score = passed ? Math.floor(Math.random() * 4) + 6 : Math.floor(Math.random() * 4) + 1;

            events.push({
                type: 'review_result',
                data: {
                    tweet_id: tweet.id,
                    username: tweet.username,
                    passed,
                    score,
                    relevance_score: passed ? 70 + Math.random() * 30 : 20 + Math.random() * 30,
                    reason: passed ? 'High quality AI content' : 'Not relevant or low quality'
                },
                elapsed_ms: elapsed
            });

            if (passed) {
                elapsed += 100;
                events.push({
                    type: 'bus_boarding',
                    data: {
                        tweet_id: tweet.id,
                        username: tweet.username,
                        passenger_count: events.filter(e => e.type === 'bus_boarding').length + 1
                    },
                    elapsed_ms: elapsed
                });
            }
        });

        // review_done
        const passedCount = events.filter(e => e.type === 'bus_boarding').length;
        events.push({
            type: 'review_done',
            data: { total: tweets.length, passed: passedCount, rejected: tweets.length - passedCount },
            elapsed_ms: elapsed
        });

        elapsed += 200;

        // bus_depart
        events.push({
            type: 'bus_depart',
            data: { passenger_count: passedCount, model: 'gemini-2.5-flash' },
            elapsed_ms: elapsed
        });

        elapsed += 5000; // 5 seconds travel

        // bus_arrive
        events.push({
            type: 'bus_arrive',
            data: {},
            elapsed_ms: elapsed
        });

        elapsed += 50; // 立即开始分类

        // classify_start
        events.push({
            type: 'classify_start',
            data: { count: passedCount },
            elapsed_ms: elapsed
        });

        // classify_result for each passed tweet
        const categories = ['时闻', '深度解析', '技术技巧', '学术研究', '产品应用', '商业洞察'];
        const buildingIds = ['news', 'analysis', 'tips', 'research', 'product', 'business'];
        const categoryStats = {};

        const boardingEvents = events.filter(e => e.type === 'bus_boarding');
        boardingEvents.forEach((boarding, i) => {
            elapsed += 50 + Math.random() * 50; // 更快的分类间隔
            const catIndex = Math.floor(Math.random() * categories.length);
            const category = categories[catIndex];

            categoryStats[category] = (categoryStats[category] || 0) + 1;

            events.push({
                type: 'classify_result',
                data: {
                    tweet_id: boarding.data.tweet_id,
                    username: boarding.data.username,
                    category,
                    sub_category: 'Demo',
                    building_id: buildingIds[catIndex],
                    building_color: ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#9d4edd', '#ff8c42'][catIndex],
                    summary: `Demo summary for ${boarding.data.username}'s tweet`
                },
                elapsed_ms: elapsed
            });
        });

        // classify_done
        events.push({
            type: 'classify_done',
            data: { category_stats: categoryStats },
            elapsed_ms: elapsed
        });

        elapsed += 500;

        // pipeline_done
        events.push({
            type: 'pipeline_done',
            data: {
                status: 'success',
                duration_ms: elapsed,
                stats: {
                    total_tweets: tweets.length,
                    passed_tweets: passedCount,
                    category_stats: categoryStats
                }
            },
            elapsed_ms: elapsed
        });

        return events;
    }
}

// 导出到全局
window.DataLoader = DataLoader;
