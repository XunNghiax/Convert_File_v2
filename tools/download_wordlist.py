import urllib.request
from pathlib import Path

def download_vietnamese_wordlist():
    url = "https://raw.githubusercontent.com/duyet/vietnamese-wordlist/master/Viet39K.txt"
    dest_path = Path("resources/dictionaries/vietnamese_words.txt")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Đang tải danh sách từ vựng tiếng Việt chuẩn từ: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        lines = [line.strip() for line in dest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"[+] Tải thành công! Tổng cộng: {len(lines):,} từ vựng.")
    except Exception as e:
        print(f"[-] Lỗi tải từ URL: {e}")

if __name__ == "__main__":
    download_vietnamese_wordlist()
