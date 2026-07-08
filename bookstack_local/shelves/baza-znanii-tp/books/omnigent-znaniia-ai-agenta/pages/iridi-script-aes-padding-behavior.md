# aes_padding_behavior

**Категория:** iRidi Script
**Источник:** ticket 971-734230, experiment

---

.Encode() uses PKCS7 bytes only for non-aligned input. For aligned input (16 bytes), no padding block is added. This is NOT standard RFC 2315 which always adds a full block.