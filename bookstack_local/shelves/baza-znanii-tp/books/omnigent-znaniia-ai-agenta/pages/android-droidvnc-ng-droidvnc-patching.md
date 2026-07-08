# droidvnc_patching

**Категория:** Android / droidVNC-NG
**Источник:** ticket 370-346871

---

droidVNC-NG 2.20.0 patching: ONLY native lib patch rfbMaxClientWait=5000->60000ms via MOVZ W8 instruction at .so offset 0x2cf34 (arm64-v8a). SMALI patches REVERTED — APK uses original dex files, behavior identical to stock. Build process: read original APK into memory, patch .so data, repack ZIP (no disk extraction — Windows case-insensitive FS corrupts APK files). resources.arsc must be STORED (Android 11+ requirement).