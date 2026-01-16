/**
 * 大巴精灵类
 */

class Bus {
    constructor(elementId) {
        this.element = document.getElementById(elementId);
        this.busZone = document.getElementById('zone-bus');
        this.windowsElement = document.getElementById('bus-windows');
        this.modelElement = document.getElementById('bus-model');

        this.passengers = [];
        this.maxVisible = 10; // 窗户最多显示的头像数
        this.state = 'waiting'; // waiting, loading, driving, arrived
    }

    // 设置模型名称
    setModel(modelName) {
        if (this.modelElement) {
            this.modelElement.textContent = modelName;
        }
    }

    // 添加乘客
    addPassenger(person) {
        this.passengers.push(person);
    }

    // 开门
    async openDoor() {
        await AnimationUtils.wait(200);
    }

    // 关门
    async closeDoor() {
        await AnimationUtils.wait(200);
    }

    // 开始行驶
    async startDriving(duration = 3000) {
        this.state = 'driving';

        // 轮子转动
        if (this.element) {
            const wheels = this.element.querySelectorAll('.wheel');
            wheels.forEach(wheel => wheel.classList.add('anim-spin'));
        }

        // 移动大巴容器
        if (this.busZone) {
            const targetLeft = window.innerWidth - 500;
            this.busZone.style.transition = `left ${duration}ms ease-in-out`;
            this.busZone.offsetHeight; // 强制重绘
            this.busZone.style.left = `${targetLeft}px`;
        }

        await AnimationUtils.wait(duration);
    }

    // 到站
    async arrive() {
        this.state = 'arrived';

        // 停止轮子
        if (this.element) {
            const wheels = this.element.querySelectorAll('.wheel');
            wheels.forEach(wheel => wheel.classList.remove('anim-spin'));
        }
    }

    // 清空乘客
    clearPassengers() {
        this.passengers = [];
        if (this.windowsElement) {
            this.windowsElement.innerHTML = '';
        }
    }

    // 获取乘客列表
    getPassengers() {
        return this.passengers;
    }

    // 获取乘客数量
    getPassengerCount() {
        return this.passengers.length;
    }

    // 重置大巴位置
    reset() {
        this.state = 'waiting';
        this.passengers = [];

        if (this.windowsElement) {
            this.windowsElement.innerHTML = '';
        }

        // 停止轮子
        if (this.element) {
            const wheels = this.element.querySelectorAll('.wheel');
            wheels.forEach(wheel => wheel.classList.remove('anim-spin'));
        }

        // 重置位置
        if (this.busZone) {
            this.busZone.style.transition = 'none';
            this.busZone.style.left = '80px';
            this.busZone.offsetHeight; // 强制重绘
        }
    }

    // 弹出乘客（爆米花效果）
    async popPassenger(index) {
        const person = this.passengers[index];
        if (!person) return null;

        // 从窗户移除头像
        if (this.windowsElement) {
            const avatar = this.windowsElement.querySelector(`[data-id="${person.id}"]`);
            if (avatar) {
                avatar.style.transition = 'transform 0.15s, opacity 0.15s';
                avatar.style.transform = 'scale(0)';
                avatar.style.opacity = '0';
                setTimeout(() => avatar.remove(), 150);
            }
        }

        return person;
    }

    // 复制乘客到另一个窗口元素
    copyPassengersTo(targetWindowsId) {
        const targetWindows = document.getElementById(targetWindowsId);
        if (!targetWindows) return;

        targetWindows.innerHTML = '';

        this.passengers.slice(0, this.maxVisible).forEach(person => {
            const avatarDiv = person.createPassengerAvatar(Math.random() < 0.3);
            targetWindows.appendChild(avatarDiv);
        });
    }
}

// 导出到全局
window.Bus = Bus;
