import os
import re
import json
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def strip_md_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[#*`>_~]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_readme():
    readme_path = os.path.join(BASE_DIR, 'README.md')
    catalog = []
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        matches = re.findall(r'-\s+\[([^\]]+)\]\((\d+\.md)\)', content)
        title_counts = Counter(t.strip() for t, _ in matches)
        seen_counts = Counter()
        for title, fname in matches:
            title = title.strip()
            seen_counts[title] += 1
            display_title = f"{title} (Part {seen_counts[title]})" if title_counts[title] > 1 else title
            fpath = os.path.join(BASE_DIR, fname)
            size_kb = round(os.path.getsize(fpath) / 1024, 1) if os.path.exists(fpath) else 0
            catalog.append({
                "file": fname,
                "title": display_title,
                "size_kb": size_kb
            })
    return catalog

def build_search_index(catalog):
    docs = []
    doc_id = 1
    anchor_re = re.compile(r'<a\s+id="([^"]+)"[^>]*></a>')

    for item in catalog:
        fname = item["file"]
        fpath = os.path.join(BASE_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()

        # 按空行切分段落，记录最近的有效锚点
        blocks = re.split(r'\n\s*\n', raw)
        current_anchor = ""
        for block in blocks:
            anchors = anchor_re.findall(block)
            if anchors:
                current_anchor = anchors[-1]
            # 跳过纯目录列表项（避免搜索结果被开头目录刷屏）
            if re.match(r'^\s*-\s+\[.*?\]\(\d+\.md#', block):
                continue
            clean = strip_md_html(block)
            if len(clean) < 25:
                continue
            docs.append({
                "id": doc_id,
                "file": fname,
                "chapter": item["title"],
                "anchor": current_anchor,
                "text": clean[:600]  # 截断超长块以控制索引体积
            })
            doc_id += 1
    return docs

if __name__ == '__main__':
    print("正在解析目录...")
    catalog = parse_readme()
    with open(os.path.join(BASE_DIR, 'catalog.json'), 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"已生成 catalog.json（共 {len(catalog)} 个章节文件）")

    print("正在构建全文检索索引...")
    docs = build_search_index(catalog)
    with open(os.path.join(BASE_DIR, 'search-index.json'), 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False)
    size_mb = os.path.getsize(os.path.join(BASE_DIR, 'search-index.json')) / (1024 * 1024)
    print(f"已生成 search-index.json（共 {len(docs)} 条段落索引，体积 {size_mb:.2f} MB）")