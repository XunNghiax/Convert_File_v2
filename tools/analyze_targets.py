import json

with open("scanner/scanner_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

out_lines = []
for idx, item in enumerate(data):
    target = item.get("target", "")
    src = item.get("source", "")
    cue = item.get("yeu_to_nhan_biet", "")
    ctx = item.get("context", "").replace("\n", " ")
    cnt = item.get("so_lan_xuat_hien", 1)
    out_lines.append(f"{idx+1:03d} | TARGET: {target} | SRC: {src} | COUNT: {cnt} | CUE: {cue}\n     CONTEXT: {ctx[:120]}...\n")

with open("scratch/analyzed_summary.txt", "w", encoding="utf-8") as f:
    f.writelines(out_lines)

print("Saved scratch/analyzed_summary.txt, total:", len(data))
