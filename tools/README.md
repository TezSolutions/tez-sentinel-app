# Sentinel App tooling

Fork of home-assistant/android, rebranded as **Sentinel** (`in.tezsolutions.sentinel`).
`main` mirrors upstream; `sentinel` = upstream + the output of these scripts.

    python3 tools/whlabel.py                       # identity, strings, deep links, server check
    ~/tools/pyb/bin/python tools/brand/fetch_brand.py   # logos from GitHub (pinned in brand.json)
    python3 tools/whlabel.py --check               # CI: fails if a re-run would change anything

Both scripts are idempotent. After merging upstream, re-run them and build.
Kotlin packages and the Gradle `namespace` stay `io.homeassistant.companion.android` on purpose.
Logo source/pin: `tools/brand/brand.json` (TezSolutions/TezSentinel, HA/config/www/tez_sentinel/logo.png).

    python3 tools/brand_audit.py [--apk app.apk]   # regression: fails on any visible Home Assistant / Open Home Foundation / Nabu Casa text,
                                                   # showBrand = true, wrong applicationId/app_name, homeassistant:// scheme (runs in CI)
