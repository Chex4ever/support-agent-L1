from typing import Optional
from agent.knowledge_base import search_knowledge_base, find_relevant_kb_articles
from agent.classifier import classify, ClassificationResult


class Recommendation:
    def __init__(self):
        self.confidence: int = 0
        self.product: str = ""
        self.problem_category: str = ""
        self.suggested_answer: str = ""
        self.doc_links: list[str] = []
        self.clarifying_questions: list[str] = []
        self.urgency_level: int = 0
        self.notes_for_engineer: str = ""


def generate(text: str) -> Recommendation:
    rec = Recommendation()
    classification = classify(text)
    kb_results = search_knowledge_base(text)
    issue_results = find_relevant_kb_articles(text)

    # --- Product ---
    if classification.products:
        rec.product = ", ".join(classification.products)
    elif kb_results:
        rec.product = kb_results[0]["product"]
    else:
        rec.product = "Не удалось определить"

    # --- Category ---
    if classification.categories:
        rec.problem_category = ", ".join(classification.categories)
        # Category in Russian for engineer
        cat_names = {
            "licensing": "Лицензирование/активация",
            "transfer": "Загрузка проекта / Transfer",
            "server_issue": "Проблемы с сервером",
            "network": "Сетевые проблемы",
            "bus77_hardware": "Bus77 / CAN шина",
            "protocol_integration": "Интеграция протоколов",
            "project": "Проблемы с проектом",
            "panel_app": "Панели / i3 pro",
            "hardware_issue": "Аппаратные проблемы",
            "legacy_migration": "Legacy / Миграция",
        }
        rec.notes_for_engineer = f"Категория: {', '.join(cat_names.get(c, c) for c in classification.categories)}"
    else:
        rec.notes_for_engineer = "Категория не определена"

    # --- Urgency ---
    rec.urgency_level = classification.urgency
    if classification.urgency >= 4:
        rec.notes_for_engineer += " | ⚠️ КРИТИЧЕСКИЙ УРОВЕНЬ, требуется немедленная реакция!"
    elif classification.urgency >= 3:
        rec.notes_for_engineer += " | ⚠️ Срочный случай, рекомендуется приоритетная обработка"

    # --- Confidence ---
    confidence = 0
    if classification.products:
        confidence += 30
    if classification.categories:
        confidence += 20
    if kb_results:
        confidence += 20
    if issue_results:
        confidence += 15
    if len(text) > 100:
        confidence += 15
    rec.confidence = min(confidence, 100)

    # --- Knowledge base search results ---
    doc_links = set()
    for r in kb_results[:3]:
        link = r.get("doc_link", "")
        if link:
            doc_links.add(f"{r['product']}: {link}")
    for issue in issue_results[:2]:
        pass
    rec.doc_links = list(doc_links)

    if not doc_links and rec.product and rec.product != "Не удалось определить":
        base = "https://doc.iridi.com"
        rec.doc_links.append(f"Общая документация: {base}")

    # --- Clarifying questions ---
    rec.clarifying_questions = _get_clarifying_questions(classification, text)

    # --- Suggested answer ---
    rec.suggested_answer = _build_suggested_answer(classification, kb_results, issue_results, rec.doc_links)

    return rec


def _get_clarifying_questions(classification: ClassificationResult, text: str) -> list[str]:
    questions = []
    text_lower = text.lower()

    if not classification.products:
        questions.append("Какой продукт/систему вы используете? (iRidi Pro, Bus77 Home/Lite, iRidi SCADA?)")

    if "bus77" in text_lower or "bus 77" in text_lower:
        if classification.is_bus77_pro is None:
            questions.append("Уточните: у вас оборудование Bus77 Pro (черное) или Bus77 Lite (белое)?")
        questions.append("Какое ПО для настройки Bus77 используете? (Bus77 Home или Bus77 Lite?)")

    if any(c in classification.categories for c in ["licensing", "transfer", "server_issue"]):
        if classification.products:
            questions.append(f"Какая версия {classification.products[0]}?")
        else:
            questions.append("Какая версия ПО/прошивки?")

    if "transfer" in classification.categories:
        questions.append("Панель и компьютер с Transfer находятся в одной подсети?")
        questions.append("Есть ли активный firewall/антивирус на компьютере?")

    if "server_issue" in classification.categories:
        questions.append("Какая платформа сервера? (HS Server, NUC, Raspberry Pi, ProAV)")
        questions.append("Есть ли .sirpz файл? Загружен ли серверный проект?")

    if classification.urgency >= 3 and "объект" not in text_lower:
        questions.append("Какой тип объекта? (частный дом, офис, гостиница, другое)")

    return questions


def _build_suggested_answer(classification: ClassificationResult,
                             kb_results: list[dict],
                             issue_results: list[dict],
                             doc_links: list[str]) -> str:
    parts = []

    if classification.products:
        parts.append(f"Определён продукт: {', '.join(classification.products)}")

    if kb_results:
        top = kb_results[0]
        parts.append(f"Найден продукт в БЗ: {top['product']} ({top['type']}) — {top['description']}")

    if issue_results:
        top_issue = issue_results[0]
        parts.append(f"Похожая проблема: {top_issue['category']}")

    if classification.is_bus77_pro is not None:
        line = "Bus77 Pro (черное оборудование)" if classification.is_bus77_pro else "Bus77 Lite (белое оборудование)"
        parts.append(f"⚠️ ВНИМАНИЕ: {line}. Оборудование Pro и Lite НЕ взаимозаменяемо!")

    if doc_links:
        parts.append(f"\nСсылки:")
        for link in doc_links:
            parts.append(f"  • {link}")

    parts.append(f"\nРекомендуется: проверить раздел документации по ссылкам выше. "
                 f"При отсутствии решения — обратиться к инженеру L2.")

    return "\n".join(parts)
