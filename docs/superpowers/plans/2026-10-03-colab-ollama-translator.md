# Kế hoạch Triển khai Hệ thống Dịch thuật Tiểu thuyết Raw bằng Ollama (Qwen2.5) qua Google Colab

> **Dành cho Agent thực thi:** BẮT BUỘC SỬ DỤNG SUB-SKILL: Sử dụng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để triển khai kế hoạch này theo từng task. Các bước sử dụng cú pháp checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Xây dựng hệ thống tự động dịch tiểu thuyết raw tiếng Trung sang tiếng Việt bằng mô hình `qwen2.5:7b-instruct` chạy trên máy chủ Google Colab GPU T4, kết nối qua Cloudflare Tunnel, hỗ trợ phân tách chương tự động, ép glossary từ điển nhân vật, cơ chế checkpoint chống mất dữ liệu, tự động bồi đắp từ điển Hán Việt và tích hợp menu vào `run_cli.py`.

**Kiến trúc:**
- **Tầng 1 (Text Processing & Glossary):** Phân đoạn chương tiếng Trung (`ChapterSplitter`), trích xuất glossary theo ngữ cảnh và phân tích từ điển Hán Việt mới sinh ra (`GlossaryManager`).
- **Tầng 2 (Orchestration & Network):** Client kết nối Ollama Colab (`OllamaTranslatorClient`), quản lý tiến độ dịch chống mất mát dữ liệu (`TranslatorProgressTracker`).
- **Tầng 3 (Integration & Post-processing):** Bộ điều phối tổng thể (`TranslatorEngine`), tích hợp tùy chọn `[15]` vào `run_cli.py` và tự động kích hoạt `ReplaceEngine` làm sạch bản dịch cuối cùng.

**Công nghệ sử dụng:** Python 3.12, Requests, Regex Unicode, Pytest, JSON Streaming.

## Ràng buộc chung (Global Constraints)
- **Tương thích ngược:** Không làm thay đổi giao diện và hoạt động của các module hiện tại (`src/scanner/`, `src/replacer/`, `src/importer/`).
- **Bảo toàn dữ liệu (Fault-tolerant):** Mỗi chương dịch xong phải lập tức ghi đĩa và cập nhật file checkpoint `convert/progress_<tên_file>.json` để có thể tiếp tục bất cứ lúc nào khi Colab bị ngắt kết nối.
- **Chịu lỗi mạng:** Timeout 180s cho mỗi chương, tự động thử lại 3 lần với exponential backoff khi gặp lỗi mạng.
- **Cấu hình Model:** Ép các tham số sinh của Ollama: `temperature: 0.2`, `top_p: 0.9`, `num_ctx: 8192` (hoặc tối thiểu 4096), `keep_alive: "24h"`.

---

### Task 1: Xây dựng Module Phân đoạn chương (`ChapterSplitter`)

**Files:**
- Create: `src/translator/__init__.py`
- Create: `src/translator/chapter_splitter.py`
- Test: `tests/test_chapter_splitter.py`

**Interfaces:**
- Consumes: Đường dẫn file raw tiếng Trung (`craw/*.txt`) hoặc nội dung chuỗi văn bản.
- Produces: `ChapterSplitter.split_file(filepath: Path, max_chars: int = 4000) -> list[Chapter]`
  ```python
  @dataclass
  class Chapter:
      index: int
      title: str
      content: str
      char_count: int
  ```

- [ ] **Bước 1: Viết test cho ChapterSplitter**
  Tạo `tests/test_chapter_splitter.py`:
  ```python
  from pathlib import Path
  from src.translator.chapter_splitter import ChapterSplitter, Chapter

  def test_split_chapters_basic(tmp_path):
      content = """第一卷 闯荡都市
      
第一章 公车南下
龙剑飞的心情象这春末夏初的天气多少有些烦躁。

第二章 英雄救美
炎河是黄河的一个小支流，虽然不阔，却水深流急。
"""
      file_path = tmp_path / "test_raw.txt"
      file_path.write_text(content, encoding="utf-8")

      splitter = ChapterSplitter()
      chapters = splitter.split_file(file_path)

      assert len(chapters) == 2
      assert chapters[0].index == 1
      assert "第一章" in chapters[0].title
      assert "龙剑飞" in chapters[0].content
      assert chapters[1].index == 2
      assert "第二章" in chapters[1].title
      assert "炎河" in chapters[1].content

  def test_split_long_chapter(tmp_path):
      # Kiểm tra tự động tách sub-chunk nếu chương quá dài (> max_chars)
      long_para = "龙剑飞在河中奋力游动。" * 200 # ~2400 ký tự
      content = f"第一章 长章节\n\n{long_para}\n\n{long_para}"
      file_path = tmp_path / "long_raw.txt"
      file_path.write_text(content, encoding="utf-8")

      splitter = ChapterSplitter()
      chapters = splitter.split_file(file_path, max_chars=3000)
      assert len(chapters) >= 2
      assert chapters[0].title.startswith("第一章")
  ```
