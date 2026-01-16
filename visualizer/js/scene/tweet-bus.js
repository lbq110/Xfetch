/**
 * 场景2: 推文大巴 (单一视图中，大巴从左向右行驶)
 */

class TweetBusScene {
    constructor() {
        this.busElement = document.getElementById('bus');
        this.busZone = document.getElementById('zone-bus'); // 大巴容器（绝对定位）
        this.busWindows = document.getElementById('bus-windows');
        this.roadElement = document.querySelector('.road');
        this.gameContainer = document.getElementById('game-container');

        this.passengers = [];
        this.travelDuration = 3000; // 默认行驶时间 3 秒
        this.isMoving = false;
    }

    // 显示/隐藏 (单一视图中不再需要，保留空实现以兼容)
    show() {}
    hide() {}

    // 设置乘客
    setPassengers(passengers) {
        this.passengers = passengers;
    }

    // 开始行驶动画 - 大巴真实从左向右移动
    async startDriving(duration = 3000) {
        this.travelDuration = duration;
        this.isMoving = true;

        console.log('Bus starting to drive!', duration);

        // 轮子转动
        if (this.busElement) {
            const wheels = this.busElement.querySelectorAll('.wheel');
            wheels.forEach(wheel => wheel.classList.add('anim-spin'));
        }

        // 移动整个大巴容器（绝对定位，用 left 动画）
        if (this.busZone) {
            // 计算目标位置（屏幕右侧，建筑附近）
            const targetLeft = window.innerWidth - 500;

            // 设置过渡动画
            this.busZone.style.transition = `left ${duration}ms ease-in-out`;

            // 强制重绘
            this.busZone.offsetHeight;

            // 移动到目标位置
            this.busZone.style.left = `${targetLeft}px`;
            console.log('Bus moving to:', targetLeft);
        }

        // 道路保持静止，不加动画

        // 等待行驶完成
        await AnimationUtils.wait(duration);

        this.stopDriving();
    }

    // 停止行驶
    stopDriving() {
        this.isMoving = false;

        if (this.busElement) {
            const wheels = this.busElement.querySelectorAll('.wheel');
            wheels.forEach(wheel => wheel.classList.remove('anim-spin'));
        }
    }

    // 重置大巴位置（回到左侧）
    resetBusPosition() {
        if (this.busZone) {
            this.busZone.style.transition = 'none';
            this.busZone.style.left = '80px'; // 回到初始位置
            // 强制重绘
            this.busZone.offsetHeight;
            this.busZone.style.transition = '';
        }
        if (this.busElement) {
            this.busElement.classList.remove('moving');
        }
    }

    // 重置场景
    reset() {
        this.passengers = [];
        this.stopDriving();
        this.resetBusPosition();
    }
}

// 导出到全局
window.TweetBusScene = TweetBusScene;
