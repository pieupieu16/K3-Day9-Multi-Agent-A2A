"""
scripts/package_solution.py — Đóng gói folder output/ thành file solution.zip chuẩn thi đấu.
Bắt buộc theo README §8:
- Zip chỉ chứa đúng 50 file EC_001.json -> EC_050.json trong folder output/.
- Loại bỏ hoàn toàn các file lạ (kể cả .gitkeep).
"""
import os
import glob
import zipfile

def package():
    output_dir = "output"
    zip_paths = ["solution.zip", "output.zip"]

    json_files = sorted(glob.glob(os.path.join(output_dir, "EC_*.json")))
    print(f"[INFO] Tim thay {len(json_files)} file EC_xxx.json de dong goi.")

    if len(json_files) != 50:
        print(f"[WARNING] Can 50 file JSON nhưng hien tai co {len(json_files)} file!")

    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fpath in json_files:
                arcname = os.path.join("output", os.path.basename(fpath))
                zipf.write(fpath, arcname)
        print(f"[OK] Da dong goi thanh cong file zip: {zip_path} ({os.path.getsize(zip_path)} bytes)")

if __name__ == "__main__":
    package()
