"""
run.py — CLI Execution Runner chính điều hành pipeline Multi-Agent.
Thực hiện quét 50 input, gọi Coordinator, ghi log trace và nộp output JSON.
"""
import os
import sys
import glob
import json
import time
import argparse
import tempfile
from typing import List

from src.contracts import CaseInput
from src.coordinator import Coordinator
from src.tracing import reset_trace_file


def find_input_files() -> List[str]:
    """Tìm tất cả các file input EC_xxx.json trong folder input/ hoặc input/input/."""
    candidates = []
    
    # Check input/
    for p in glob.glob(os.path.join("input", "EC_*.json")):
        candidates.append(p)
        
    # Check input/input/
    for p in glob.glob(os.path.join("input", "input", "EC_*.json")):
        candidates.append(p)
        
    # Deduplicate by filename
    file_map = {}
    for p in candidates:
        fname = os.path.basename(p)
        if fname not in file_map:
            file_map[fname] = p
            
    sorted_files = sorted(file_map.values(), key=lambda x: os.path.basename(x))
    return sorted_files


def save_atomic_json(output_path: str, data: dict) -> None:
    """Ghi JSON an toàn bằng file tạm rồi đổi tên (tránh file bị hư dở dang)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dir_name = os.path.dirname(output_path)
    
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=2)
        tmp_name = tmp_file.name
        
    os.replace(tmp_name, output_path)


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent E-commerce Dispute Resolution Runner")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số lượng case cần xử lý (ví dụ: --limit 5)")
    args = parser.parse_args()

    print("=" * 70)
    print("KHOI CHAY MULTI-AGENT E-COMMERCE DISPUTE RESOLUTION PIPELINE")
    print("=" * 70)

    # 1. Reset trace files
    reset_trace_file()
    print("[OK] Da reset trace.jsonl cho luot chay moi nhat.")

    # 2. Find input files
    input_files = find_input_files()
    if not input_files:
        print("[WARNING] Khong tim thay file input nao trong input/ hoac input/input/!")
        sys.exit(1)

    if args.limit and args.limit > 0:
        input_files = input_files[: args.limit]
        print(f"[INFO] Dang chay Smoke Test voi gioi han: {len(input_files)} cases.")

    print(f"[INFO] Tim thay {len(input_files)} file input de xu ly.\n")

    coordinator = Coordinator()
    success_count = 0
    start_total_time = time.time()

    for idx, input_path in enumerate(input_files, start=1):
        fname = os.path.basename(input_path)
        case_start = time.time()
        
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                
            case_input = CaseInput.from_dict(raw_data)
            output = coordinator.process_case(case_input)
            
            output_path = os.path.join("output", fname)
            save_atomic_json(output_path, output.to_dict())
            
            case_time = (time.time() - case_start) * 1000
            print(f"[{idx:02d}/{len(input_files):02d}] [OK] {fname} -> Issue: {output.assessment['primary_issue']:<25} | Refund: {output.financial_resolution['recommended_refund_brl']:>6.2f} BRL ({case_time:.1f}ms)")
            success_count += 1

        except Exception as e:
            case_time = (time.time() - case_start) * 1000
            print(f"[{idx:02d}/{len(input_files):02d}] [ERROR] {fname} -> LOI: {e} ({case_time:.1f}ms)")

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 70)
    print(f"HOAN THANH: {success_count}/{len(input_files)} cases thanh cong.")
    if len(input_files) > 0:
        print(f"Tong thoi gian: {total_elapsed:.2f} seconds ({total_elapsed/len(input_files)*1000:.1f} ms/case)")
    print("=" * 70)


if __name__ == "__main__":
    main()
