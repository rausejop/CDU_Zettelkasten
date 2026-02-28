import os
import re
import shutil
from datetime import datetime

# Configuration & Mappings
ICON_MAP = {"0": "🔬", "1": "🧠", "2": "⛪", "3": "⚖️", "5": "📐", "6": "⚙️", "7": "🎨", "8": "📚", "9": "🌍"}

ROOT_EN = {
    "0": "Science and Knowledge / Computer Science", "1": "Philosophy and Psychology", "2": "Religion and Theology",
    "3": "Social Sciences", "5": "Mathematics and Natural Sciences", "6": "Applied Sciences / Medicine",
    "7": "The Arts / Recreation", "8": "Language and Literature", "9": "Geography and History"
}

ROOT_ES = {
    "0": "Ciencia y Conocimiento / Informática", "1": "Filosofía y Psicología", "2": "Religión y Teología",
    "3": "Ciencias Sociales", "5": "Matemáticas y Ciencias Naturales", "6": "Ciencias Aplicadas / Medicina",
    "7": "Bellas Artes / Recreación", "8": "Lengua y Literatura", "9": "Geografía e Historia"
}

# Translation Dictionary for UI/Structure
TRANS = {
    "EN": {
        "nav": "Navigation", "hier": "Hierarchy", "found": "Foundations", "rel": "Related",
        "prev": "Previous", "next": "Next", "desc": "Description", "kd": "Knowledge Down",
        "kc": "Key Concepts", "def": "Definition", "meth": "Methodology", "bl": "Backlinks",
        "sum": "Summary", "moc": "Map of Content", "home": "Home", "back": "Back",
        "abs": "Conceptual Abstract", "child": "Child", "atomic": "This is an atomic terminal category.",
        "none_bl": "No backlinks recorded.", "branch": "Open Branch", "lang_name": "English"
    },
    "ES": {
        "nav": "Navegación", "hier": "Jerarquía", "found": "Cimientos", "rel": "Relacionados",
        "prev": "Anterior", "next": "Siguiente", "desc": "Descripción", "kd": "Desglose de Conocimiento",
        "kc": "Conceptos Clave", "def": "Definición", "meth": "Metodología", "bl": "Retroenlaces",
        "sum": "Resumen", "moc": "Mapa de Contenido", "home": "Inicio", "back": "Volver",
        "abs": "Resumen Conceptual", "child": "Hijo", "atomic": "Esta es una categoría terminal atómica.",
        "none_bl": "No hay retroenlaces registrados.", "branch": "Abrir Rama", "lang_name": "Español"
    }
}

def clean_title(title):
    title = title.replace(' ', '_')
    title = re.sub(r'[^a-zA-Z0-9_]', '', title)
    return title

def get_filename(code, title):
    safe_code = code.replace('/', '-').replace(':', '-')
    ct = clean_title(title)
    base = f"{safe_code}_{ct}"
    if len(base) > 59: base = base[:59]
    return base

class Node:
    def __init__(self, code, title, original_line):
        self.code = code
        self.title = title
        self.original_line = original_line
        self.clean_title = clean_title(title)
        self.filename_base = get_filename(code, title)
        self.children = []
        self.parent = None
        self.role = "ATOMIC"
        # Language-specific attributes will be set during generation
        self.path_en = None
        self.path_es = None
        self.level = len(re.sub(r'\D', '', self.code))
        self.backlinks = []

    def count_recursive(self):
        count = 1
        for child in self.children:
            count += child.count_recursive()
        return count

