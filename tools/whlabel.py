#!/usr/bin/env python3
"""Rebrand the Home Assistant Android app as "Sentinel" (in.tezsolutions.sentinel).

Idempotent. Run from anywhere; operates on the repo that contains this file (tools/..).

    python3 tools/whlabel.py            # code + strings rebrand
    python3 tools/brand/fetch_brand.py  # logos (run this too; see tools/brand/brand.json)
    python3 tools/whlabel.py --check    # exit 1 if anything was left to change / leftovers found

Scope: DISPLAY identity only. Kotlin source packages (io.homeassistant.companion.android.*) are
kept on purpose so upstream merges stay cheap. Server-facing identifiers that must keep working
against stock Home Assistant (e.g. "Home Assistant Core" update entities) are left alone.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_APP_ID = "in.tezsolutions.sentinel"
OLD_APP_ID = "io.homeassistant.companion.android"
BRAND = "Sentinel"
SCHEME = "sentinel"
SUPPORT_URL = "https://sentinel.tezsolutions.in"  # single target for every help/docs/privacy link

changed = []


def write(path: Path, text: str):
    if path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))


def sub(rel: str, old: str, new: str, optional=False):
    """Exact-string replace. Idempotent: already-applied is fine, neither present is an error."""
    p = ROOT / rel
    if not p.exists():
        if optional:
            return
        sys.exit(f"missing file {rel}")
    t = p.read_text(encoding="utf-8")
    if old in t:
        write(p, t.replace(old, new))
    elif new not in t and not optional:
        sys.exit(f"{rel}: neither old nor new text found for: {old[:70]!r}")


def add_import(rel: str, imp: str):
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    line = f"import {imp}\n"
    if line in t:
        return
    imports = list(re.finditer(r"^import .*\n", t, re.M))
    pos = imports[-1].end()
    write(p, t[:pos] + line + t[pos:])


# ---------------------------------------------------------------- 1. application id
def app_id():
    plugin = "build-logic/convention/src/main/kotlin/AndroidApplicationConventionPlugin.kt"
    # The namespace (R, BuildConfig package) must stay io.homeassistant...; only applicationId changes.
    sub(plugin, f'private const val APPLICATION_ID = "{OLD_APP_ID}"',
        f'private const val NAMESPACE = "{OLD_APP_ID}"\nprivate const val APPLICATION_ID = "{NEW_APP_ID}"')
    sub(plugin, "namespace = APPLICATION_ID", "namespace = NAMESPACE")
    # app id sent to the server on registration (push routing key)
    sub("common/src/main/kotlin/io/homeassistant/companion/android/common/data/integration/impl/IntegrationRepositoryImpl.kt",
        f'private const val APP_ID = "{OLD_APP_ID}"', f'private const val APP_ID = "{NEW_APP_ID}"')
    sub("common/src/main/kotlin/io/homeassistant/companion/android/common/data/integration/impl/IntegrationRepositoryImpl.kt",
        'private const val APP_NAME = "Home Assistant"', f'private const val APP_NAME = "{BRAND}"')
    sub("common/src/main/kotlin/io/homeassistant/companion/android/common/data/HomeAssistantApis.kt",
        'USER_AGENT_STRING = "Home Assistant/', f'USER_AGENT_STRING = "{BRAND}/')
    sub("app/src/main/kotlin/io/homeassistant/companion/android/util/DataUriDownloadManager.kt",
        'var generated = "Home Assistant ', f'var generated = "{BRAND} ')


# ---------------------------------------------------------------- 2. strings
# "Home Assistant X" where X names a server-side product/entity stays as is.
KEEP = r"(?! (?:Core|Supervisor|OS|Operating System|Cloud|Container|Green|Yellow|Connect)\b)"
# strings also use a literal \u00A0 (non-breaking space) between the words
HA_RE = re.compile(r"Home(?: |\\u00A0|\u00A0)Assistant" + KEEP)


def strings():
    n = 0
    for p in ROOT.glob("*/src/main/res/values*/strings.xml"):
        t = p.read_text(encoding="utf-8")
        new = HA_RE.sub(BRAND, t)
        if new != t:
            write(p, new)
            n += 1
    return n


# ---------------------------------------------------------------- 2b. marketing copy + links
# Strings whose wording is Home Assistant marketing, not just a name: rewritten, not substituted.
COPY = {
    "welcome_details": "Access your Sentinel node on the go.\\n\\nSentinel keeps your cameras and automations "
                       "on your own hardware, with local control and privacy first. Connect this app to your node "
                       "to view and control it from anywhere.",
    "sensor_privacy": "You have full control over your data. When enabled, sensor data is only sent to your own "
                      "Sentinel server. It will never be shared with Tez Solutions or third parties.",
    "location_secure_connection_hint": "This data will never be shared with Tez Solutions or third parties.",
}
URL_RE = re.compile(r'https://(?:companion|www|community)\.home-assistant\.io[^"<\s]*')


def copy_and_links():
    p = ROOT / "common/src/main/res/values/strings.xml"
    t = p.read_text(encoding="utf-8")
    for name, text in COPY.items():
        t, n = re.subn(rf'(<string name="{name}">).*?(</string>)', lambda m: m.group(1) + text.replace("'", "\\'") + m.group(2), t, flags=re.S)
        if n != 1:
            sys.exit(f"string {name} not found")
    write(p, t)
    for p in list(ROOT.glob("*/src/main/**/*.kt")) + list(ROOT.glob("*/src/main/res/**/*.xml")):
        t = p.read_text(encoding="utf-8")
        new = URL_RE.sub(SUPPORT_URL, t)
        if new != t:
            write(p, new)


# ---------------------------------------------------------------- 3. deep links
def deep_links():
    sub("app/src/main/kotlin/io/homeassistant/companion/android/launch/link/LinkHandler.kt",
        'HA_DEEP_LINK_SCHEME = "homeassistant"', f'HA_DEEP_LINK_SCHEME = "{SCHEME}"')
    for p in list(ROOT.glob("*/src/main/AndroidManifest.xml")) + list(ROOT.glob("*/src/*/AndroidManifest.xml")):
        t = p.read_text(encoding="utf-8")
        write(p, t.replace('android:scheme="homeassistant"', f'android:scheme="{SCHEME}"'))
    for p in ROOT.glob("*/src/main/**/*.kt"):
        t = p.read_text(encoding="utf-8")
        if "homeassistant://" in t:
            write(p, t.replace("homeassistant://", f"{SCHEME}://"))


# ---------------------------------------------------------------- 4. server verification
CC = "common/src/main/kotlin/io/homeassistant/companion/android/common/data/connectivity/DefaultConnectivityChecker.kt"


def connectivity():
    """A rebranded server serves its own PWA name ("Tez Home", "Sentinel"...), so recognise a
    Home Assistant frontend by its stable manifest id instead of requiring name == "Home Assistant"."""
    sub(CC, "private data class ManifestResponse(val name: String? = null) {\n    fun isHomeAssistant(): Boolean = name == HOME_ASSISTANT_NAME\n",
        "private data class ManifestResponse(val name: String? = null, val id: String? = null) {\n"
        "    // Whitelabeled servers change the name; the manifest id is stable.\n"
        "    fun isHomeAssistant(): Boolean = name == HOME_ASSISTANT_NAME || id == HOME_ASSISTANT_MANIFEST_ID\n")
    if "HOME_ASSISTANT_MANIFEST_ID = " not in (ROOT / CC).read_text(encoding="utf-8"):
        sub(CC, '        private const val HOME_ASSISTANT_NAME = "Home Assistant"\n',
            '        private const val HOME_ASSISTANT_NAME = "Home Assistant"\n'
            '        private const val HOME_ASSISTANT_MANIFEST_ID = "/?homescreen=1"\n')


# ---------------------------------------------------------------- 5. in-app logo (Compose)
APP = "app/src/main/kotlin/io/homeassistant/companion/android/"
LOGO_VECTOR_RE = re.compile(r"imageVector = ImageVector\.vectorResource\((?:R|commonR)\.drawable\.(ic_home_assistant_branding|app_icon_launch)\)")


def logo_usage():
    for rel in ("onboarding/welcome/WelcomeTemplate.kt", "onboarding/serverdiscovery/ServerDiscoveryScreen.kt",
                "onboarding/connection/ConnectionScreen.kt", "launch/link/LinkActivity.kt", "loading/LoadingScreen.kt"):
        p = ROOT / APP / rel
        t = p.read_text(encoding="utf-8")
        new = LOGO_VECTOR_RE.sub("painter = painterResource(R.drawable.ic_sentinel_logo)", t)
        if new != t:
            write(p, new)
            add_import(APP + rel, "androidx.compose.ui.res.painterResource")
    # loading screen: HA's three animated dots no longer exist in the logo
    p = ROOT / APP / "loading/LoadingScreen.kt"
    t = p.read_text(encoding="utf-8")
    t2 = re.sub(r"\n            \.drawWithContent \{.*?\n            \},\n", "\n", t, flags=re.S)
    t2 = t2.replace("    val dotScales = logoDotScales()\n", "")
    write(p, t2)
    # remaining references to the old vectors
    for rel in ("app/src/main/kotlin/io/homeassistant/companion/android/widgets/todo/TodoGlanceAppWidget.kt",
                "app/src/main/res/drawable-v26/launch_screen_background.xml"):
        sub(rel, "app_icon_launch\"", "ic_sentinel_logo\"", optional=True)
        sub(rel, "R.drawable.app_icon_launch)", "R.drawable.ic_sentinel_logo)", optional=True)
    sub("app/src/main/res/values-v31/styles.xml", "@drawable/app_icon_launch_screen", "@drawable/ic_sentinel_splash")
    for stale in ("drawable/app_icon_launch.xml", "drawable/ic_home_assistant_branding.xml",
                  "drawable-v31/app_icon_launch_screen.xml"):
        f = ROOT / "app/src/main/res" / stale
        if f.exists():
            f.unlink()
            changed.append(f"deleted {stale}")


def leftovers():
    """Report remaining user-facing 'Home Assistant' in resources (code comments/logs are ignored)."""
    bad = []
    for p in ROOT.glob("*/src/main/res/**/*.xml"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        for m in HA_RE.finditer(t):
            bad.append(f"{p.relative_to(ROOT)}: ...{t[max(0, m.start() - 30):m.end() + 20]!r}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    app_id()
    n = strings()
    copy_and_links()
    deep_links()
    connectivity()
    logo_usage()
    print(f"strings files rebranded: {n}; files changed: {len(changed)}")
    for c in changed[:60]:
        print("  ", c)
    left = leftovers()
    print(f"leftover 'Home Assistant' in resources: {len(left)}")
    for l in left[:20]:
        print("  ", l)
    if args.check and (changed or left):
        sys.exit(1)


if __name__ == "__main__":
    main()