- [ ] **Bước 2: Chạy test để xác nhận test chạy và FAIL (chưa có code)**
  Chạy: `pytest tests/test_chapter_splitter.py`
- [ ] **Bước 3: Cài đặt `ChapterSplitter`**
  Tạo `src/translator/__init__.py` và `src/translator/chapter_splitter.py`:
  ```python
  import re
  from pathlib import Path
  from dataclasses import dataclass

  @dataclass
  class Chapter:
      index: int
      title: str
      content: str
      char_count: int

  class ChapterSplitter:
      CHAPTER_PATTERN = re.compile(
          r'^\s*(?:第\s*[0-9一二三四五六七八九十百千万]+\s*[章卷回节]|===|\d+[\.\s]+).*$',
          re.MULTILINE
      )

      def split_text(self, text: str, max_chars: int = 4000) -> list[Chapter]:
          matches = list(self.CHAPTER_PATTERN.finditer(text))
          raw_chapters = []

          if not matches:
              # Fallback nếu file không có header chương rõ ràng
              paras = [p.strip() for p in text.split("\n\n") if p.strip()]
              cur_chunk, cur_len, idx = [], 0, 1
              for p in paras:
                  if cur_len + len(p) > max_chars and cur_chunk:
                      raw_chapters.append((f"Phần {idx}", "\n\n".join(cur_chunk)))
                      idx += 1
                      cur_chunk, cur_len = [p], len(p)
                  else:
                      cur_chunk.append(p)
                      cur_len += len(p)
              if cur_chunk:
                  raw_chapters.append((f"Phần {idx}", "\n\n".join(cur_chunk)))
          else:
              for i, m in enumerate(matches):
                  title = m.group(0).strip()
                  start_pos = m.end()
                  end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                  content = text[start_pos:end_pos].strip()
                  raw_chapters.append((title, content))

          # Phân tách sub-chunk cho các chương dài
          final_chapters: list[Chapter] = []
          chap_idx = 1
          for title, body in raw_chapters:
              if len(body) <= max_chars:
                  final_chapters.append(Chapter(
                      index=chap_idx,
                      title=title,
                      content=body,
                      char_count=len(body)
                  ))
                  chap_idx += 1
              else:
                  paras = [p.strip() for p in body.split("\n\n") if p.strip()]
                  sub_idx = 1
                  cur_chunk, cur_len = [], 0
                  for p in paras:
                      if cur_len + len(p) > max_chars and cur_chunk:
                          final_chapters.append(Chapter(
                              index=chap_idx,
                              title=f"{title} (Phần {sub_idx})",
                              content="\n\n".join(cur_chunk),
                              char_count=cur_len
                          ))
                          chap_idx += 1
                          sub_idx += 1
                          cur_chunk, cur_len = [p], len(p)
                      else:
                          cur_chunk.append(p)
                          cur_len += len(p)
                  if cur_chunk:
                      final_chapters.append(Chapter(
                          index=chap_idx,
                          title=f"{title} (Phần {sub_idx})" if sub_idx > 1 else title,
                          content="\n\n".join(cur_chunk),
                          char_count=cur_len
                      ))
                      chap_idx += 1

          return final_chapters

      def split_file(self, filepath: Path, max_chars: int = 4000) -> list[Chapter]:
          text = Path(filepath).read_text(encoding="utf-8", errors="ignore")
          return self.split_text(text, max_chars=max_chars)
  ```
- [ ] **Bước 4: Chạy test xác nhận PASS**
  Chạy: `pytest tests/test_chapter_splitter.py`
- [ ] **Bước 5: Commit**
  `git add src/translator/ tests/test_chapter_splitter.py`
  `git commit -m "feat(translator): implement ChapterSplitter with smart header detection and chunking"`

---

### Task 2: Xây dựng Module Quản lý Glossary & Bồi đắp Từ điển (`GlossaryManager`)

