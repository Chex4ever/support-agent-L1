# apk_patching_toolchain

**Категория:** Общее (инструменты, окружение)
**Источник:** ticket 370-346871

---

APK patching toolchain (Windows): read original APK entries into memory -> patch .so in memory -> write new ZIP preserving original filenames+case -> zipalign -p 4 -> apksigner (v2+v3). NO apktool needed for dex. NO disk extraction (Windows case-insensitive FS causes resource collisions). Use Python zipfile, process all entries in RAM (~10 MB). Key constraints: .so files must be STORED (page alignment), resources.arsc must be STORED (Android 11+).