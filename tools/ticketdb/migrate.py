"""
One-time migration: populate database with known tickets and KB facts.
Run once after creating the database tables.

Usage:
    python -m tools.ticketdb.migrate
"""

from . import database as db


def migrate():
    db.init_db()

    tickets = _tickets()
    for t in tickets:
        existing = db.get_ticket(t["ticket_id"])
        if existing:
            db.update_ticket(t["ticket_id"], **t)
            print(f"  Updated ticket {t['ticket_id']}")
        else:
            db.create_ticket(**t)
            print(f"  Created ticket {t['ticket_id']}")

    kb_entries = _kb()
    for k in kb_entries:
        entry = db.create_kb(**k)
        if entry:
            print(f"  Created KB {k['category']}/{k['key']}")
        else:
            print(f"  Skipped existing KB {k['category']}/{k['key']}")

    print("Migration complete.")


def _tickets():
    return [
        {
            "ticket_id": "370-346871",
            "status": "in_progress",
            "priority": "high",
            "product": "droidVNC-NG",
            "client_name": "",
            "summary": "droidVNC-NG remote access on iRidiP10-T — always use fallback mode",
            "client_question": "Need VNC access without repeated MediaProjection permission prompts on iRidi panel",
            "research_summary": "droidVNC-NG uses EXTRA_FALLBACK_SCREEN_CAPTURE to bypass MediaProjection dialog. Patched APK to always use fallback and suppress upgrade-to-fast-mode prompt on client connect.",
            "reply_draft_path": "tickets/970-346871/files/reply_draft.txt",
            "reply_sent": 0,
            "related_files": [
                "tickets/970-346871/research.md",
                "tickets/970-346871/files/iRidi_Error.txt",
                "C:\\Users\\iRidi\\AppData\\Local\\Temp\\opencode\\droidvnc-ng-patched.apk",
            ],
            "notes": "APK compiled and signed with debug keystore. Java 21 at C:\\Program Files\\Android\\openjdk\\jdk-21.0.8. Need to verify jarsigner v1 works on Android 11+ for SDK 35 target.",
        },
        {
            "ticket_id": "971-734230",
            "status": "completed",
            "priority": "medium",
            "product": "iRidi",
            "client_name": "",
            "summary": "AES padding investigation — PKCS7 not applied for aligned data",
            "client_question": "How does iRidi's AES encryption handle padding?",
            "research_summary": "iRidi .Encode() uses PKCS7 padding only for non-aligned input (standard would force a full block). .Decode() auto-strips PKCS7. Key format is hex bytes via comma. CalculateHash accepts Array for binary data.",
            "reply_draft_path": "",
            "reply_sent": 0,
            "related_files": [
                "tickets/971-734230/",
            ],
            "notes": "Updated knowledge_base/iridi_script_api.md with Encryption API section.",
        },
        {
            "ticket_id": "886-267205",
            "status": "completed",
            "priority": "low",
            "product": "iRidi",
            "client_name": "",
            "summary": "Cloud/DHCP connectivity issues investigation",
            "client_question": "",
            "research_summary": "Investigated cloud and DHCP issues. Formal reply prepared: need DHCP logs, feature request declined.",
            "reply_draft_path": "tickets/886-267205/reply_formal.txt",
            "reply_sent": 0,
            "related_files": [
                "tickets/886-267205/",
            ],
            "notes": "",
        },
        {
            "ticket_id": "422-279121",
            "status": "completed",
            "priority": "medium",
            "product": "iRidi",
            "client_name": "",
            "summary": "Dynamic List token values cannot be updated programmatically",
            "client_question": "How to update token values inside a Dynamic List without recreating items?",
            "research_summary": "Dynamic List can't update Labels after creation. Advanced List breaks button State on tap. No workaround exists — recommended Static List or sacrificing button responsiveness.",
            "reply_draft_path": "",
            "reply_sent": 0,
            "related_files": [],
            "notes": "Conclusion: no solution.",
        },
    ]