**Files:**
- Create: `src/translator/glossary_manager.py`
- Test: `tests/test_glossary_manager.py`

**Interfaces:**
- Consumes: `character_dict.json`, `common_dict.json`, `deconvert_dict.json`.
- Produces:
  - `build_prompt_glossary(chapter_text: str) -> str`: Tạo danh sách glossary phù hợp cho chương hiện tại.
  - `parse_and_integrate_new_terms(ai_response: str) -> tuple[str, dict[str, str]]`: Tách riêng bản dịch và các từ Hán Việt mới; tự động lưu từ mới vào từ điển hoặc file gợi ý `samples/suggested_terms.json`.

- [ ] **Bước 1: Viết test cho GlossaryManager**
  Tạo `tests/test_glossary_manager.py`:
  ```python
  import json
  from pathlib import Path
  from src.translator.glossary_manager import GlossaryManager

  def test_build_prompt_glossary(tmp_path):
      dict_dir = tmp_path / "resources" / "dictionaries"
      dict_dir.mkdir(parents=True)
      (dict_dir / "character_dict.json").write_text(json.dumps({
          "long kiếm phi": "Long Kiếm Phi",
          "thẩm thiến ảnh": "Thẩm Thiến Ảnh",
          "tô diệc khả": "Tô Diệc Khả"
      }), encoding="utf-8")
      (dict_dir / "common_dict.json").write_text("{}", encoding="utf-8")
      (dict_dir / "deconvert_dict.json").write_text(json.dumps({
          "tô cũng có thể": "Tô Diệc Khả"
      }), encoding="utf-8")

      gm = GlossaryManager(base_dir=tmp_path)
      gm.load_dictionaries()

      chapter_text = "Long Kiếm Phi và Tô Diệc Khả cùng nhau đi dạo bên bờ sông."
      glossary = gm.build_prompt_glossary(chapter_text)

      assert "Long Kiếm Phi" in glossary
      assert "Tô Diệc Khả" in glossary
      assert "Thẩm Thiến Ảnh" not in glossary  # Không xuất hiện trong chương thì không nhồi vào prompt

  def test_parse_dual_output(tmp_path):
      gm = GlossaryManager(base_dir=tmp_path)
      ai_output = """=== BẢN DỊCH ===
Long Kiếm Phi bước nhanh về phía bờ sông Viêm.

=== TỪ ĐIỂN MỚI ===
- 炎河 => Sông Viêm (Loại: Địa danh)
- 稷下村 => Tắc Hạ thôn (Loại: Địa danh)
"""
      translation, new_terms = gm.parse_dual_output(ai_output)
      assert "Long Kiếm Phi bước nhanh" in translation
      assert "=== TỪ ĐIỂN MỚI ===" not in translation
      assert new_terms.get("炎河") == "Sông Viêm"
      assert new_terms.get("稷下村") == "Tắc Hạ thôn"
  ```
- [ ] **Bước 2: Chạy test để xác nhận FAIL**
  Chạy: `pytest tests/test_glossary_manager.py`
- [ ] **Bước 3: Cài đặt `GlossaryManager`**
  Tạo `src/translator/glossary_manager.py`:
  - Nạp từ điển từ `resources/dictionaries/`.
  - Phương thức `build_prompt_glossary`: Quét chuỗi tìm các key xuất hiện, bổ sung cảnh báo deconvert cho các tên dễ bị dịch nghĩa đen.
  - Phương thức `parse_dual_output`: Tách nội dung sau `=== BẢN DỊCH ===` và phân tích các dòng gạch đầu dòng trong `=== TỪ ĐIỂN MỚI ===`.
  - Phương thức `integrate_terms`: Lưu các từ mới vào file `samples/suggested_terms.json` và cập nhật từ điển trong bộ nhớ.
- [ ] **Bước 4: Chạy test xác nhận PASS**
  Chạy: `pytest tests/test_glossary_manager.py`
- [ ] **Bước 5: Commit**
  `git add src/translator/glossary_manager.py tests/test_glossary_manager.py`
  `git commit -m "feat(translator): implement GlossaryManager for dynamic context glossary and term harvesting"`

---

### Task 3: Xây dựng Module Quản lý Tiến độ Checkpoint (`TranslatorProgressTracker`)

**Files:**
- Create: `src/translator/progress_tracker.py`
- Test: `tests/test_translator_progress.py`

