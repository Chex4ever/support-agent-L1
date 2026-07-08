# bacnet_ede_23_to_21

**Категория:** Интеграции (BACnet, Modbus, HDL, Rapix)
**Источник:** ticket 591-266500

---

BACnet EDE layout 2.3 (Rapix) -> 2.1 (iRidi). Rapix exports EDE 2.3 (comma-sep, 17 columns with notification-class). iRidi Studio supports only EDE 2.1 (semicolon-sep, 16 columns, #-prefixed headers). Convert: drop notification-class, comma->semicolon, add # prefix, add mandatory/optional row, set VERSION_OF_LAYOUT to 2.1.