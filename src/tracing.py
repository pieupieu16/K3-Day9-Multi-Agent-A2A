"""
src/tracing.py — Ghi log truy vết luồng xử lý Multi-Agent (Traceability Logger).
Bắt buộc theo README: trace.jsonl chứa duy nhất lượt chạy mới nhất, ghi đè khi chạy lại.
Đồng thời ghi vào cả root/trace.jsonl và logging/trace.jsonl.
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.llm_client import MODEL_NAME

ROOT_DIR = Path(__file__).resolve().parents[1]
TRACE_PATHS = [
    ROOT_DIR / "logging" / "trace.jsonl",
    ROOT_DIR / "trace.jsonl",
]


def reset_trace_file() -> None:
    """Xóa / reset toàn bộ file trace.jsonl trước lượt chạy mới."""
    for path in TRACE_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            pass  # Truncate file


def trace_event(
    case_id: str,
    agent: str,
    task_type: str,
    payload: Any,
    status: str,
    output: Any,
    latency_ms: float,
    model_name: str = MODEL_NAME,
) -> None:
    """
    Ghi 1 dòng event truy vết dạng JSONL.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "agent": agent,
        "task_type": task_type,
        "payload": payload if isinstance(payload, (dict, list, str, int, float, bool)) else str(payload),
        "status": status,
        "output": output if isinstance(output, (dict, list, str, int, float, bool)) else str(output),
        "latency_ms": round(latency_ms, 2),
        "model": model_name,
    }

    line = json.dumps(record, ensure_ascii=False) + "\n"

    for path in TRACE_PATHS:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[Tracing Warning] Không thể ghi trace vào {path}: {e}")
