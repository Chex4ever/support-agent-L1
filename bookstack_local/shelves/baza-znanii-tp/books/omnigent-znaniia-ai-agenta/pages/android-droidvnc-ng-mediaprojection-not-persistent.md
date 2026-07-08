# mediaprojection_not_persistent

**Категория:** Android / droidVNC-NG
**Источник:** ticket 370-346871, Android docs

---

Android 10+ MediaProjection permission is NOT stored between app restarts by design. Workaround: adb shell cmd appops set PKG PROJECT_MEDIA allow — but not guaranteed on all devices or across reboots.