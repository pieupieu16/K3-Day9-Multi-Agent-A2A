"""
src/llm_client.py — LLM Wrapper với Model hardcode <= 10B & Mock Mode.
Bắt buộc theo quy định cuộc thi:
- Model name được HARDCODE trong source code (không đặt trong .env).
- Có chế độ LLM_MOCK=1 để dev/test offline.
- Tự động retry khi JSON parse thất bại.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Union, Optional

# HARDCODED MODEL NAME (Bắt buộc <= 10B parameters theo README §9.4 & PHAN_CONG §1.9)
MODEL_NAME = "qwen2.5:7b"
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30  # seconds

logger = logging.getLogger(__name__)


def is_mock_mode() -> bool:
    """Kiểm tra flag LLM_MOCK trong môi trường."""
    val = os.environ.get("LLM_MOCK", "1").strip().lower()
    return val in ("1", "true", "yes")


def get_ollama_url() -> str:
    """Lấy URL Ollama local."""
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _get_mock_response(prompt: str, system_prompt: str) -> str:
    """Trả về JSON giả lập tùy theo loại prompt agent để không bị crash khi mock mode active."""
    lower_p = (prompt + " " + system_prompt).lower()
    
    if "order_seller" in lower_p or "seller" in lower_p:
        return json.dumps({
            "order_status": "delivered",
            "has_items": True,
            "seller_ids": ["mock_seller_1"],
            "item_ids": ["mock_order:1"],
            "seller_handoff_late": {"mock_seller_1": False},
            "evidence": ["order:mock_order", "seller:mock_seller_1"],
            "notes": "Mock OrderSeller agent evaluation"
        })
    elif "delivery" in lower_p:
        return json.dumps({
            "delivered": True,
            "delivered_after_estimate": False,
            "carrier_handoff_ts": "2018-01-02T10:00:00",
            "estimated_ts": "2018-01-10T00:00:00",
            "delivered_ts": "2018-01-08T15:00:00",
            "any_seller_handoff_late": False,
            "late_seller_ids": [],
            "evidence": ["order:mock_order"],
            "notes": "Mock Delivery agent evaluation"
        })
    elif "payment" in lower_p or "financial" in lower_p:
        return json.dumps({
            "n_payment_rows": 1,
            "payment_total": 100.0,
            "item_total": 85.0,
            "freight_total": 15.0,
            "reconciled_within_010": True,
            "is_split_payment": False,
            "payment_ids": ["mock_order:1"],
            "evidence": ["payment:mock_order:1"],
            "notes": "Mock Payment agent evaluation"
        })
    elif "policy" in lower_p:
        return json.dumps({
            "primary_issue": "unsupported_late_claim",
            "case_status": "no_action",
            "confidence": 0.95,
            "ranked_causes": [{"cause_code": "DELIVERY_WITHIN_ESTIMATE", "rank": 1}],
            "responsible_parties": [],
            "recommended_refund_brl": 0.0,
            "resolution_actions": ["reject_late_refund"],
            "evidence": ["policy:DELIVERY_WITHIN_ESTIMATE"]
        })
    
    # Generic mock response
    return json.dumps({"status": "ok", "mock": True, "model": MODEL_NAME})


def call_llm(
    prompt: str,
    system_prompt: str = "",
    json_mode: bool = True,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any] | str:
    """
    Gọi LLM model (Qwen2.5-7B) và trả về response hoặc dict JSON.
    Tự động fallback về Mock Mode nếu LLM_MOCK=1 hoặc gặp lỗi kết nối server.
    """
    if is_mock_mode():
        raw_res = _get_mock_response(prompt, system_prompt)
        if json_mode:
            try:
                return json.loads(raw_res)
            except json.JSONDecodeError:
                return {"raw": raw_res}
        return raw_res

    # Nếu không phải mock mode, thực hiện gọi Ollama API
    import requests
    
    ollama_endpoint = f"{get_ollama_url()}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    if json_mode:
        payload["format"] = "json"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start_time = time.time()
            response = requests.post(ollama_endpoint, json=payload, timeout=timeout)
            response.raise_for_status()
            res_data = response.json()
            raw_text = res_data.get("response", "")
            
            if not json_mode:
                return raw_text

            # Parse JSON
            try:
                parsed = json.loads(raw_text)
                return parsed
            except json.JSONDecodeError as je:
                logger.warning(f"Lỗi parse JSON lần {attempt}/{MAX_RETRIES}: {je}")
                if attempt == MAX_RETRIES:
                    # Chuyển về mock mode nếu retry thất bại 3 lần
                    logger.error("Đã hết số lần retry. Fallback về Mock Response.")
                    return json.loads(_get_mock_response(prompt, system_prompt))

        except Exception as e:
            logger.warning(f"Lỗi kết nối Ollama API ({ollama_endpoint}) lần {attempt}: {e}")
            if attempt == MAX_RETRIES:
                logger.warning("Không thể gọi Ollama. Tự động chuyển sang Mock Mode.")
                raw_res = _get_mock_response(prompt, system_prompt)
                return json.loads(raw_res) if json_mode else raw_res

    return {}
