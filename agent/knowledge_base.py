import re
import csv
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


class ProductRecord:
    def __init__(self, group: str, name: str, ptype: str, description: str, keywords: str, parent: str):
        self.group = group
        self.name = name
        self.type = ptype
        self.description = description
        self.keywords = [k.strip().lower() for k in keywords.split(",")]
        self.parent = parent


def load_products() -> list[ProductRecord]:
    products = []
    csv_path = BASE_DIR / "data" / "products.csv"
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            row["ptype"] = row.pop("type")
            products.append(ProductRecord(**row))
    return products


def load_markdown(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def search_knowledge_base(query: str) -> list[dict]:
    results = []

    products = load_products()
    query_lower = query.lower()

    for p in products:
        score = 0
        for kw in p.keywords:
            if kw in query_lower:
                score += 1

        if score > 0:
            doc_path = BASE_DIR / "products" / f"{p.name.lower().replace(' ', '_').replace('-', '_')}.md"
            doc_content = ""
            if doc_path.exists():
                doc_content = load_markdown(doc_path)[:500]

            results.append({
                "product": p.name,
                "type": p.type,
                "group": p.group,
                "description": p.description,
                "score": score,
                "matched_keywords": [kw for kw in p.keywords if kw in query_lower],
                "doc_link": get_doc_link(p.name),
                "doc_excerpt": doc_content[:300] if doc_content else "",
            })

    results.sort(key=lambda r: r["score"], reverse=True)

    return results


def get_doc_link(product_name: str) -> str:
    links = {
        "iRidium studio": "https://doc.iridi.com/Системы управления/iRidi%20Pro/Основные%20компоненты/IRidium_studio_2019",
        "i3 pro": "https://doc.iridi.com/Системы управления/iRidi%20Pro/Основные%20компоненты/I3pro_install",
        "iRidium server": "https://doc.iridi.com/Системы управления/iRidi%20Pro/Основные%20компоненты/Products_server",
        "HS Server": "https://doc.iridi.com/Оборудование/Серверы/IRidi_HS_Server",
        "ProAV Advanced": "https://doc.iridi.com/Оборудование/Серверы/IRidi_ProAV_Advanced",
        "ProAV Basic": "https://doc.iridi.com/Оборудование/Серверы/IRidi_ProAV_Basic",
        "Bus77 Home": "https://doc.iridi.com/Автоматизация/Bus77/Основные%20компоненты/Bus77_Home",
        "Bus77 Lite": "https://doc.iridi.com/Автоматизация/Bus77/Основные%20компоненты/Bus77_Home",
        "Bus77 Pro": "https://doc.iridi.com/Автоматизация/Bus77/Основные%20компоненты/Pro/general_information",
        "Bus77 Lite (equipment)": "https://doc.iridi.com/Автоматизация/Bus77/Основные%20компоненты/Lite/general_information",
        "iRidium transfer": "https://doc.iridi.com/Системы управления/iRidi%20Pro/Основные%20компоненты/Products_server",
    }
    return links.get(product_name, "https://doc.iridi.com")


def find_relevant_kb_articles(query: str) -> list[dict]:
    issues_path = BASE_DIR / "common_issues.md"
    content = load_markdown(issues_path)
    if not content:
        return []

    sections = re.split(r"##\s+\d+\.\s+", content)
    results = []
    query_lower = query.lower()

    for section in sections:
        if not section.strip():
            continue
        first_line = section.strip().split("\n")[0]
        lines = section.lower()
        score = 0

        problem_patterns = re.findall(r"\|\s*\*\*(.*?)\*\*\s*\|", section)
        for prob in problem_patterns:
            if prob.lower() in query_lower:
                score += 3

        keywords = re.findall(r"\|\s*([^|]+)\s*\|", lines)
        for kw in keywords:
            kw = kw.strip().lower()
            if len(kw) > 3 and kw in query_lower:
                score += 1

        if score > 0:
            results.append({
                "category": first_line,
                "score": score,
                "content": section[:500],
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
