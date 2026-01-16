/**
 * 小人精灵类
 */

class Person {
    constructor(data) {
        this.id = data.id || data.tweet_id;
        this.username = data.username;
        this.displayname = data.displayname || data.username;
        this.avatar = data.avatar || '';
        this.content = data.content || '';
        this.followers = data.followers || 0;

        // 状态
        this.state = 'queue'; // queue, reviewing, boarding, rejected, sorted
        this.passed = false;
        this.score = 0;
        this.category = '';

        // DOM 元素
        this.element = null;

        // 随机选择衣服颜色
        this.color = this.getRandomColor();
    }

    getRandomColor() {
        const colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c'];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    // 创建 DOM 元素
    createElement() {
        this.element = document.createElement('div');
        this.element.className = 'pixel-person';
        this.element.dataset.id = this.id;
        this.element.style.setProperty('--person-color', this.color);

        // 头像
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = this.avatar || PixelArt.createAvatarPlaceholder(this.username);
        avatarImg.alt = this.username;
        avatarImg.onerror = () => {
            avatarImg.src = PixelArt.createAvatarPlaceholder(this.username);
        };
        avatarDiv.appendChild(avatarImg);

        // 身体
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'body';

        this.element.appendChild(avatarDiv);
        this.element.appendChild(bodyDiv);

        // 悬浮提示
        this.element.addEventListener('mouseenter', (e) => this.showTooltip(e));
        this.element.addEventListener('mouseleave', () => this.hideTooltip());
        this.element.addEventListener('mousemove', (e) => this.updateTooltipPosition(e));

        return this.element;
    }

    // 显示悬浮提示
    showTooltip(e) {
        const tooltip = document.getElementById('tooltip');
        if (!tooltip) return;

        tooltip.innerHTML = `
            <div style="color: var(--accent-primary)">@${this.username}</div>
            <div style="margin-top: 4px; color: var(--text-secondary)">${this.content.substring(0, 80)}...</div>
            ${this.score ? `<div style="margin-top: 4px">Score: ${this.score}/10</div>` : ''}
        `;
        tooltip.classList.add('visible');
        this.updateTooltipPosition(e);
    }

    hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) tooltip.classList.remove('visible');
    }

    updateTooltipPosition(e) {
        const tooltip = document.getElementById('tooltip');
        if (!tooltip) return;
        tooltip.style.left = `${e.clientX + 15}px`;
        tooltip.style.top = `${e.clientY + 15}px`;
    }

    // 状态转换动画
    async setReviewing() {
        this.state = 'reviewing';
        this.element.classList.add('reviewing');
    }

    async setApproved(score) {
        this.state = 'boarding';
        this.passed = true;
        this.score = score;

        console.log('setApproved called for:', this.username, 'element:', this.element);

        if (!this.element) {
            console.error('Element is null in setApproved!');
            return;
        }

        // 显示通过效果
        const rect = this.element.getBoundingClientRect();
        PixelArt.showApprovalEffect(rect.left, rect.top);

        // 跳跃上车动画
        this.element.classList.add('jumping');

        // 也直接设置样式作为备份
        this.element.style.opacity = '0';
        this.element.style.transform = 'translateY(-30px) scale(0.5)';
        this.element.style.transition = 'all 0.3s ease-out';

        await AnimationUtils.wait(400);

        // 移除元素
        console.log('Removing element for:', this.username);
        this.element.remove();
    }

    async setRejected() {
        this.state = 'rejected';
        this.passed = false;

        // 显示拒绝效果
        const rect = this.element.getBoundingClientRect();
        PixelArt.showRejectionEffect(rect.left, rect.top);

        // 变灰消散
        this.element.classList.add('rejected');
        await AnimationUtils.wait(600);
        this.element.remove();
    }

    // 爆米花弹出（从大巴下车）
    async popOut(direction) {
        this.element.style.setProperty('--pop-x', `${direction.x}px`);
        this.element.style.setProperty('--pop-y', `${direction.y}px`);
        this.element.classList.add('popping');
        await AnimationUtils.wait(150);
    }

    // 跑向建筑
    async runToBuilding(targetX, targetY) {
        this.element.classList.remove('popping');
        this.element.classList.add('running');

        // 使用CSS transition移动
        this.element.style.transition = 'left 0.4s ease-in-out, top 0.3s ease-out';
        this.element.style.left = `${targetX}px`;
        this.element.style.top = `${targetY}px`;

        await AnimationUtils.wait(400);
    }

    // 进入建筑
    async enterBuilding() {
        this.state = 'sorted';
        this.element.classList.remove('running');
        this.element.classList.add('entering');

        await AnimationUtils.wait(150);
        this.element.remove();
    }

    // 创建乘客头像（用于大巴窗户）
    createPassengerAvatar(pressed = false) {
        const avatar = document.createElement('div');
        avatar.className = 'avatar-window' + (pressed ? ' pressed' : '');

        const img = document.createElement('img');
        img.src = this.avatar || PixelArt.createAvatarPlaceholder(this.username);
        img.alt = this.username;
        img.onerror = () => {
            img.src = PixelArt.createAvatarPlaceholder(this.username);
        };

        avatar.appendChild(img);
        return avatar;
    }

    // 销毁
    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
    }
}

// 导出到全局
window.Person = Person;
