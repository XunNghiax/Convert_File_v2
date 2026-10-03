import re
import sys
import time
import json
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_url(url: str, retries: int = 3, delay: float = 1.0) -> str:
    """Tải nội dung trang web với User-Agent và cơ chế thử lại."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(delay * (attempt + 1))
    return ""

def extract_chapter_content(html: str) -> str:
    """Trích xuất nội dung văn bản thuần trong thẻ <pre>...</pre> của cool18."""
    # Tìm vùng nội dung chính trong pre
    m = re.search(r'<pre>(.*?)</pre>', html, re.DOTALL)
    if not m:
        # Fallback tìm trong content-section
        m = re.search(r'<div class=["\']content-section["\'][^>]*>(.*?)</div>', html, re.DOTALL)
        if not m:
            return ""
    
    raw = m.group(1)
    
    # Loại bỏ footer chỉnh sửa diễn đàn: 本贴由[...]最后编辑于...
    raw = re.sub(r'本贴由\[.*?\]最后编辑于:.*', '', raw)
    # Loại bỏ các link quảng cáo nếu có
    raw = re.sub(r'<font color=[^>]+>\s*www\.6park\.com\s*</font>', '', raw)
    
    # Chuẩn hóa ngắt dòng HTML
    raw = raw.replace('<br>', '\n').replace('<BR>', '\n')
    raw = raw.replace('<p>', '\n\n').replace('<P>', '\n\n')
    # Bỏ mọi thẻ HTML còn sót
    text = re.sub(r'<[^>]+>', '', raw)
    
    # Chuẩn hóa khoảng trắng và dòng trống liên tiếp
    lines = [line.rstrip() for line in text.splitlines()]
    clean_text = "\n".join(lines)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()
    return clean_text

def get_thread_info(html: str) -> dict:
    """Lấy thông tin threadInfo từ mã nguồn trang."""
    m = re.search(r'const threadInfo = (\{.*?\});', html)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Tìm rootid từ input hidden nếu có
    m_root = re.search(r'<input [^>]*name=["\']rootid["\'] [^>]*value=["\'](\d+)["\']', html)
    rootid = m_root.group(1) if m_root else None
    return {"rootid": rootid}

def crawl_cool18_novel(root_tid: int = 34093, output_file: Path = Path("craw/shao_long_feng_liu_raw.txt"), max_chunks: int = 0):
    """Crawl toàn bộ các chương của bộ truyện từ cool18 qua achildlist API."""
    print(f"[*] Đang lấy danh sách các chương từ Thread gốc TID: {root_tid}...")
    api_url = f"https://www.cool18.com/bbs4/index.php?app=forum&act=achildlist&tid={root_tid}"
    api_resp = fetch_url(api_url)
    
    if not api_resp:
        print("[-] Không thể tải danh sách chương từ API.")
        return
        
    try:
        data = json.loads(api_resp)
    except Exception as e:
        print(f"[-] Lỗi phân tích JSON API: {e}")
        return

    # Lọc các bài đăng của tác giả/người đăng chính (ở đây là 小脸猫)
    chapters = []
    for item in data:
        subj = item.get("subject", "").strip()
        m = re.match(r'^(\d{3})-(\d{3})', subj)
        if m:
            start_ch = int(m.group(1))
            end_ch = int(m.group(2))
            chapters.append({
                "start": start_ch,
                "end": end_ch,
                "tid": item.get("tid"),
                "subject": subj,
                "bytes": item.get("size")
            })

    # Sắp xếp các tập chương theo thứ tự tăng dần
    chapters.sort(key=lambda x: x["start"])
    print(f"[+] Tìm thấy {len(chapters)} cụm chương (từ chương {chapters[0]['start']:03d} đến {chapters[-1]['end']:03d}).")

    if max_chunks > 0:
        chapters = chapters[:max_chunks]
        print(f"[*] Chế độ giới hạn thử nghiệm: Chỉ crawl {len(chapters)} cụm chương đầu tiên.")


    output_file.parent.mkdir(parents=True, exist_ok=True)
    total_chars = 0

    with open(output_file, "w", encoding="utf-8") as f_out:
        for idx, ch in enumerate(chapters, start=1):
            ch_url = f"https://www.cool18.com/bbs4/index.php?app=forum&act=threadview&tid={ch['tid']}"
            print(f"[{idx}/{len(chapters)}] Đang crawl: {ch['subject']} (TID: {ch['tid']})...", end="", flush=True)
            
            try:
                ch_html = fetch_url(ch_url)
                content = extract_chapter_content(ch_html)
                if content:
                    f_out.write(f"\n\n=== {ch['subject']} ===\n\n")
                    f_out.write(content)
                    f_out.write("\n")
                    f_out.flush()
                    total_chars += len(content)
                    print(f" Xong ({len(content):,} ký tự).")
                else:
                    print(" Cảnh báo: Không bóc tách được nội dung.")
            except Exception as e:
                print(f" Lỗi: {e}")
            
            # Nghỉ ngắn giữa các request để lịch sự với server
            time.sleep(0.5)

    print(f"\n[+] ĐÃ HOÀN TẤT CRAWL!")
    print(f"[+] File RAW tiếng Trung đã lưu tại: {output_file}")
    print(f"[+] Tổng số ký tự tiếng Trung thu được: {total_chars:,} chữ.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tool crawl truyện RAW tiếng Trung từ cool18")
    parser.add_argument("--tid", type=int, default=34093, help="TID thread gốc của truyện (mặc định: 34093)")
    parser.add_argument("--output", default="craw/shao_long_feng_liu_raw.txt", help="Đường dẫn file lưu kết quả")
    parser.add_argument("--max-chunks", type=int, default=0, help="Số cụm chương tối đa cần tải (0 = tải tất cả)")
    parser.add_argument("--single-url", default="", help="Crawl duy nhất 1 trang theo URL cụ thể")

    args = parser.parse_args()

    if args.single_url:
        print(f"[*] Crawl trang đơn: {args.single_url}")
        html = fetch_url(args.single_url)
        content = extract_chapter_content(html)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"[+] Đã lưu {len(content):,} ký tự vào: {out}")
    else:
        out_path = Path(args.output)
        crawl_cool18_novel(root_tid=args.tid, output_file=out_path, max_chunks=args.max_chunks)


