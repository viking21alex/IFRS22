import os
import re
import json
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MDCN_DIR = os.path.join(BASE_DIR, 'MDCN')

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

def extract_blocks(fpath, fname, chapter_title, lang, start_id):
    docs = []
    doc_id = start_id
    anchor_re = re.compile(r'<a\s+id="([^"]+)"[^>]*></a>')

    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    # 按 H2 粗分小节索引，确保中文版即使没有 <a id> 也能精准定位到小节
    h2_parts = re.split(r'(?m)^(?=##\s+)', raw)
    for sec_idx, part in enumerate(h2_parts):
        blocks = re.split(r'\n\s*\n', part)
        current_anchor = ""
        for block in blocks:
            anchors = anchor_re.findall(block)
            if anchors:
                current_anchor = anchors[-1]
            if re.match(r'^\s*-\s+\[.*?\]\(\d+\.md#', block):
                continue
            clean = strip_md_html(block)
            min_len = 12 if lang == 'zh' else 25
            if len(clean) < min_len:
                continue
            docs.append({
                "id": doc_id,
                "lang": lang,
                "file": fname,
                "sec": sec_idx,
                "chapter": chapter_title,
                "anchor": current_anchor,
                "text": clean[:450]
            })
            doc_id += 1
    return docs, doc_id

def build_search_index(catalog):
    all_docs = []
    doc_id = 1
    zh_count = 0

    for item in catalog:
        fname = item["file"]
        en_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(en_path):
            docs, doc_id = extract_blocks(en_path, fname, item["title"], "en", doc_id)
            all_docs.extend(docs)

        zh_path = os.path.join(MDCN_DIR, fname)
        if os.path.exists(zh_path):
            docs, doc_id = extract_blocks(zh_path, fname, item["title"], "zh", doc_id)
            all_docs.extend(docs)
            zh_count += 1

    print(f"已扫描英文 {len(catalog)} 章，中文(MDCN) {zh_count} 章")
    return all_docs

if __name__ == '__main__':
    print("正在解析目录...")
    catalog = parse_readme()
    with open(os.path.join(BASE_DIR, 'catalog.json'), 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("正在构建中英文双语全文检索索引...")
    docs = build_search_index(catalog)
    with open(os.path.join(BASE_DIR, 'search-index.json'), 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False)
    size_mb = os.path.getsize(os.path.join(BASE_DIR, 'search-index.json')) / (1024 * 1024)
    print(f"完成！已生成 search-index.json（共 {len(docs)} 条中英段落索引，体积 {size_mb:.2f} MB）")