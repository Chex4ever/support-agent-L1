# Серверное оборудование iRidi

## HS Server

| Характеристика | Значение |
|---------------|----------|
| Процессор | RK3399 |
| RAM | 2GB DDR4 |
| Накопитель | 16GB eMMC |
| Интерфейсы | RS-485, RS-232, KNX TP1-256, CAN (Bus77), Ethernet |
| Макс. панелей | 25 |
| Макс. тэгов | 3000+ (рекомендуется ≤7000) |
| Назначение | Основной сервер, замена UMC C3 |

**Внимание**: HS Server НЕ совместим с UMC C3 по разъемам! Другое напряжение питания (2.5W vs 30W), другой pinout.

### Роли HS Server (в зависимости от ПО/лицензии)
- Bus77 Home Server
- Bus77 Integration Server
- iRidi Pro Server
- KNX Home Server

## ProAV Control Processor

| Характеристика | Advanced (PX-VP100-Advanced) | Basic (PX-VM20-Basic) |
|---------------|------------------------------|----------------------|
| Процессор | RK3399 | RK3399 |
| RAM | 2GB DDR4 | 2GB DDR4 |
| Интерфейсы | 2x CAN, KNX, 2x RS-485/232, 6x RS-232, 10 inputs, 10 relays, 8 IR out, IR in | 1x CAN, KNX, 1x RS-485/232, 2x RS-232, 2 inputs, 2 relays, 2 IR out, IR in |
| Форм-фактор | 1U rack | Компактный |
| Макс. панелей | 25 | 25 |
| Макс. тэгов | до 7000 | до 7000 |

## Raspberry Pi 3

| Характеристика | Значение |
|---------------|----------|
| CPU | BCM2837, 1GB RAM |
| Макс. панелей | 15 |
| Макс. тэгов | 3000+ (≤5000) |
| Примечание | Только для небольших проектов |

## Intel NUC

| Характеристика | Windows | Linux |
|---------------|---------|-------|
| CPU | Celeron/Core i3/i5/i7 | Celeron/Core i3/i5/i7 |
| RAM | ≥4GB | ≥4GB |
| Макс. панелей | 50 | 50 |
| Макс. тэгов | 6000+ (≤12000) | 6000+ (≤12000) |

## Legacy оборудование (архив)

- **UMC C2** — старый контроллер
- **UMC C3** — заменен на HS Server
- **UMC C4** (HDL IntelliCenter 2) — заменен на HS Server

## Связанные страницы
- [HS Server](https://doc.iridi.com/Оборудование/Серверы/IRidi_HS_Server)
- [ProAV Advanced](https://doc.iridi.com/Оборудование/Серверы/IRidi_ProAV_Advanced)
- [ProAV Basic](https://doc.iridi.com/Оборудование/Серверы/IRidi_ProAV_Basic)
- [UMC Spec (архив)](https://doc.iridi.com/Системы управления/Архив/UMC_Spec)
