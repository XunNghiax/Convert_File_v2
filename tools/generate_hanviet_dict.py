import json
import re
import urllib.request
import zipfile
import io
from pathlib import Path

def generate_hanviet_dictionary():
    dict_path = Path("resources/dictionaries/hanviet_dict.json")
    print(f"Generating full Han-Viet dictionary into {dict_path}...")

    # 1. Load Unihan
    url_unihan = 'https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip'
    req = urllib.request.Request(url_unihan, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        zip_data = resp.read()

    simp_to_trad = {}
    trad_to_simp = {}
    unihan_readings = {}

    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        with z.open('Unihan_Variants.txt') as f:
            for line in f:
                line_str = line.decode('utf-8', errors='ignore').strip()
                if not line_str or line_str.startswith('#'):
                    continue
                parts = line_str.split('\t')
                if len(parts) >= 3:
                    codepoints = re.findall(r'U\+([0-9A-Fa-f]+)', parts[0])
                    if not codepoints:
                        continue
                    char = chr(int(codepoints[0], 16))
                    target_cps = re.findall(r'U\+([0-9A-Fa-f]+)', parts[2])
                    target_chars = [chr(int(cp, 16)) for cp in target_cps]
                    if not target_chars:
                        continue
                    tag = parts[1]
                    if tag in ('kTraditionalVariant', 'kSemanticVariant', 'kZVariant'):
                        simp_to_trad[char] = target_chars[0]
                    elif tag == 'kSimplifiedVariant':
                        for simp in target_chars:
                            simp_to_trad[simp] = char

        with z.open('Unihan_Readings.txt') as f:
            for line in f:
                line_str = line.decode('utf-8', errors='ignore').strip()
                if not line_str or line_str.startswith('#'):
                    continue
                parts = line_str.split('\t')
                if len(parts) >= 3 and parts[1] == 'kVietnamese':
                    codepoints = re.findall(r'U\+([0-9A-Fa-f]+)', parts[0])
                    if not codepoints:
                        continue
                    char = chr(int(codepoints[0], 16))
                    readings = parts[2].split()
                    if readings:
                        unihan_readings[char] = readings[0].lower()

    # 2. Load hanvietData.js
    url_hanviet_data = 'https://raw.githubusercontent.com/ph0ngp/hanviet-pinyin-words/main/src/hanvietData.js'
    req = urllib.request.Request(url_hanviet_data, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode('utf-8', errors='ignore')
    json_text = text.replace('export const hanvietData = ', '').rstrip('; \n\r')
    hanviet_pinyin_data = json.loads(json_text)

    # 3. Load xue-hanzi
    url_xue = 'https://raw.githubusercontent.com/phucbm/xue-hanzi/main/public/data/dictionary.json'
    req = urllib.request.Request(url_xue, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        xue_data = json.loads(resp.read().decode('utf-8'))

    char_dict = {}

    # Common compound words from xue-hanzi / web novels for high priority
    compound_words = {
        "套装裙": "bộ váy công sở",
        "职业套装": "trang phục công sở",
        "职业套裙": "váy công sở",
        "肉色丝袜": "quần tất màu da",
        "丝袜": "quần tất",
        "高跟鞋": "giày cao gót",
        "勾勒出": "khắc họa rõ nét",
        "勾勒": "phác nét",
        "桃腮杏眼": "má đào mắt hạnh",
        "瑶鼻樱唇": "mũi ngọc môi anh đào",
        "梨花带雨": "lê hoa đái vũ",
        "雨后海棠": "hải đường sau mưa",
        "公车南下": "Công xa nam hạ",
        "江水春潮": "Giang thủy xuân triều",
        "乍遇凶险": "Sạ ngộ hung hiểm",
        "白领男女": "nam nữ văn phòng",
        "写字大楼": "tòa nhà văn phòng",
        "亚太保险公司": "Công ty bảo hiểm Á Thái",
        "省人民医院": "Bệnh viện nhân dân tỉnh",
        "大结局": "Đại kết cục",
        "上一章": "Chương trước",
        "下一章": "Chương sau",
        "返回目录": "Về mục lục"
    }

    # 1. From xue-hanzi single chars (simplified and traditional)
    for entry in xue_data:
        s = entry.get('s')
        t = entry.get('t')
        sv = entry.get('sv')
        if sv:
            reading = sv.split(',')[0].strip().lower()
            if reading:
                if s and len(s) == 1 and s not in char_dict:
                    char_dict[s] = reading
                if t and len(t) == 1 and t not in char_dict:
                    char_dict[t] = reading

    # 2. From hanviet_pinyin_data
    for char, pinyin_map in hanviet_pinyin_data.items():
        if char not in char_dict and isinstance(pinyin_map, dict):
            all_readings = []
            for rd_list in pinyin_map.values():
                for rd in rd_list:
                    if rd and rd not in all_readings:
                        all_readings.append(rd.strip().lower())
            if all_readings:
                char_dict[char] = all_readings[0]

    # 3. From Unihan readings
    for char, rd in unihan_readings.items():
        if char not in char_dict:
            char_dict[char] = rd

    # 4. Map simplified via simp_to_trad
    for simp, trad in simp_to_trad.items():
        if simp not in char_dict and trad in char_dict:
            char_dict[simp] = char_dict[trad]

    # 5. Hand-curated missing characters
    extra_chars = {
        '肏': 'thao',
        '滟': 'diễm',
        '瘙': 'táo',
        '咝': 'ti',
        '焗': 'cục',
        '蚝': 'hào',
        '腼': 'miện',
        '痦': 'ngụ',
        '栅': 'sanh',
        '礴': 'bác',
        '嗲': 'đã',
        '噼': 'phích',
        '鳘': 'mẫn',
        '剠': 'kình',
        '噻': 'tắc',
        '趐': 'khiêu',
        '忴': 'cầm',
        '掹': 'manh',
        '亽': 'nhân',
        '套': 'thao',
        '袜': 'vạt',
        '勾': 'câu',
        '勒': 'lặc',
    }
    char_dict.update(extra_chars)

    # Final combined dict: compound words + single characters
    final_dict = {}
    # Compound words first
    for k, v in compound_words.items():
        final_dict[k] = v
    # Single characters
    for k, v in sorted(char_dict.items()):
        if k not in final_dict:
            final_dict[k] = v

    dict_path.parent.mkdir(parents=True, exist_ok=True)
    dict_path.write_text(json.dumps(final_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Successfully saved {len(final_dict):,} entries to {dict_path}!")

if __name__ == "__main__":
    generate_hanviet_dictionary()
