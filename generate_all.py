import os
import re
import shutil
import urllib.parse

ROOT_DIR = r"c:\_CONFIANZA23\_CDU_Zettelkasten"

def sanitize_filesystem_name(name):
    if name is None: return ""
    # Illegal Windows characters: / \ : * ? " < > |
    s = name.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "").replace('"', "").replace("<", "").replace(">", "").replace("|", "").replace("`", "-")
    # Limit length and strip trailing dots/spaces
    s = s.strip().strip(".")
    return s[:100].strip()

def get_dir_name(code, title):
    safe_code = sanitize_filesystem_name(code)
    safe_title = sanitize_filesystem_name(title)
    return f"{safe_code} - {safe_title}"

def get_file_name(code, title):
    safe_code = sanitize_filesystem_name(code)
    safe_title = sanitize_filesystem_name(title)
    return f"{safe_code} - {safe_title}.md"

def encode_link(link):
    # Use urllib.parse.quote for maximum compatibility.
    return urllib.parse.quote(link.replace("\\", "/"), safe="/")

def get_parent_code(code, all_codes):
    if "." in code:
        curr = code[:code.rfind(".")]
        if curr in all_codes: return curr
        base = code.split(".")[0]
        if base in all_codes: return base
    if "/" in code:
        if "." in code:
            base = code.split(".")[0]
            if base in all_codes: return base
        else:
            curr = code
            while len(curr) > 1:
                curr = curr[:-1]
                if curr in all_codes: return curr
    curr = code
    while len(curr) > 1:
        curr = curr[:-1]
        if curr in all_codes: return curr
    return None

