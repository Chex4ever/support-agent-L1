"""
iRidi Support Agent — ассистент второй линии техподдержки.
 
Usage:
    # CLI mode
    python -m agent.main "Не работает iRidium transfer, не видит панель"

    # File mode
    python -m agent.main --file ticket.txt

    # Interactive mode
    python -m agent.main --interactive

    # Omnidesk mode (requires API token)
    python -m agent.main --ticket 12345
"""

import sys
import json
import argparse

from agent.recommender import generate
from agent.omnidesk_api import get_ticket


def format_recommendation(rec) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("РЕКОМЕНДАЦИЯ АГЕНТА ВТОРОЙ ЛИНИИ")
    lines.append("=" * 60)
    lines.append(f"Продукт:        {rec.product}")
    lines.append(f"Категория:      {rec.problem_category}")
    lines.append(f"Уверенность:    {rec.confidence}%")
    lines.append(f"Срочность:      {rec.urgency_level}/5")
    lines.append("")

    if rec.notes_for_engineer:
        lines.append("[ЗАМЕТКА ИНЖЕНЕРУ]:")
        lines.append(f"  {rec.notes_for_engineer}")
        lines.append("")

    if rec.suggested_answer:
        lines.append("[РЕКОМЕНДУЕМЫЙ ОТВЕТ]:")
        for line in rec.suggested_answer.split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    if rec.doc_links:
        lines.append("[ССЫЛКИ НА ДОКУМЕНТАЦИЮ]:")
        for link in rec.doc_links:
            lines.append(f"  * {link}")
        lines.append("")

    if rec.clarifying_questions:
        lines.append("[УТОЧНЯЮЩИЕ ВОПРОСЫ ПОЛЬЗОВАТЕЛЮ]:")
        for i, q in enumerate(rec.clarifying_questions, 1):
            lines.append(f"  {i}. {q}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def cli():
    parser = argparse.ArgumentParser(description="iRidi Support Agent L1")
    parser.add_argument("text", nargs="?", help="Текст обращения")
    parser.add_argument("--file", "-f", help="Файл с текстом обращения")
    parser.add_argument("--interactive", "-i", action="store_true", help="Интерактивный режим")
    parser.add_argument("--ticket", "-t", type=int, help="ID тикета в Omnidesk (требуется API токен)")
    parser.add_argument("--json", "-j", action="store_true", help="Вывод в JSON")
    args = parser.parse_args()

    text = ""

    if args.ticket:
        ticket = get_ticket(args.ticket)
        if ticket:
            text = f"{ticket.title}\n\n{ticket.description}"
        else:
            print(f"Не удалось получить тикет #{args.ticket}")
            return
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.interactive:
        print("iRidi Support Agent L1 (интерактивный режим)")
        print("Введите текст обращения (Ctrl+Z на пустой строке для завершения):")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        text = "\n".join(lines)
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        return

    if not text.strip():
        print("Нет текста для анализа")
        return

    rec = generate(text)

    if args.json:
        print(json.dumps({
            "product": rec.product,
            "problem_category": rec.problem_category,
            "confidence": rec.confidence,
            "urgency_level": rec.urgency_level,
            "suggested_answer": rec.suggested_answer,
            "doc_links": rec.doc_links,
            "clarifying_questions": rec.clarifying_questions,
            "notes_for_engineer": rec.notes_for_engineer,
        }, ensure_ascii=False, indent=2))
    else:
        print(format_recommendation(rec))


if __name__ == "__main__":
    cli()
