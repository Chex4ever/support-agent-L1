import re
from typing import Optional

PRODUCT_PATTERNS = [
    # iRidi Pro ecosystem
    (r"iridium\s*studio|iridium_studio|studio\s+iridi", "iRidium studio"),
    (r"\bi3[\s_-]?pro\b|\bi3pro\b", "i3 pro"),
    (r"iridium\s*server|\biridium[\s_-]server\b", "iRidium server"),
    (r"iridium\s*transfer|\btransfer\b", "iRidium transfer"),
    (r"iridi\s*pro|iridium\s*pro|\biridi\s+pro\b", "iRidi Pro"),
    (r"\biridi\s+scada\b|scada", "iRidi SCADA"),

    # Bus77
    (r"bus77\s*home|bus77[\s_-]home", "Bus77 Home"),
    (r"bus77\s*lite|\bbus77[\s_-]lite\b", "Bus77 Lite"),
    (r"\bbus77\b|\bbus\s*77\b|басовка|басс", "Bus77"),

    # Hardware
    (r"\bhs[\s_-]?server\b", "HS Server"),
    (r"proav|px[\s_-]vp100|px[\s_-]vm20", "ProAV"),
    (r"raspberry\s*pi\s*3|rpi3|rpi\s*3", "Raspberry Pi 3"),
    (r"\bnuc\b|intel\s*nuc", "Intel NUC"),

    # Panels
    (r"\bp6\b|6[\s-]*дюйм", "P6"),
    (r"\bp7\b|7[\s-]*дюйм", "P7"),
    (r"\bp8\b|8[\s-]*дюйм", "P8"),
    (r"\bp10\b|10[\s-]*дюйм", "P10"),

    # Bus77 equipment lines
    (r"bus77\s*pro|pro\s*оборудование", "Bus77 Pro"),
    (r"bus77\s*lite\s*оборудование|lite\s*оборудование", "Bus77 Lite"),

    # Legacy
    (r"\bumc[\s_-]?c2\b", "UMC C2"),
    (r"\bumc[\s_-]?c3\b", "UMC C3"),
    (r"\bumc[\s_-]?c4\b", "UMC C4"),
    (r"\bi3[\s_-]?lite\b|iridium[\s_-]lite", "i3 Lite"),

    # Cloud
    (r"iridium\s*cloud|облако", "iRidium Cloud"),
]

CATEGORY_PATTERNS = [
    (r"(лиценз|активац|license|wrong\s*id|hwid|ключа?\b)", "licensing"),
    (r"(transfer|загрузк|прошивк|upload|update)", "transfer"),
    (r"(сервер|server|не\s*стартует|не\s*запускается|error\s*core|web[\s-]?интерфейс)", "server_issue"),
    (r"(сеть|network|подключен|ip|подсет|маршрут|vlan|wifi|ethernet)", "network"),
    (r"(can|bus77|шина|терминир|резистор)", "bus77_hardware"),
    (r"(knx|modbus|dali|bacnet|mqtt|hdl|crestron|amx|helvar|domintell|lutron|global\s*cache|z[\s_-]?wave|zigbee)",
     "protocol_integration"),
    (r"(проект|project|\.irpz|\.sirpz|\.pirpz|gui|интерфейс|visualization)", "project"),
    (r"(панел|panel|touch|i3\s*pro|crashes|черн\w*\s*экран|black\s*screen)", "panel_app"),
    (r"(желез|hardware|пита|не\s*включается|не\s*работает\s*устройств)", "hardware_issue"),
    (r"(старый|legacy|миграц|переход|v1\.5|v2\.0|i2control)", "legacy_migration"),
]

URGENCY_PATTERNS = [
    (r"(пожар|авария|критическ)", 5),
    (r"(не\s*работает\s*все|все\s*не\s*работает|полностью)", 4),
    (r"(срочн|вчера|немедленн|urgent|asap|срок)", 3),
    (r"(клиент|заказчик)\s*(давит|звонит|требует|недовол)", 3),
    (r"(гостиниц|отель|больниц|госпиталь|клиник|аэропорт)", 2),
    (r"(офис|магазин|ресторан|кафе|production)", 1),
]


class ClassificationResult:
    def __init__(self):
        self.products: list[str] = []
        self.categories: list[str] = []
        self.urgency: int = 0
        self.urgency_reason: str = ""
        self.is_iridi_scada: bool = False
        self.is_bus77_pro: Optional[bool] = None
        self.is_software_issue: Optional[bool] = None

    def __repr__(self):
        return (f"Classification("
                f"products={self.products}, "
                f"categories={self.categories}, "
                f"urgency={self.urgency})")


def classify(text: str) -> ClassificationResult:
    result = ClassificationResult()
    text_lower = text.lower()

    for pattern, product_name in PRODUCT_PATTERNS:
        if re.search(pattern, text_lower):
            if product_name not in result.products:
                result.products.append(product_name)

    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, text_lower):
            if category not in result.categories:
                result.categories.append(category)

    max_urgency = 0
    reason = ""
    for pattern, level in URGENCY_PATTERNS:
        if re.search(pattern, text_lower):
            if level > max_urgency:
                max_urgency = level
                reason = pattern
    result.urgency = max_urgency
    result.urgency_reason = reason

    if "scada" in text_lower:
        result.is_iridi_scada = True

    if any(kw in text_lower for kw in ["pro оборудование", "bus77 pro", "pro черный", "черное", "черный"]):
        result.is_bus77_pro = True
    elif any(kw in text_lower for kw in ["lite оборудование", "bus77 lite", "lite белый", "белое", "белый"]):
        result.is_bus77_pro = False

    if any(kw in text_lower for kw in ["установк", "настройк", "конфигур", "загрузк", "обновлен"]):
        result.is_software_issue = True
    elif any(kw in text_lower for kw in ["сломал", "не включа", "индикатор", "провод", "разъем"]):
        result.is_software_issue = False

    return result
