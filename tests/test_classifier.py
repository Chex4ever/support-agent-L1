from agent.classifier import classify


def test_classify_licensing():
    text = "Не работает лицензия на iRidium server. Пишет wrong ID при активации. HWID разный."
    result = classify(text)
    assert "iRidium server" in result.products
    assert "licensing" in result.categories


def test_classify_bus77_pro():
    text = "Bus77 Home не видит устройства. Оборудование черное, HS Server."
    result = classify(text)
    assert "Bus77 Home" in result.products
    assert "HS Server" in result.products
    assert "Bus77" in result.products
    assert result.is_bus77_pro is True


def test_classify_transfer():
    text = "iRidium transfer не находит панель в сети"
    result = classify(text)
    assert "iRidium transfer" in result.products
    assert "transfer" in result.categories


def test_classify_iridi_pro():
    text = "Проблема с iRidi Pro, i3 pro вылетает при загрузке проекта"
    result = classify(text)
    assert "i3 pro" in result.products or "iRidi Pro" in result.products


def test_urgency_critical():
    text = "Пожарная сигнализация не работает, объект горит!"
    result = classify(text)
    assert result.urgency >= 4


def test_no_false_firewall():
    text = "Firewall отключен, но Transfer не работает"
    result = classify(text)
    assert result.urgency == 0