**Interfaces:**
- Consumes: File raw, output file path, checkpoint path.
- Produces: `TranslatorProgressTracker`
  - `is_completed(chapter_index: int) -> bool`
  - `mark_completed(chapter_index: int, chapter_title: str, translated_text: str)`
  - `get_resume_index() -> int`
  - `get_stats() -> dict`

- [ ] **Bước 1: Viết test cho TranslatorProgressTracker**
  Tạo `tests/test_translator_progress.py`:
  ```python
  from pathlib import Path
  from src.translator.progress_tracker import TranslatorProgressTracker

  def test_progress_tracking_and_resume(tmp_path):
      progress_file = tmp_path / "progress.json"
      output_file = tmp_path / "translated.txt"

      tracker = TranslatorProgressTracker(
          progress_file=progress_file,
          output_file=output_file,
          total_chapters=10
      )

      assert tracker.get_resume_index() == 1
      assert not tracker.is_completed(1)

      tracker.mark_completed(1, "Chương 1", "Nội dung chương 1 dịch.")
      assert tracker.is_completed(1)
      assert tracker.get_resume_index() == 2
      assert "Nội dung chương 1 dịch." in output_file.read_text(encoding="utf-8")

      # Khởi tạo lại tracker từ file checkpoint cũ để kiểm tra resume
      tracker_resume = TranslatorProgressTracker(
          progress_file=progress_file,
          output_file=output_file,
          total_chapters=10
      )
      assert tracker_resume.get_resume_index() == 2
      assert tracker_resume.is_completed(1)
  ```
- [ ] **Bước 2: Chạy test để xác nhận FAIL**
  Chạy: `pytest tests/test_translator_progress.py`
- [ ] **Bước 3: Cài đặt `TranslatorProgressTracker`**
  Tạo `src/translator/progress_tracker.py`:
  - Quản lý tải và lưu JSON checkpoint atomic bằng file `.tmp`.
  - Ghi bản dịch vào file `.txt` ở chế độ append và flush ngay lập tức.
  - Theo dõi thời gian trung bình mỗi chương để tính ETA.
- [ ] **Bước 4: Chạy test xác nhận PASS**
  Chạy: `pytest tests/test_translator_progress.py`
- [ ] **Bước 5: Commit**
  `git add src/translator/progress_tracker.py tests/test_translator_progress.py`
  `git commit -m "feat(translator): implement TranslatorProgressTracker with atomic checkpoint and resume"`

---

### Task 4: Xây dựng Client Kết nối Colab Ollama (`OllamaTranslatorClient`) & Bộ điều phối (`TranslatorEngine`)

**Files:**
- Create: `src/translator/ollama_client.py`
- Create: `src/translator/translator_engine.py`
- Test: `tests/test_translator_engine.py`

**Interfaces:**
- Consumes: `OllamaTranslatorClient(base_url, model_name)`, `TranslatorEngine`
- Produces: `TranslatorEngine.translate_novel(raw_path, output_path, start_chap, end_chap)` điều phối toàn trình từ đọc raw, gọi Colab, checkpoint, bồi đắp từ điển và hậu kỳ qua `ReplaceEngine`.

- [ ] **Bước 1: Viết test cho OllamaTranslatorClient và TranslatorEngine (sử dụng mock requests)**
  Tạo `tests/test_translator_engine.py`:
  ```python
  from unittest.mock import patch, MagicMock
  from pathlib import Path
  from src.translator.ollama_client import OllamaTranslatorClient
  from src.translator.translator_engine import TranslatorEngine

  def test_ollama_client_health_check():
      client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com")
      with patch("requests.get") as mock_get:
          mock_get.return_value.status_code = 200
          mock_get.return_value.json.return_value = {
              "models": [{"name": "qwen2.5:7b-instruct:latest"}]
          }
          assert client.check_health() is True

  def test_translator_engine_mock_run(tmp_path):
      raw_file = tmp_path / "raw.txt"
      raw_file.write_text("第一章 试运行\n\n龙剑飞走进了校园。", encoding="utf-8")
      out_file = tmp_path / "out.txt"

      engine = TranslatorEngine(
          colab_url="https://fake-tunnel.trycloudflare.com",
          base_dir=tmp_path
      )

      with patch.object(engine.client, "translate_chapter") as mock_translate:
          mock_translate.return_value = """=== BẢN DỊCH ===
Chương 1: Chạy thử
Long Kiếm Phi bước vào khuôn viên trường học.

=== TỪ ĐIỂN MỚI ===
- 龙剑飞 => Long Kiếm Phi
"""
          success = engine.translate_novel(
              raw_filepath=raw_file,
              output_filepath=out_file,
              max_chapters=1,
              run_post_processing=False
          )
          assert success is True
          assert out_file.exists()
          assert "Long Kiếm Phi bước vào" in out_file.read_text(encoding="utf-8")
  ```