def parse_cdu_files(base_dir):
    nodes = []
    for i in range(10):
        filepath = os.path.join(base_dir, f"cdu{i}.txt")
        if not os.path.exists(filepath): continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                match = re.match(r'^([\d\.\/`\':]+)\s+(.*)$', line)
                if match:
                    code = match.group(1)
                    title = match.group(2)
                    nodes.append(Node(code, title, line))
    
    nodes.sort(key=lambda x: x.code)
    nodes_by_code = {n.code: n for n in nodes}
    root_nodes = []
    for n in nodes:
        if len(n.code) == 1:
            root_nodes.append(n)
            continue
        p_code = n.code
        parent = None
        while len(p_code) > 1:
            if '.' in p_code: p_code = p_code.rsplit('.', 1)[0]
            else: p_code = p_code[:-1]
            if p_code in nodes_by_code:
                parent = nodes_by_code[p_code]
                break
        if parent:
            n.parent = parent
            parent.children.append(n)
        else:
            root_nodes.append(n)
    return root_nodes, nodes_by_code

def assign_hierarchy_and_roles(root_nodes, base_output_dir):
    for r in root_nodes:
        total = r.count_recursive()
        r.role = "FOLDER"
        
        for lang in ["EN", "ES"]:
            lang_root = os.path.join(base_output_dir, lang)
            r_dir = os.path.join(lang_root, r.filename_base)
            os.makedirs(r_dir, exist_ok=True)
            path = os.path.join(r_dir, r.filename_base + ".md")
            if lang == "EN": r.path_en = path
            else: r.path_es = path
            
            for c1 in r.children:
                c1.role = "FOLDER"
                c1_dir = os.path.join(r_dir, c1.filename_base)
                os.makedirs(c1_dir, exist_ok=True)
                path_c1 = os.path.join(c1_dir, c1.filename_base + ".md")
                if lang == "EN": c1.path_en = path_c1
                else: c1.path_es = path_c1
                
                for c2 in c1.children:
                    if total > 99:
                        c2.role = "BUCKET"
                        path_c2 = os.path.join(c1_dir, c2.filename_base + ".md")
                        if lang == "EN": c2.path_en = path_c2
                        else: c2.path_es = path_c2
                        
                        def set_fragment_roles(node):
                            for child in node.children:
                                child.role = "FRAGMENT"
                                set_fragment_roles(child)
                        set_fragment_roles(c2)
                    else:
                        c2.role = "ATOMIC"
                        path_c2 = os.path.join(c1_dir, c2.filename_base + ".md")
                        if lang == "EN": c2.path_en = path_c2
                        else: c2.path_es = path_c2
                        
                        def set_atomic_paths_recursive(node, p_dir, l):
                            for child in node.children:
                                child.role = "ATOMIC"
                                p = os.path.join(p_dir, child.filename_base + ".md")
                                if l == "EN": child.path_en = p
                                else: child.path_es = p
                                set_atomic_paths_recursive(child, p_dir, l)
                        set_atomic_paths_recursive(c2, c1_dir, lang)

def get_rel_link(source_node, target_node, lang, label=None):
    if not target_node: return "None"
    
    # Target lookup
    target_is_frag = (target_node.role == "FRAGMENT")
    target_bucket = target_node
    if target_is_frag:
        curr = target_node
        while curr and curr.role != "BUCKET": curr = curr.parent
        if curr: target_bucket = curr

    # Source lookup
    source_bucket = source_node
    if source_node.role == "FRAGMENT":
        curr = source_node
        while curr and curr.role != "BUCKET": curr = curr.parent
        if curr: source_bucket = curr
    
    tp = target_bucket.path_en if lang == "EN" else target_bucket.path_es
    sp = source_bucket.path_en if lang == "EN" else source_bucket.path_es
    
    if not tp or not sp: return f"[{target_node.code} {target_node.title}]"

    source_dir = os.path.dirname(sp)
    rel_path = os.path.relpath(tp, source_dir).replace('\\', '/')
    anchor = f"#{target_node.filename_base}" if target_is_frag else ""
    
    final_label = label if label else f"{target_node.code} {target_node.title}"
    return f"[{final_label}]({rel_path}{anchor})"