def _kb():
    return [
        # ── iRidi Script ──
        {
            "category": "iridi_script",
            "key": "aes_padding_behavior",
            "value": ".Encode() uses PKCS7 bytes only for non-aligned input. For aligned input (16 bytes), no padding block is added. This is NOT standard RFC 2315 which always adds a full block.",
            "source": "ticket 971-734230, experiment",
        },
        {
            "category": "iridi_script",
            "key": "aes_key_format",
            "value": "Key/Vector format: hex bytes via comma. Example: '60,25,cd' = [0x60, 0x25, 0xcd]. Not decimal.",
            "source": "ticket 971-734230, experiment",
        },
        {
            "category": "iridi_script",
            "key": "calculate_hash_array",
            "value": "CalculateHash accepts Array as argument. Using String.fromCharCode with bytes >127 gives wrong hash.",
            "source": "ticket 971-734230, experiment",
        },
        {
            "category": "iridi_script",
            "key": "decode_auto_unpad",
            "value": ".Decode() automatically strips PKCS7 padding.",
            "source": "ticket 971-734230, experiment",
        },
        {
            "category": "iridi_script",
            "key": "dynamic_list_limitation",
            "value": "Dynamic List items cannot have their token values (Labels) updated programmatically after creation. Advanced List can update but button State resets on tap. No workaround — use Static List or sacrifice responsiveness.",
            "source": "ticket 422-279121",
        },
        {
            "category": "iridi_script",
            "key": "no_arrow_functions",
            "value": "iRidi Script does NOT support arrow/lambda functions, let/const, setTimeout/setInterval, or JSON. Use IR.SetTimeout, IR.SetInterval, IR.Log(). Server tags write via IR.GetServer().Set().",
            "source": "built-in constraint",
        },
        {
            "category": "iridi_script",
            "key": "ugly_number_fix",
            "value": "parseFloat with || default value is buggy when value is 0 (treated as falsy). Use isNaN() check instead. For floating-point artifacts (0.30000000000000004) use toFixed(n) or string match.",
            "source": "built-in constraint",
        },
        {
            "category": "iridi_script",
            "key": "panel_no_virtual_tags",
            "value": "Panel projects (i3 Pro): no virtual tags, no EVENT_TAG_CHANGE, no virtual driver type. Project tokens have no change events.",
            "source": "ticket 422-279121 investigation",
        },
        # ── Android ──
        {
            "category": "android",
            "key": "mediaprojection_not_persistent",
            "value": "Android 10+ MediaProjection permission is NOT stored between app restarts by design. Workaround: adb shell cmd appops set PKG PROJECT_MEDIA allow — but not guaranteed on all devices or across reboots.",
            "source": "ticket 370-346871, Android docs",
        },
        {
            "category": "android",
            "key": "droidvnc_fallback_mode",
            "value": "droidVNC-NG EXTRA_FALLBACK_SCREEN_CAPTURE uses AccessibilityService for screenshot capture. Slower but no MediaProjection dialog at startup. Patched APK: forced always-fallback + suppressed upgrade-to-fast-mode prompt.",
            "source": "ticket 370-346871",
        },
        # ── API ──
        {
            "category": "api",
            "key": "omnidesk_message_format",
            "value": "Omnidesk ticket messages API: keys are '0', '1'... with 'message': {...} nested under each. total_count at top level. Not a 'messages' array.",
            "source": "ticket practice",
        },
        {
            "category": "api",
            "key": "redmine_post_returns_404",
            "value": "Redmine API (https://redmine.iridi.nt): POST requests return 404 on success. DELETE returns 403. Use ?key= param for authentication.",
            "source": "ticket practice",
        },
        {
            "category": "api",
            "key": "domains_list",
            "value": "doc.iridi.com (Docusaurus), dev.iridi.com (mediawiki), iridi.omnidesk.ru (support), redmine.iridi.nt (bug tracker), wiki2.iridiummobile.net (old wiki).",
            "source": "project setup",
        },
        # ── General ──
        {
            "category": "general",
            "key": "apk_patching_toolchain",
            "value": "APK patching: apktool d -r → edit smali → apktool b → jarsigner with debug keystore. Java 21 at C:\\Program Files\\Android\\openjdk\\jdk-21.0.8. Apktool 2.11.0 at C:\\Users\\iRidi\\AppData\\Local\\Temp\\opencode\\apktool.jar.",
            "source": "ticket 370-346871",
        },
        {
            "category": "general",
            "key": "ocr_fallback",
            "value": "EasyOCR model download from GitHub releases timed out (objects.githubusercontent.com blocked). Fallback: OCR.space free API (apikey=helloworld).",
            "source": "project setup",
        },
        {
            "category": "general",
            "key": "iridi_server_headless_unsupported",
            "value": "iRidi Server/Studio runtime requires interactive Windows desktop (GUI). No headless/CLI mode available.",
            "source": "project setup",
        },
    ]


if __name__ == "__main__":
    migrate()
