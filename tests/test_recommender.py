from agent.recommender import generate


def test_licensing_recommendation():
    text = "Не работает лицензия на iRidium server. Пишет wrong ID. HWID каждый раз разный."
    rec = generate(text)
    assert "iRidium server" in rec.product or "iRidi Pro" in rec.product
    assert rec.confidence > 0
    assert len(rec.doc_links) > 0 or rec.suggested_answer


def test_bus77_recommendation():
    text = "Bus77 Home не видит устройства. Оборудование черное."
    rec = generate(text)
    assert len(rec.clarifying_questions) > 0
    assert any("Bus77" in q for q in rec.clarifying_questions)


def test_empty_input():
    text = ""
    rec = generate(text)
    assert rec.product == "Не удалось определить"
    assert rec.confidence < 50
