/**
 * 建筑精灵类
 */

class Building {
    constructor(element) {
        this.element = element;
        this.id = element.dataset.id;
        this.category = element.dataset.category;
        this.countElement = element.querySelector('.building-count');
        this.doorElement = element.querySelector('.building-door');

        this.count = 0;
        this.tweets = [];
    }

    // 获取建筑位置
    getPosition() {
        const rect = this.element.getBoundingClientRect();
        return {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height
        };
    }

    // 接收小人
    async receive(person) {
        this.tweets.push({
            id: person.id,
            username: person.username,
            content: person.content,
            score: person.score
        });

        this.count++;
        this.updateCount();

        // 建筑闪烁动画
        this.element.classList.add('anim-glow', 'anim-bounce');

        setTimeout(() => {
            this.element.classList.remove('anim-glow', 'anim-bounce');
        }, 500);
    }

    // 更新计数
    updateCount() {
        if (this.countElement) {
            this.countElement.textContent = this.count;

            // 数字弹跳效果
            this.countElement.style.transform = 'scale(1.3)';
            setTimeout(() => {
                this.countElement.style.transform = '';
            }, 200);
        }
    }

    // 重置
    reset() {
        this.count = 0;
        this.tweets = [];
        this.updateCount();
    }

    // 获取分类的推文列表
    getTweets() {
        return this.tweets;
    }

    // 点击显示推文列表
    enableClickToShowTweets(callback) {
        this.element.addEventListener('click', () => {
            if (callback) {
                callback(this.category, this.tweets);
            }
        });
    }
}

// 建筑管理器
class BuildingManager {
    constructor() {
        this.buildings = new Map();
        this.categoryMap = {
            '时闻': 'news',
            '深度解析': 'analysis',
            '技术技巧': 'tips',
            '学术研究': 'research',
            '产品应用': 'product',
            '商业洞察': 'business'
        };

        this.init();
    }

    init() {
        const buildingElements = document.querySelectorAll('.building');
        buildingElements.forEach(el => {
            const building = new Building(el);
            this.buildings.set(building.id, building);
        });
    }

    // 根据分类名获取建筑
    getBuildingByCategory(categoryName) {
        const id = this.categoryMap[categoryName] || 'news';
        return this.buildings.get(id);
    }

    // 根据 ID 获取建筑
    getBuildingById(id) {
        return this.buildings.get(id);
    }

    // 重置所有建筑
    resetAll() {
        this.buildings.forEach(building => building.reset());
    }

    // 更新分类统计
    updateCategoryStats() {
        const stats = {};
        this.buildings.forEach(building => {
            stats[building.category] = building.count;
        });
        return stats;
    }

    // 绘制导向线
    drawGuideLine(fromX, fromY, toBuilding, color) {
        const svg = document.getElementById('guide-lines');
        if (!svg) return;

        const toPos = toBuilding.getPosition();

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.classList.add('guide-line');
        path.setAttribute('stroke', color);

        // 创建曲线路径
        const midY = (fromY + toPos.y) / 2 - 50;
        const d = `M ${fromX} ${fromY} Q ${(fromX + toPos.x) / 2} ${midY} ${toPos.x} ${toPos.y}`;
        path.setAttribute('d', d);

        svg.appendChild(path);

        // 动画后移除
        setTimeout(() => {
            path.classList.add('active');
        }, 10);

        setTimeout(() => {
            path.remove();
        }, 2000);

        return path;
    }

    // 清除所有导向线
    clearGuideLines() {
        const svg = document.getElementById('guide-lines');
        if (svg) {
            svg.innerHTML = '';
        }
    }
}

// 导出到全局
window.Building = Building;
window.BuildingManager = BuildingManager;
