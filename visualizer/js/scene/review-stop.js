/**
 * 场景1: 审核公交站 (单一视图中的左侧区域)
 */

class ReviewStopScene {
    constructor() {
        this.queueArea = document.getElementById('queue-area');
        this.modelBadge = document.getElementById('model-analyzer');
        this.busWindows = document.getElementById('bus-windows');

        this.bus = new Bus('bus');
        this.persons = new Map(); // tweet_id -> Person
        this.queue = []; // 排队队列
    }

    // 显示/隐藏 (单一视图中不再需要，保留空实现以兼容)
    show() {}
    hide() {}

    // 设置模型名称
    setModel(modelName) {
        if (this.modelBadge) {
            this.modelBadge.textContent = modelName;
        }
    }

    // 添加推文到队列 - 松散分布在车门附近
    addTweets(tweets) {
        tweets.forEach((tweet, index) => {
            const person = new Person(tweet);
            this.persons.set(tweet.id, person);
            this.queue.push(person);

            // 创建 DOM 元素
            const element = person.createElement();

            // 随机位置 - 松散分布而非整齐排列
            const randomX = Math.random() * 80; // 0-80px 范围
            const randomY = Math.random() * 120 + 30; // 30-150px 范围
            element.style.left = `${randomX}px`;
            element.style.top = `${randomY}px`;

            // 轻微随机旋转，看起来更自然
            const randomRotate = (Math.random() - 0.5) * 10; // -5 到 5 度
            element.style.transform = `rotate(${randomRotate}deg)`;

            // 延迟添加以实现逐个出现效果
            setTimeout(() => {
                if (this.queueArea) {
                    this.queueArea.appendChild(element);
                }
            }, index * 100);
        });
    }

    // 开始审核一条推文
    async reviewTweet(tweetId) {
        const person = this.persons.get(tweetId);
        if (!person) return;

        // 更新当前审核卡片
        this.updateCurrentCard(person);

        // 移动到审核位置
        await person.setReviewing();
    }

    // 审核结果
    async reviewResult(data) {
        console.log('reviewResult called:', data.tweet_id, 'persons keys:', Array.from(this.persons.keys()));
        const person = this.persons.get(data.tweet_id);
        if (!person) {
            console.error('Person not found for tweet_id:', data.tweet_id);
            return;
        }
        console.log('Found person:', person.username, 'passed:', data.passed);

        person.score = data.score;
        person.relevanceScore = data.relevance_score;

        // 更新当前审核卡片
        this.updateCurrentCard(person);

        if (data.passed) {
            // 通过 - 上车
            await person.setApproved(data.score);
            this.bus.addPassenger(person);

            // 添加头像到大巴窗户
            this.addPassengerToBusWindow(person);
        } else {
            // 拒绝 - 消散
            await person.setRejected();
        }

        // 从队列移除
        const index = this.queue.indexOf(person);
        if (index > -1) {
            this.queue.splice(index, 1);
        }
    }

    // 添加乘客头像到大巴窗户
    addPassengerToBusWindow(person) {
        if (!this.busWindows) return;

        // 使用新的乘客头像方法
        const avatarDiv = person.createPassengerAvatar(Math.random() < 0.3);
        avatarDiv.dataset.id = person.id;

        this.busWindows.appendChild(avatarDiv);
    }

    // 上车事件
    async boarding(data) {
        this.updateBusCount(data.passenger_count);
    }

    // 更新当前审核卡片
    updateCurrentCard(person) {
        const avatar = document.getElementById('card-avatar');
        const username = document.getElementById('card-username');
        const content = document.getElementById('card-content');

        if (avatar) {
            avatar.innerHTML = `<img src="${person.avatar || PixelArt.createAvatarPlaceholder(person.username)}" alt="${person.username}">`;
        }
        if (username) {
            username.textContent = `@${person.username}`;
        }
        if (content) {
            content.textContent = person.content.substring(0, 100) + '...';
        }
    }

    // 更新审核结果显示
    updateReviewScores(relevance, value, category = '--') {
        const relEl = document.getElementById('card-relevance');
        const valEl = document.getElementById('card-value');
        const catEl = document.getElementById('card-category');

        if (relEl) relEl.textContent = typeof relevance === 'number' ? Math.round(relevance) : relevance;
        if (valEl) valEl.textContent = value;
        if (catEl) catEl.textContent = category;
    }

    // 更新大巴乘客数
    updateBusCount(count) {
        // 可以在 UI 某处显示
    }

    // 大巴出发
    async busDeparting() {
        await this.bus.closeDoor();
    }

    // 重置场景
    reset() {
        // 清空队列
        if (this.queueArea) {
            this.queueArea.innerHTML = '';
        }

        // 清空大巴窗户
        if (this.busWindows) {
            this.busWindows.innerHTML = '';
        }

        // 清空大巴
        this.bus.clearPassengers();

        // 清空数据
        this.persons.clear();
        this.queue = [];

        // 重置卡片
        const avatar = document.getElementById('card-avatar');
        const username = document.getElementById('card-username');
        const content = document.getElementById('card-content');

        if (avatar) avatar.innerHTML = '';
        if (username) username.textContent = '@waiting...';
        if (content) content.textContent = 'Waiting for tweets...';

        this.updateReviewScores('--', '--', '--');

        // 重置大巴位置
        this.bus.reset();
    }

    // 获取大巴乘客
    getPassengers() {
        return this.bus.getPassengers();
    }
}

// 导出到全局
window.ReviewStopScene = ReviewStopScene;