def generate_node_content(node, lang, root_dir):
    t = TRANS[lang]
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    tags = [f"udc_{node.code[0]}", f"level_{node.level}", lang.lower()]
    
    # Multi-language title
    title_en = node.title
    # For ES, we'd ideally translate. For now, we use English title but Spanish structure.
    title_display = title_en
    if node.code in ROOT_ES and lang == "ES": title_display = ROOT_ES[node.code]
    elif node.code in ROOT_EN and lang == "EN": title_display = ROOT_EN[node.code]

    frontmatter = f"---\ntitle: \"{node.code} {title_display}\"\nudc_code: \"{node.code}\"\nlevel: {node.level}\nstatus: final\ncreated: {today}\ntags: {tags}\nlanguage: {lang}\n---\n"
    
    # Is it a fragment?
    is_frag = False
    if node.level > 3:
        root = node
        while root.parent: root = root.parent
        if root.count_recursive() > 99: is_frag = True
    
    header = "##" if is_frag else "#"
    
    # Navigation
    lang_root = os.path.join(root_dir, lang)
    source_p = node.path_en if lang == "EN" else node.path_es
    if not source_p: # fragment
        sb = node
        while sb.level > 3: sb = sb.parent
        source_p = sb.path_en if lang == "EN" else sb.path_es
        
    rel_readme = os.path.relpath(os.path.join(root_dir, "README.md"), os.path.dirname(source_p)).replace('\\', '/')
    
    hierarchy = [f"[🏠 {t['home']}]({rel_readme})"]
    p = node.parent
    ancestors = []
    while p:
        ancestors.insert(0, p)
        p = p.parent
    for anc in ancestors: hierarchy.append(get_rel_link(node, anc, lang))
    hierarchy.append(f"**[{node.code}]**")
    
    related = "None"
    if node.parent:
        sibs = node.parent.children
        idx = sibs.index(node)
        rel_notes = []
        if idx > 0: rel_notes.append(f"⬅️ {t['prev']}: {get_rel_link(node, sibs[idx-1], lang, 'Prev')}")
        if idx < len(sibs) - 1: rel_notes.append(f"{t['next']}: {get_rel_link(node, sibs[idx+1], lang, 'Next')} ➡️")
        if rel_notes: related = " | ".join(rel_notes)

    kd = [f"* {get_rel_link(node, c, lang)}" for c in node.children] or [f"*{t['atomic']}*"]
    bl = [f"* {get_rel_link(node, n, lang)} ({t['child'] if r=='Child' else r})" for n, r in node.backlinks] or [f"*{t['none_bl']}*"]

    return f"""{frontmatter if not is_frag else ""}
{header} {node.code} {title_display} <a name="{node.filename_base}"></a>

> [!ABSTRACT] {t['abs']}
> Original UDC: **{node.title}**.
> {t['sum']}: {node.code}.

### 🧭 {t['nav']}
* **{t['hier']}**: {" > ".join(hierarchy)}
* **{t['found']}**: {get_rel_link(node, node.parent, lang)}
* **{t['rel']}**: {related}

### 📥 {t['kd']}
{"\n".join(kd)}

### 📑 {t['bl']}
{"\n".join(bl)}

### 💡 {t['kc']}
> [!INFO] {t['def']}
> {title_display} ({node.code}).

> [!TIP] {t['meth']}
> UDC {node.code}.
"""

def generate_moc(parent_node, lang, root_dir):
    t = TRANS[lang]
    p_path = parent_node.path_en if lang == "EN" else parent_node.path_es
    moc_path = os.path.join(os.path.dirname(p_path), "_MOC.md")
    
    mermaid = ["graph LR", f'    ROOT["{parent_node.code} MOC"]']
    for child in parent_node.children:
        mermaid.append(f'    ROOT --> N{child.filename_base[:10]}["{child.code}"]')
    
    content = f"""---\ntitle: \"Map of Content - {parent_node.code}\"\ntags: [moc, {parent_node.code}, {lang.lower()}]\n---\n# 🗺️ {t['moc']}: {parent_node.code} {parent_node.title}\n\n## Visual\n```mermaid\n{"\n".join(mermaid)}\n```\n\n## List\n"""
    for child in parent_node.children:
        content += f"* {get_rel_link(parent_node, child, lang)}\n"
        
    with open(moc_path, 'w', encoding='utf-8') as f: f.write(content)

