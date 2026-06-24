from agent.knowledge_base import load_products, search_knowledge_base


def test_load_products():
    products = load_products()
    assert len(products) > 0
    names = [p.name for p in products]
    assert "iRidium server" in names
    assert "HS Server" in names


def test_search_iridium():
    results = search_knowledge_base("iRidium server не работает")
    assert len(results) > 0
    assert any("iRidium server" in r["product"] for r in results)


def search_bus77():
    results = search_knowledge_base("Bus77 Home проблема с подключением")
    assert len(results) > 0
    assert any("Bus77 Home" in r["product"] for r in results)
