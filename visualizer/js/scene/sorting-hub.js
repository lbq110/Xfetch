class SortingHubScene {
    static CATEGORY_COLORS = {
        news: '#ff6b6b',
        analysis: '#ffd93d',
        tips: '#6bcb77',
        research: '#4d96ff',
        product: '#9d4edd',
        business: '#ff8c42'
    };

    static CATEGORY_MAP = {
        '时闻': 'news',
        '深度解析': 'analysis',
        '技术技巧': 'tips',
        '学术研究': 'research',
        '产品应用': 'product',
        '商业洞察': 'business'
    };

    constructor() {
        this.gameContainer = document.getElementById('game-container');
        this.buildingsArea = document.getElementById('buildings');
        this.busWindows = document.getElementById('bus-windows');
        this.busElement = document.getElementById('bus');
        this.guideLines = document.getElementById('guide-lines');

        this.buildingManager = new BuildingManager();
        this.passengers = [];
        this.sortingQueue = [];
    }

    show() {}
    hide() {}

    setPassengers(passengers) {
        this.passengers = passengers;
        this.sortingQueue = [...passengers];
    }

    async busArrived() {}

    async classifyTweet(data) {
        const person = this.passengers.find(p => p.id === data.tweet_id);
        if (!person) return;

        person.category = data.category;

        const buildingId = this.getCategoryId(data.category);
        const buildingEl = document.querySelector(`.building[data-id="${buildingId}"]`);
        if (!buildingEl) return;

        const busWindows = document.getElementById('bus-windows');
        const avatar = busWindows?.querySelector(`[data-id="${data.tweet_id}"]`);
        avatar?.remove();

        await this.animatePersonToBuilding(person, buildingEl, buildingId);
        this.updateBuildingCount(buildingId);
        this.updateCategoryBar(buildingId);
    }

    async animatePersonToBuilding(person, buildingEl, categoryId) {
        if (!this.gameContainer || !this.busElement) return;

        const tempPerson = this.createPersonElement(person);
        const busRect = this.busElement.getBoundingClientRect();
        const containerRect = this.gameContainer.getBoundingClientRect();

        const startX = busRect.right - containerRect.left + 10;
        const startY = busRect.bottom - containerRect.top - 50;

        tempPerson.style.left = `${startX}px`;
        tempPerson.style.top = `${startY}px`;
        this.gameContainer.appendChild(tempPerson);

        const popAngle = Math.random() * 60 - 30;
        const popHeight = 20 + Math.random() * 30;
        const popX = Math.cos(popAngle * Math.PI / 180) * 20;
        const popY = -popHeight;

        tempPerson.style.transition = 'transform 0.05s ease-out';
        tempPerson.style.transform = `translate(${popX}px, ${popY}px)`;
        await AnimationUtils.wait(50);

        const buildingRect = buildingEl.getBoundingClientRect();
        const targetX = buildingRect.left - containerRect.left + buildingRect.width / 2 - 10;
        const targetY = buildingRect.bottom - containerRect.top - 40;

        this.drawGuideLine(startX + popX, startY + popY, targetX, targetY, SortingHubScene.CATEGORY_COLORS[categoryId]);

        tempPerson.style.transition = 'left 0.15s ease-in-out, top 0.1s ease-out';
        tempPerson.style.left = `${targetX}px`;
        tempPerson.style.top = `${targetY}px`;
        await AnimationUtils.wait(150);

        buildingEl.classList.add('receiving');

        tempPerson.style.transition = 'opacity 0.03s, transform 0.03s';
        tempPerson.style.opacity = '0';
        tempPerson.style.transform = 'scale(0.5)';
        await AnimationUtils.wait(30);

        tempPerson.remove();
        setTimeout(() => buildingEl.classList.remove('receiving'), 200);
    }

    createPersonElement(person) {
        const tempPerson = document.createElement('div');
        tempPerson.className = 'pixel-person moving-person';
        tempPerson.style.setProperty('--person-color', person.color || '#3498db');

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        const img = document.createElement('img');
        img.src = person.avatar || PixelArt.createAvatarPlaceholder(person.username);
        img.onerror = () => { img.src = PixelArt.createAvatarPlaceholder(person.username); };
        avatarDiv.appendChild(img);
        tempPerson.appendChild(avatarDiv);

        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'body';
        tempPerson.appendChild(bodyDiv);

        return tempPerson;
    }

    drawGuideLine(x1, y1, x2, y2, color) {
        if (!this.guideLines) return;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const midX = (x1 + x2) / 2;
        const midY = Math.min(y1, y2) - 30;

        line.setAttribute('d', `M ${x1} ${y1} Q ${midX} ${midY} ${x2} ${y2}`);
        line.setAttribute('class', 'guide-line active');
        line.setAttribute('stroke', color || '#ffffff');
        this.guideLines.appendChild(line);

        setTimeout(() => {
            line.classList.remove('active');
            setTimeout(() => line.remove(), 500);
        }, 1000);
    }

    updateBuildingCount(categoryId) {
        const countEl = document.querySelector(`.building[data-id="${categoryId}"] .building-count`);
        if (countEl) {
            countEl.textContent = parseInt(countEl.textContent) + 1;
        }
    }

    updateCategoryBar(categoryId) {
        const categoryBar = document.querySelector(`.category-bar[data-category="${categoryId}"]`);
        if (!categoryBar) return;

        const countEl = categoryBar.querySelector('.cat-count');
        const fillEl = categoryBar.querySelector('.cat-bar-fill');

        if (countEl) {
            const count = parseInt(countEl.textContent) + 1;
            countEl.textContent = count;
            if (fillEl) {
                fillEl.style.width = `${Math.min((count / 10) * 100, 100)}%`;
            }
        }
    }

    updateAllCategoryStats(stats) {
        const maxCount = Math.max(...Object.values(stats), 1);

        Object.entries(stats).forEach(([category, count]) => {
            const categoryId = this.getCategoryId(category);

            const countEl = document.querySelector(`.category-bar[data-category="${categoryId}"] .cat-count`);
            const fillEl = document.querySelector(`.category-bar[data-category="${categoryId}"] .cat-bar-fill`);
            const buildingCount = document.querySelector(`.building[data-id="${categoryId}"] .building-count`);

            if (countEl) countEl.textContent = count;
            if (fillEl) fillEl.style.width = `${(count / maxCount) * 100}%`;
            if (buildingCount) buildingCount.textContent = count;
        });
    }

    getCategoryId(categoryName) {
        return SortingHubScene.CATEGORY_MAP[categoryName] || 'news';
    }

    reset() {
        this.passengers = [];
        this.sortingQueue = [];

        if (this.guideLines) {
            this.guideLines.innerHTML = '';
        }

        document.querySelectorAll('.building .building-count').forEach(el => {
            el.textContent = '0';
        });

        document.querySelectorAll('.category-bar').forEach(bar => {
            const countEl = bar.querySelector('.cat-count');
            const fillEl = bar.querySelector('.cat-bar-fill');
            if (countEl) countEl.textContent = '0';
            if (fillEl) fillEl.style.width = '0%';
        });
    }
}

// 导出到全局
window.SortingHubScene = SortingHubScene;
