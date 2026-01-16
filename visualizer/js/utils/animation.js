/**
 * 动画工具函数
 */

const AnimationUtils = {
    // 等待指定时间
    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    // 等待动画完成
    waitForAnimation(element, animationName) {
        return new Promise(resolve => {
            const handler = (e) => {
                if (!animationName || e.animationName === animationName) {
                    element.removeEventListener('animationend', handler);
                    resolve();
                }
            };
            element.addEventListener('animationend', handler);
        });
    },

    // 添加动画类并等待完成
    async playAnimation(element, animClass) {
        element.classList.add(animClass);
        await this.waitForAnimation(element);
        element.classList.remove(animClass);
    },

    // 顺序执行动画队列
    async runSequence(animations) {
        for (const anim of animations) {
            await anim();
        }
    },

    // 并行执行动画
    async runParallel(animations) {
        await Promise.all(animations.map(anim => anim()));
    },

    // 缓动函数
    easing: {
        linear: t => t,
        easeInQuad: t => t * t,
        easeOutQuad: t => t * (2 - t),
        easeInOutQuad: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
        easeOutBounce: t => {
            if (t < 1 / 2.75) {
                return 7.5625 * t * t;
            } else if (t < 2 / 2.75) {
                return 7.5625 * (t -= 1.5 / 2.75) * t + 0.75;
            } else if (t < 2.5 / 2.75) {
                return 7.5625 * (t -= 2.25 / 2.75) * t + 0.9375;
            } else {
                return 7.5625 * (t -= 2.625 / 2.75) * t + 0.984375;
            }
        }
    },

    // 数值动画
    animateValue(element, start, end, duration, formatter = v => v) {
        return new Promise(resolve => {
            const startTime = performance.now();

            const update = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easedProgress = this.easing.easeOutQuad(progress);
                const current = start + (end - start) * easedProgress;

                element.textContent = formatter(Math.round(current));

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    resolve();
                }
            };

            requestAnimationFrame(update);
        });
    },

    // 移动元素到目标位置
    moveTo(element, targetX, targetY, duration = 1000) {
        return new Promise(resolve => {
            const rect = element.getBoundingClientRect();
            const startX = rect.left;
            const startY = rect.top;
            const startTime = performance.now();

            const update = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easedProgress = this.easing.easeOutQuad(progress);

                const currentX = startX + (targetX - startX) * easedProgress;
                const currentY = startY + (targetY - startY) * easedProgress;

                element.style.transform = `translate(${currentX - startX}px, ${currentY - startY}px)`;

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    resolve();
                }
            };

            requestAnimationFrame(update);
        });
    },

    // 随机爆米花弹出方向
    getPopcornDirection() {
        const angle = (Math.random() - 0.5) * Math.PI; // -90 to 90 degrees
        const distance = 30 + Math.random() * 50;
        return {
            x: Math.sin(angle) * distance,
            y: -Math.abs(Math.cos(angle) * distance) - 20
        };
    }
};

// 导出到全局
window.AnimationUtils = AnimationUtils;
