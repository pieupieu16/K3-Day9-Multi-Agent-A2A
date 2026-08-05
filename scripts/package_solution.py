"""
scripts/package_solution.py — Script đóng gói output/ thành solution.zip
"""
import os
import glob
import zipfile

def package():
    output_dir = "output"
    zip_paths = ["solution.zip", "output.zip"]

    json_files = sorted(glob.glob(os.path.join(output_dir, "EC_*.json")))
    print(f"[INFO] Tim thay {len(json_files)} file EC_xxx.json de dong goi.")

    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fpath in json_files:
                arcname = os.path.join("output", os.path.basename(fpath))
                zipf.write(fpath, arcname)
        print(f"[OK] Da dong goi thanh cong file zip: {zip_path} ({os.path.getsize(zip_path)} bytes)")

if __name__ == "__main__":
    package()
