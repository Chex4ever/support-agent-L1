# AES через IR.CreateEncryption

Примеры: `tickets/971-734230/files/aes_padding_test.js`, `tickets/971-734230/research.md`.

## Правила

- iRidi дополняет данные до 16 байт, но только если нужно (не PKCS7).
- Ручной PKCS7 перед `.Encode()` — правильный подход.
- `.Decode()` стриппит PKCS7 автоматически.
- `IR.CalculateHash` принимает Array как аргумент.

## BookStack

- `omnigent-znaniia-ai-agenta/pages/iridi-script-aes-padding-behavior.md`
- `omnigent-znaniia-ai-agenta/pages/iridi-script-aes-key-format.md`
- `omnigent-znaniia-ai-agenta/pages/iridi-script-decode-auto-unpad.md`
- `omnigent-znaniia-ai-agenta/pages/iridi-script-calculate-hash-array.md`