- [ ] **Bước 2: Chạy test để xác nhận FAIL**
  Chạy: `pytest tests/test_translator_engine.py`
- [ ] **Bước 3: Cài đặt `OllamaTranslatorClient` trong `src/translator/ollama_client.py`**
  - Quản lý request POST `/api/chat` với payload cấu hình model: `temperature: 0.2`, `num_ctx: 8192`.
  - Tự động retry 3 lần, kiểm tra mã trạng thái HTTP 200.
- [ ] **Bước 4: Cài đặt `TranslatorEngine` trong `src/translator/translator_engine.py`**
  - Kết nối `ChapterSplitter`, `GlossaryManager`, `TranslatorProgressTracker`, `OllamaTranslatorClient` và `ReplaceEngine`.
  - Vòng lặp dịch từng chương có hiển thị tiến trình, thời gian xử lý và lưu checkpoint.
  - Gọi `ReplaceEngine` tự động hậu kỳ sau khi hoàn thành.
- [ ] **Bước 5: Chạy test xác nhận PASS**
  Chạy: `pytest tests/test_translator_engine.py`
- [ ] **Bước 6: Commit**
  `git add src/translator/ollama_client.py src/translator/translator_engine.py tests/test_translator_engine.py`
  `git commit -m "feat(translator): implement OllamaTranslatorClient and TranslatorEngine orchestration"`

---

### Task 5: Tích hợp CLI Menu `run_cli.py` & Kịch bản Colab Notebook (`tools/colab_ollama_server.ipynb`)

**Files:**
- Modify: `run_cli.py`
- Create: `tools/colab_ollama_server.ipynb`
- Test: Kiểm tra `python run_cli.py` hiển thị tùy chọn [15]

- [ ] **Bước 1: Tạo file notebook `tools/colab_ollama_server.ipynb`**
  - Chứa sẵn các code cell:
    1. Cài đặt Ollama + Cloudflared.
    2. Tải `qwen2.5:7b-instruct`.
    3. Chạy service và mở Cloudflare Tunnel hiển thị URL public HTTPS.
- [ ] **Bước 2: Cập nhật `run_cli.py`**
  - Thêm lựa chọn menu:
    ```text
      [ QUY TRÌNH DỊCH THUẬT AI (OLLAMA / COLAB) ]
      [15] 🌐 Dịch tiểu thuyết raw bằng Ollama Qwen2.5 (Colab Server)
    ```
  - Viết hàm xử lý cho lựa chọn `choice == "15"`:
    - Nhập URL Colab Tunnel.
    - Kiểm tra kết nối nhanh (Health check).
    - Chọn file raw từ danh sách gợi ý trong `craw/` và `samples/`.
    - Chọn phạm vi chương (toàn bộ hoặc giới hạn số chương).
    - Thực thi `TranslatorEngine.translate_novel()`.
- [ ] **Bước 3: Chạy test toàn bộ test suite để đảm bảo không có regression**
  Chạy: `pytest tests/` (Tất cả tests phải PASS).
- [ ] **Bước 4: Commit**
  `git add run_cli.py tools/colab_ollama_server.ipynb`
  `git commit -m "feat(cli): add Colab Ollama translator option [15] to run_cli and provide notebook"`

---

### Task 6: Kiểm thử Hồi quy Hệ thống & Dịch thử nghiệm Thực tế

**Files:**
- Run: Toàn bộ suite test trong `tests/`
- Run: Dịch thử nghiệm chương 1 của `craw/shao_long_feng_liu_raw.txt`
- Output: `convert/translated/shao_long_feng_liu_vietnamese.txt`

- [ ] **Bước 1: Chạy toàn bộ Unit Tests của dự án**
  Chạy: `pytest tests/` (Đảm bảo 100% PASS).
- [ ] **Bước 2: Chạy kiểm thử dịch với file raw thực tế**
  Kiểm tra chạy thử dịch chương 1 của `craw/shao_long_feng_liu_raw.txt` để đảm bảo văn phong mượt mà, tên `Long Kiếm Phi` chuẩn xác và không bị lỗi encoding hay đứt kết nối.
- [ ] **Bước 3: Báo cáo kết quả hoàn thành cho người dùng.**
