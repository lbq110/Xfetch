"""事件写入器 - 用于可视化前端的事件流"""

import json
import os
import time
from datetime import datetime
from typing import Any, Optional


class EventEmitter:
    """
    纯粹的事件记录器，只写文件，不知道谁在读

    - Pipeline 可选择是否使用
    - 不使用时不影响任何功能
    - 事件以 JSONL 格式追加写入
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or self._generate_run_id()
        self.events_dir = "data/events"
        self.event_file = os.path.join(self.events_dir, f"{self.run_id}.jsonl")
        self.start_time = time.time()

        # 确保目录存在
        os.makedirs(self.events_dir, exist_ok=True)

    def _generate_run_id(self) -> str:
        """生成运行 ID: YYYY-MM-DD_HHmmss"""
        return datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def emit(self, event_type: str, data: Optional[dict] = None) -> None:
        """
        追加一行事件到 JSONL 文件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event = {
            "type": event_type,
            "data": data or {},
            "elapsed_ms": int((time.time() - self.start_time) * 1000),
            "timestamp": datetime.now().isoformat()
        }

        with open(self.event_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def get_event_file(self) -> str:
        """获取事件文件路径"""
        return self.event_file

    def get_run_id(self) -> str:
        """获取运行 ID"""
        return self.run_id


# 事件类型常量
class EventType:
    """事件类型定义"""
    # 管道生命周期
    PIPELINE_START = "pipeline_start"
    PIPELINE_DONE = "pipeline_done"
    PIPELINE_ERROR = "pipeline_error"

    # 抓取阶段
    FETCH_START = "fetch_start"
    FETCH_DONE = "fetch_done"

    # 审核阶段 (ContentAnalyzer)
    REVIEW_BATCH_START = "review_batch_start"
    REVIEW_START = "review_start"
    REVIEW_RESULT = "review_result"
    REVIEW_DONE = "review_done"

    # 上车阶段
    BUS_BOARDING = "bus_boarding"
    BUS_DEPART = "bus_depart"
    BUS_ARRIVE = "bus_arrive"

    # 分类阶段
    CLASSIFY_START = "classify_start"
    CLASSIFY_RESULT = "classify_result"
    CLASSIFY_DONE = "classify_done"

    # 生成阶段
    GENERATE_START = "generate_start"
    GENERATE_DONE = "generate_done"