def generate_files_for_lang(nodes_by_code, lang, root_dir):
    # Group by physical file
    file_groups = {}
    for node in nodes_by_code.values():
        bucket = node
        if node.role == "FRAGMENT":
            curr = node
            while curr and curr.role != "BUCKET": curr = curr.parent
            bucket = curr
        
        if bucket not in file_groups: file_groups[bucket] = []
        if bucket != node: file_groups[bucket].append(node)

    for bucket, fragments in file_groups.items():
        path = bucket.path_en if lang == "EN" else bucket.path_es
        if not path: continue
        
        content = generate_node_content(bucket, lang, root_dir)
        if fragments:
            content += f"\n---\n## 🧩 {TRANS[lang]['sum']} Agregado\n"
            fragments.sort(key=lambda x: x.code)
            for f in fragments: content += generate_node_content(f, lang, root_dir) + "\n---\n"
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        
        if bucket.role == "FOLDER" and bucket.level == 2:
            generate_moc(bucket, lang, root_dir)

def generate_readme(root_nodes, root_dir):
    readme_path = os.path.join(root_dir, "README.md")
    
    def get_table(lang):
        t = TRANS[lang]
        rows = []
        for n in root_nodes:
            icon = ICON_MAP.get(n.code, "📁")
            title = ROOT_EN[n.code] if lang == "EN" else ROOT_ES[n.code]
            p = n.path_en if lang == "EN" else n.path_es
            rel = os.path.relpath(p, root_dir).replace('\\', '/')
            rows.append(f"| {icon} | `{n.code}` | {title} | [{t['branch']}]({rel}) |")
        return "| Icon | Code | Title | Link |\n|:---:|:---:|:---|:---:|\n" + "\n".join(rows)

    content = f"""# 🏛️ Universal Decimal Classification (UDC) Zettelkasten v5.0

![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Status](https://img.shields.io/badge/Status-Bilingual--Optimized-green)

Dual-language knowledge repository organized by UDC.

## 🌍 Language Portals / Portales de Idioma

### 🇺🇸 [English Version (EN)](EN/)
{get_table('EN')}

### 🇪🇸 [Versión Española (ES)](ES/)
{get_table('ES')}

## 📑 Project Plan & Progress
- [x] Initial UDC Parsing and Hierarchy Building.
- [x] Recursive Directory Density Optimization (<100 files).
- [x] Bidirectional Lateral and Vertical Linking.
- [x] Hybrid Aggregation for high-density nodes.
- [x] **Premium UI**: Callouts, MOCs, and YAML Metadata.
- [x] **v5.0**: Dual Language (EN/ES) concurrent generation.
- [ ] Integration with External Knowledge APIs (Wikipedia/UDCC).
- [ ] automated PDF export for offline study.

## ⚖️ License
Licensed under the **Apache License, Version 2.0** (the "License").
You may obtain a copy of the License at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

---
*Generated by Antigravity AI | {datetime.now().year}*
"""
    with open(readme_path, 'w', encoding='utf-8') as f: f.write(content)

if __name__ == "__main__":
    base = r"c:\_CONFIANZA23\_CDU_Zettelkasten"
    output = os.path.join(base, "CDU_Zettelkasten")
    if os.path.exists(output):
        try: shutil.rmtree(output)
        except: pass
    os.makedirs(output, exist_ok=True)
    
    roots, by_code = parse_cdu_files(base)
    assign_hierarchy_and_roles(roots, output)
    
    # Calculate backlinks (relation type 'Child')
    for n in by_code.values():
        if n.parent: n.parent.backlinks.append((n, "Child"))
        
    generate_files_for_lang(by_code, "EN", output)
    generate_files_for_lang(by_code, "ES", output)
    generate_readme(roots, output)
    print("Zettelkasten v5.0 (Bilingual Apache2) generated successfully.")
