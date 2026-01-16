class EventPlayer {
    constructor(options = {}) {
        this.events = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.playbackSpeed = options.speed || 1;
        this.startTime = 0;
        this.handlers = new Map();

        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onEvent = options.onEvent || (() => {});
    }

    load(events) {
        this.events = events;
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
    }

    on(eventType, handler) {
        if (!this.handlers.has(eventType)) {
            this.handlers.set(eventType, []);
        }
        this.handlers.get(eventType).push(handler);
    }

    off(eventType, handler) {
        const handlers = this.handlers.get(eventType);
        if (!handlers) return;
        const index = handlers.indexOf(handler);
        if (index > -1) handlers.splice(index, 1);
    }

    async emit(event) {
        const handlers = this.handlers.get(event.type) || [];
        for (const handler of handlers) {
            await handler(event);
        }
        this.onEvent(event);
    }

    async play() {
        if (this.events.length === 0) return;

        this.isPlaying = true;
        this.isPaused = false;
        this.startTime = performance.now();

        await this.playLoop();
    }

    async playLoop() {
        while (this.currentIndex < this.events.length && this.isPlaying) {
            if (this.isPaused) {
                await AnimationUtils.wait(100);
                continue;
            }

            const event = this.events[this.currentIndex];
            const nextEvent = this.events[this.currentIndex + 1];
            const handlerStart = performance.now();

            await this.emit(event);

            const handlerDuration = performance.now() - handlerStart;
            const progress = (this.currentIndex + 1) / this.events.length;
            this.onProgress(progress, event.elapsed_ms);

            this.currentIndex++;

            if (nextEvent && this.isPlaying && !this.isPaused) {
                const rawDelay = (nextEvent.elapsed_ms - event.elapsed_ms) / this.playbackSpeed;
                const delay = Math.min(rawDelay, 500);
                const remainingDelay = delay - handlerDuration;
                if (remainingDelay > 0) {
                    await AnimationUtils.wait(remainingDelay);
                }
            }
        }

        if (this.currentIndex >= this.events.length) {
            this.isPlaying = false;
            this.onComplete();
        }
    }

    pause() {
        this.isPaused = true;
    }

    resume() {
        this.isPaused = false;
    }

    stop() {
        this.isPlaying = false;
        this.isPaused = false;
        this.currentIndex = 0;
    }

    setSpeed(speed) {
        this.playbackSpeed = speed;
    }

    seekTo(index) {
        if (index >= 0 && index < this.events.length) {
            this.currentIndex = index;
        }
    }

    seekToTime(timeMs) {
        const index = this.events.findIndex(e => e.elapsed_ms >= timeMs);
        this.currentIndex = index >= 0 ? index : this.events.length - 1;
    }

    getStatus() {
        return {
            isPlaying: this.isPlaying,
            isPaused: this.isPaused,
            currentIndex: this.currentIndex,
            totalEvents: this.events.length,
            progress: this.events.length > 0 ? this.currentIndex / this.events.length : 0,
            speed: this.playbackSpeed
        };
    }

    getCurrentEvent() {
        return this.events[this.currentIndex] || null;
    }

    getDuration() {
        if (this.events.length === 0) return 0;
        return this.events[this.events.length - 1].elapsed_ms || 0;
    }

    async playInstant() {
        this.isPlaying = true;

        for (const event of this.events) {
            this.emit(event);
            await AnimationUtils.wait(50);
        }

        this.isPlaying = false;
        this.onComplete();
    }
}

// 导出到全局
window.EventPlayer = EventPlayer;