def build_udc_data(lang):
    cdus_dir = os.path.join(ROOT_DIR, "CDUs", lang)
    udc_data = {}
    if not os.path.exists(cdus_dir):
        return {}
    for filename in sorted(os.listdir(cdus_dir)):
        if filename.endswith(f"_{lang}.txt"):
            with open(os.path.join(cdus_dir, filename), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    match = re.match(r"^([^\s]+)\s+(.+)$", line)
                    if match:
                        code = match.group(1)
                        title = match.group(2).replace('"', '\\"')
                        udc_data[code] = title
    return udc_data

def get_relative_link(from_path_list, to_path_list, to_file):
    common_len = 0
    for i in range(min(len(from_path_list), len(to_path_list))):
        if from_path_list[i] == to_path_list[i]:
            common_len += 1
        else:
            break
    up = "../" * (len(from_path_list) - common_len)
    down = "/".join(to_path_list[common_len:])
    if down:
        down += "/"
    return encode_link(f"{up}{down}{to_file}")

def generate_portal(lang, udc_data, all_languages_data, all_path_caches):
    portal_dir = os.path.join(ROOT_DIR, lang)
    if os.path.exists(portal_dir):
        shutil.rmtree(portal_dir)
    os.makedirs(portal_dir)
    
    shutil.copytree(os.path.join(ROOT_DIR, "CDUs", lang), 
                   os.path.join(portal_dir, "CDUs"), 
                   dirs_exist_ok=True)
    
    all_codes = sorted(udc_data.keys(), key=lambda x: (x.replace(".", "").replace("/", "")))
    all_codes_set = set(all_codes)
    
    prev_code = {}
    next_code = {}
    for i in range(len(all_codes)):
        if i > 0:
            prev_code[all_codes[i]] = all_codes[i-1]
        if i < len(all_codes) - 1:
            next_code[all_codes[i]] = all_codes[i+1]
            
    path_cache = all_path_caches[lang]
    parent_to_children = {}
    for code in all_codes:
        direct_parent = get_parent_code(code, all_codes_set)
        if direct_parent not in parent_to_children:
            parent_to_children[direct_parent] = []
        parent_to_children[direct_parent].append(code)

    for code in all_codes:
        title = udc_data[code]
        p_folder_list = path_cache[code]
        dest_dir = os.path.join(portal_dir, *p_folder_list)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        # Home link relative to README.md
        readme_rel = "../" * (len(p_folder_list) + 1) + "README.md"
        breadcrumb_list = [f"[🏠 Home]({encode_link(readme_rel)})"]
        
        p_codes = []
        curr_p = get_parent_code(code, all_codes_set)
        while curr_p:
            p_codes.insert(0, curr_p)
            curr_p = get_parent_code(curr_p, all_codes_set)
            
        for i, p_code in enumerate(p_codes):
            p_title = udc_data[p_code]
            rel_link = get_relative_link(p_folder_list, path_cache[p_code], get_file_name(p_code, p_title))
            breadcrumb_list.append(f"[{p_title}]({rel_link})")
        breadcrumb_list.append(f"**[{title}]**")
        
        pr_nx_links = []
        if code in prev_code:
            pr = prev_code[code]
            rel_link = get_relative_link(p_folder_list, path_cache[pr], get_file_name(pr, udc_data[pr]))
            pr_nx_links.append(f"⬅️ Previous: [{udc_data[pr]}]({rel_link})")
        if code in next_code:
            nx = next_code[code]
            rel_link = get_relative_link(p_folder_list, path_cache[nx], get_file_name(nx, udc_data[nx]))
            pr_nx_links.append(f"Next ➡️: [{udc_data[nx]}]({rel_link})")
        
        # Hierarchy section list
        hierarchy_items = []
        for i, p_code in enumerate(p_codes):
            p_title = udc_data[p_code]
            rel_link = get_relative_link(p_folder_list, path_cache[p_code], get_file_name(p_code, p_title))
            hierarchy_items.append(f"- [L{i+1}: {p_title}]({rel_link})")
        
        # Cross-lingual links
        cross_links = []
        up_to_root = "../" * (len(p_folder_list) + 1)
        for l_key, l_data in all_languages_data.items():
            if l_key != lang and code in l_data:
                l_title = l_data[code]
                l_path_cache = all_path_caches[l_key]
                l_p_folder_list = l_path_cache[code]
                l_deep_path = "/".join(l_p_folder_list + [get_file_name(code, l_title)])
                cross_links.append(f"[{l_key}: {l_title}]({encode_link(up_to_root + l_key + '/' + l_deep_path)})")

        # Children section as Table
        children_table = ""
        if code in parent_to_children:
            header = "| Code | Title | Link |\n| :--- | :--- | :--- |\n"
            rows = []
            for ch in parent_to_children[code]:
                ch_p_folders = p_folder_list + [get_dir_name(code, title)]
                rel_link = get_relative_link(p_folder_list, ch_p_folders, get_file_name(ch, udc_data[ch]))
                rows.append(f"| {ch} | {udc_data[ch]} | [View]({rel_link}) |")
            children_table = header + "\n".join(rows)
        else:
            children_table = "- No direct children." if lang == "EN" else "- No hay hijos directos."

        # MOC only for non-leaf nodes
        moc_line = ""
        if code in parent_to_children:
            moc_line = f"- [Map of Content (MOC)]({encode_link('./' + get_dir_name(code, title) + '/_MOC.md')})\n"

        content = f"""---
title: "{title}"
udc_code: "{code}"
status: "stable"
tags: [udc, {lang.lower()}, node_{sanitize_filesystem_name(code).replace(".", "_")}]
---

{" > ".join(breadcrumb_list)}

{" | ".join(pr_nx_links)}

# {code} - {title}

## Hierarchy
{"".join([x + "\n" for x in hierarchy_items]) if hierarchy_items else "- Parent: [🏠 Home](" + encode_link(readme_rel) + ")\n"}

### Children / Subcategories
{children_table}

## Foundations
> [!ABSTRACT] ABSTRACT
> {"This node represents the UDC category" if lang == "EN" else "Este nodo representa la categoría CDU"} {code} in {lang}.

## Related & Interlinking
- {"See also" if lang == "EN" else "Ver también"}: [UDC Summary](http://udcsummary.info/php/index.php)
{"- Languages: " + " | ".join(cross_links) if cross_links else ""}
{moc_line}
## Backlinks
{"No backlinks yet." if lang == "EN" else "No hay enlaces entrantes aún."}
"""
        filename = get_file_name(code, title)
        with open(os.path.join(dest_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    for p_code, ch_list in parent_to_children.items():
        if p_code is None: continue
        p_path_list = path_cache[p_code] + [get_dir_name(p_code, udc_data[p_code])]
        target_dir = os.path.join(portal_dir, *p_path_list)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        moc_title = f"Map of Content - {p_code}"
        mermaid = ["graph TD"]
        mermaid.append(f'    Root["{p_code} - {udc_data[p_code]}"]')
        for ch in ch_list:
            mermaid.append(f'    Root --> Node_{sanitize_filesystem_name(ch).replace(".", "_")}["{ch} - {udc_data[ch]}"]')
        
        moc_content = f"""# {moc_title}

```mermaid
{chr(10).join(mermaid)}
```

## Children Table
| Code | Title | Link |
| :--- | :--- | :--- |
"""
        for ch in ch_list:
            moc_content += f"| {ch} | {udc_data[ch]} | [{udc_data[ch]}]({encode_link(get_file_name(ch, udc_data[ch]))}) |\n"
        
        with open(os.path.join(target_dir, "_MOC.md"), "w", encoding="utf-8") as f:
            f.write(moc_content)

def generate_readme(all_languages_data, all_path_caches):
    readme_path = os.path.join(ROOT_DIR, "README.md")
    
    sections = []
    sections.append("# 🏛️ Universal UDC Zettelkasten (v7.2.2-STABLE)")
    sections.append("\nWelcome to the **Dynamic Universal Zettelkasten**, organized with perfect hierarchical linking and URL encoding.")
    
    sections.append("\n## 🌍 Multilingual Portals")
    sections.append("| Language | Portal Link | Status |")
    sections.append("| :--- | :--- | :--- |")
    for lang in sorted(all_languages_data.keys()):
        first_codes = [c for c in all_languages_data[lang].keys() if len(c) == 1]
        if not first_codes: first_codes = sorted(all_languages_data[lang].keys())
        code0 = first_codes[0]
        title0 = all_languages_data[lang][code0]
        rel_link = f"./{lang}/{get_file_name(code0, title0)}"
        sections.append(f"| {lang} | [{lang} Portal]({encode_link(rel_link)}) | 🟢 Active |")

    sections.append("\n## 🗺️ Knowledge Domains (EN vs ES)")
    sections.append("| Icon | Code | Domain (EN) | Dominio (ES) |")
    sections.append("| :---: | :--- | :--- | :--- |")
    
    icons = {"0": "📚", "1": "🧠", "2": "🛐", "3": "⚖️", "5": "⚗️", "6": "🛠️", "7": "🎨", "8": "📖", "9": "📜"}
    en_data = all_languages_data.get("EN", {})
    es_data = all_languages_data.get("ES", {})
    
    for code in sorted(en_data.keys()):
        if len(code) == 1:
            icon = icons.get(code, "📁")
            en_title = en_data[code]
            es_title = es_data.get(code, en_title)
            en_link = f"./EN/{get_file_name(code, en_title)}"
            es_link = f"./ES/{get_file_name(code, es_title)}"
            sections.append(f"| {icon} | **{code}** | [{en_title}]({encode_link(en_link)}) | [{es_title}]({encode_link(es_link)}) |")

    sections.append("\n## 🚀 Bugfix Release (v7.2.2)")
    sections.append("### ✨ Bugfixes & Improvements")
    sections.append("- [x] **URL Encoding**: Fixed broken links due to spaces and special characters.")
    sections.append("- [x] **Cross-Portal Deep Linking**: Corrected paths for inter-language navigation.")
    sections.append("- [x] **Leaf Node Optimization**: No more broken MOC links on terminal nodes.")
    
    sections.append("\n---")
    sections.append("> [!TIP]\n> Use the breadcrumbs at the top of each file to navigate back to any level of the hierarchy up to the Home (README).")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))

# Main Execution
en_data = build_udc_data("EN")
es_data = build_udc_data("ES")
all_langs = {"EN": en_data, "ES": es_data}

all_path_caches = {}
for lang, data in all_langs.items():
    cache = {}
    codes_sorted = sorted(data.keys())
    codes_set = set(codes_sorted)
    for code in codes_sorted:
        p_folders = []
        curr = get_parent_code(code, codes_set)
        while curr:
            p_folders.insert(0, get_dir_name(curr, data[curr]))
            curr = get_parent_code(curr, codes_set)
        cache[code] = p_folders
    all_path_caches[lang] = cache

generate_portal("EN", en_data, all_langs, all_path_caches)
generate_portal("ES", es_data, all_langs, all_path_caches)
generate_readme(all_langs, all_path_caches)
print("Generation complete.")
