"""
scripts/create_empty_zip.py — Script tạo 1 file zip trống.
"""
import os
import zipfile

def create_empty_zip(filename="empty.zip"):
    filepath = os.path.abspath(filename)
    with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as z:
        pass  # Không thêm file nào vào zip
    
    print(f"[OK] Da tao file zip trong: {filepath} ({os.path.getsize(filepath)} bytes)")

if __name__ == "__main__":
    create_empty_zip("empty.zip")
