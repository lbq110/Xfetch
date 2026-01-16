/**
 * 像素艺术工具函数
 */

const PixelArt = {
    // 更丰富的随机颜色
    colors: [
        '#ff6b6b', '#ff8e72', '#ffd93d', '#ffe66d',
        '#6bcb77', '#4ade80', '#4d96ff', '#60a5fa',
        '#9d4edd', '#c084fc', '#f472b6', '#fb7185',
        '#14b8a6', '#22d3ee', '#a78bfa', '#f97316'
    ],

    getRandomColor() {
        return this.colors[Math.floor(Math.random() * this.colors.length)];
    },

    // 创建像素烟雾效果
    createSmokeEffect(x, y, container) {
        const particleCount = 6;
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'smoke-particle';
            particle.style.left = `${x + (Math.random() - 0.5) * 20}px`;
            particle.style.top = `${y + (Math.random() - 0.5) * 20}px`;
            particle.style.animationDelay = `${Math.random() * 0.2}s`;
            container.appendChild(particle);

            // 动画结束后移除
            particle.addEventListener('animationend', () => {
                particle.remove();
            });
        }
    },

    // 创建心形效果
    createHeartEffect(x, y, container) {
        const heart = document.createElement('div');
        heart.className = 'heart-effect';
        heart.textContent = '♥';
        heart.style.left = `${x}px`;
        heart.style.top = `${y}px`;
        container.appendChild(heart);

        heart.addEventListener('animationend', () => {
            heart.remove();
        });
    },

    // 创建勾选效果
    createCheckEffect(x, y, container) {
        const check = document.createElement('div');
        check.className = 'check-effect';
        check.textContent = '✓';
        check.style.left = `${x}px`;
        check.style.top = `${y}px`;
        container.appendChild(check);

        check.addEventListener('animationend', () => {
            check.remove();
        });
    },

    // 生成头像占位符
    createAvatarPlaceholder(username) {
        const colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#9d4edd'];
        const color = colors[username.length % colors.length];
        const initial = username.charAt(0).toUpperCase();

        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">
                <rect width="40" height="40" fill="${color}"/>
                <text x="50%" y="50%" dy=".35em" text-anchor="middle"
                    font-family="'Press Start 2P', cursive" font-size="16" fill="#fff">
                    ${initial}
                </text>
            </svg>
        `;
        return `data:image/svg+xml,${encodeURIComponent(svg)}`;
    },

    // 格式化数字显示
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },

    // 格式化时间
    formatTime(ms) {
        const seconds = ms / 1000;
        if (seconds < 60) {
            return seconds.toFixed(1) + 's';
        }
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = (seconds % 60).toFixed(0);
        return `${minutes}m ${remainingSeconds}s`;
    },

    // 显示通过效果 (绿色勾 + 爱心)
    showApprovalEffect(x, y) {
        const container = document.getElementById('game-container');
        if (!container) return;

        // 绿色勾
        this.createCheckEffect(x + 10, y - 20, container);
        // 爱心
        setTimeout(() => {
            this.createHeartEffect(x + 20, y - 30, container);
        }, 100);
    },

    // 显示拒绝效果 (烟雾)
    showRejectionEffect(x, y) {
        const container = document.getElementById('game-container');
        if (!container) return;

        this.createSmokeEffect(x + 10, y, container);
    }
};

// 导出到全局
window.PixelArt = PixelArt;
