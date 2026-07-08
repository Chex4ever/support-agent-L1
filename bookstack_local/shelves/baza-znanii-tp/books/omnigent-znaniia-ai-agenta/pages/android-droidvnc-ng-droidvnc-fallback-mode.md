# droidvnc_fallback_mode

**Категория:** Android / droidVNC-NG
**Источник:** ticket 370-346871

---

droidVNC-NG EXTRA_FALLBACK_SCREEN_CAPTURE is NOT forced. SMALI patches reverted. Fallback is only used when app-op PROJECT_MEDIA is denied (stock behavior). Native .so patch only (rfbMaxClientWait 5->60s).