class App {
    constructor() {
        this.dataLoader = new DataLoader();
        this.eventPlayer = null;
        this.events = [];

        this.reviewScene = new ReviewStopScene();
        this.transitScene = new TweetBusScene();
        this.sortingScene = new SortingHubScene();
        this.currentScene = 'review';

        this.isLoaded = false;
        this.isPlaying = false;
        this.passengers = [];
        this.authorScores = new Map();

        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.elapsedTime = document.getElementById('elapsed-time');
        this.passedCount = document.getElementById('passed-count');
        this.totalCount = document.getElementById('total-count');

        this.btnLoad = document.getElementById('btn-load');
        this.btnPlay = document.getElementById('btn-play');
        this.btnHistory = document.getElementById('btn-history');

        this.fileModal = document.getElementById('file-modal');
        this.fileList = document.getElementById('file-list');
        this.btnCloseModal = document.getElementById('btn-close-modal');

        this.init();
    }

    init() {
        this.bindEvents();
        this.setupEventPlayer();
    }

    bindEvents() {
        this.btnLoad?.addEventListener('click', () => this.showLoadModal());
        this.btnPlay?.addEventListener('click', () => this.togglePlay());
        this.btnHistory?.addEventListener('click', () => this.showHistory());
        this.btnCloseModal?.addEventListener('click', () => this.hideModal());

        this.fileModal?.addEventListener('click', (e) => {
            if (e.target === this.fileModal) this.hideModal();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === ' ') {
                e.preventDefault();
                this.togglePlay();
            }
            if (e.key === 'Escape') this.hideModal();
        });
    }

    setupEventPlayer() {
        this.eventPlayer = new EventPlayer({
            speed: 1,
            onProgress: (progress, elapsed) => this.updateProgress(progress, elapsed),
            onComplete: () => this.onPlaybackComplete()
        });

        const eventHandlers = {
            pipeline_start: (e) => this.handlePipelineStart(e),
            fetch_done: (e) => this.handleFetchDone(e),
            review_result: (e) => this.handleReviewResult(e),
            bus_boarding: (e) => this.handleBusBoarding(e),
            bus_depart: (e) => this.handleBusDepart(e),
            bus_arrive: (e) => this.handleBusArrive(e),
            classify_result: (e) => this.handleClassifyResult(e),
            classify_done: (e) => this.handleClassifyDone(e),
            pipeline_done: (e) => this.handlePipelineDone(e)
        };

        Object.entries(eventHandlers).forEach(([name, handler]) => {
            this.eventPlayer.on(name, handler);
        });
    }

    showLoadModal() {
        if (!this.fileList) return;

        this.fileList.innerHTML = `
            <div class="file-item" data-action="demo">
                <div class="file-name">DEMO MODE</div>
                <div class="file-date">Load demo data for testing</div>
            </div>
            <div class="file-item" data-action="upload">
                <div class="file-name">UPLOAD FILE</div>
                <div class="file-date">Select a .jsonl event file</div>
            </div>
        `;

        this.fileList.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', () => {
                if (item.dataset.action === 'demo') this.loadDemo();
                else if (item.dataset.action === 'upload') this.uploadFile();
                this.hideModal();
            });
        });

        this.fileModal?.classList.remove('hidden');
    }

    hideModal() {
        this.fileModal?.classList.add('hidden');
    }

    loadDemo() {
        this.events = this.dataLoader.loadDemoData();
        this.finishLoading();
    }

    async uploadFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.jsonl';

        input.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            try {
                const text = await file.text();
                this.events = this.dataLoader.loadFromText(text);
                this.finishLoading();
            } catch (error) {
                alert('Failed to load file. Please make sure it\'s a valid JSONL file.');
            }
        });

        input.click();
    }

    finishLoading() {
        this.eventPlayer.load(this.events);
        this.isLoaded = true;
        if (this.btnPlay) {
            this.btnPlay.disabled = false;
            this.btnPlay.textContent = 'PLAY';
        }
        this.resetAll();
    }

    togglePlay() {
        if (!this.isLoaded) return;

        if (this.isPlaying) {
            this.eventPlayer.pause();
            this.isPlaying = false;
            if (this.btnPlay) this.btnPlay.textContent = 'PLAY';
        } else {
            if (this.eventPlayer.getStatus().currentIndex >= this.events.length) {
                this.resetAll();
                this.eventPlayer.load(this.events);
            }
            this.eventPlayer.play();
            this.isPlaying = true;
            if (this.btnPlay) this.btnPlay.textContent = 'PAUSE';
        }
    }

    showHistory() {
        window.open('history.html', '_blank');
    }

    updateProgress(progress, elapsed) {
        const percent = Math.round(progress * 100);
        if (this.progressFill) this.progressFill.style.width = `${percent}%`;
        if (this.progressText) this.progressText.textContent = `${percent}%`;
        if (this.elapsedTime) this.elapsedTime.textContent = PixelArt.formatTime(elapsed);
    }

    onPlaybackComplete() {
        this.isPlaying = false;
        if (this.btnPlay) this.btnPlay.textContent = 'REPLAY';
    }

    resetAll() {
        this.passengers = [];
        this.authorScores.clear();

        this.reviewScene.reset();
        this.transitScene.reset();
        this.sortingScene.reset();

        this.switchToScene('review');
        this.updateProgress(0, 0);

        if (this.passedCount) this.passedCount.textContent = '0';
        if (this.totalCount) this.totalCount.textContent = '0';
    }

    switchToScene(sceneName) {
        this.currentScene = sceneName;
    }

    handlePipelineStart(event) {
        const { analyzer_model, classifier_model } = event.data;
        this.reviewScene.setModel(analyzer_model || 'unknown');
        const busModelEl = document.getElementById('bus-model');
        if (busModelEl) busModelEl.textContent = classifier_model || 'unknown';
    }

    handleFetchDone(event) {
        const { count, tweets } = event.data;
        if (this.totalCount) this.totalCount.textContent = count;
        this.reviewScene.addTweets(tweets);
    }

    async handleReviewResult(event) {
        const data = event.data;
        await this.reviewScene.reviewResult(data);
        this.reviewScene.updateReviewScores(data.relevance_score, data.score);

        if (data.passed && this.passedCount) {
            this.passedCount.textContent = parseInt(this.passedCount.textContent) + 1;
        }

        if (!this.authorScores.has(data.username)) {
            this.authorScores.set(data.username, { total: 0, count: 0 });
        }
        const authorScore = this.authorScores.get(data.username);
        authorScore.total += data.score;
        authorScore.count += 1;

        this.updateLeaderboard();
    }

    handleBusBoarding(event) {
        const person = this.reviewScene.persons.get(event.data.tweet_id);
        if (person) this.passengers.push(person);
    }

    async handleBusDepart() {
        await this.reviewScene.busDeparting();
        this.transitScene.setPassengers(this.passengers);
        this.switchToScene('transit');
        await this.transitScene.startDriving(5000);
    }

    async handleBusArrive() {
        this.sortingScene.setPassengers(this.passengers);
        this.switchToScene('sorting');
        await this.sortingScene.busArrived();
    }

    async handleClassifyResult(event) {
        const data = event.data;
        this.reviewScene.updateReviewScores('--', '--', data.category);
        await this.sortingScene.classifyTweet(data);
        await AnimationUtils.wait(50);
    }

    handleClassifyDone(event) {
        this.sortingScene.updateAllCategoryStats(event.data.category_stats);
        const busWindows = document.getElementById('bus-windows');
        if (busWindows) busWindows.innerHTML = '';
    }

    handlePipelineDone(event) {
        const { stats } = event.data;
        if (stats) {
            if (this.passedCount) this.passedCount.textContent = stats.passed_tweets;
            if (this.totalCount) this.totalCount.textContent = stats.total_tweets;
        }
    }

    updateLeaderboard() {
        const leaderboard = document.getElementById('leaderboard');
        if (!leaderboard) return;

        const sorted = Array.from(this.authorScores.entries())
            .map(([username, { total, count }]) => ({ username, avgScore: total / count }))
            .sort((a, b) => b.avgScore - a.avgScore)
            .slice(0, 5);

        leaderboard.innerHTML = sorted.map((author, i) => `
            <div class="leaderboard-item">
                <span class="rank">${i + 1}.</span>
                <span class="name">@${author.username}</span>
                <span class="score">${author.avgScore.toFixed(1)}</span>
            </div>
        `).join('');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
