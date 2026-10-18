#!/usr/bin/env python3
"""Regression audit: nothing user-visible may still say Home Assistant / Open Home Foundation / Nabu Casa.

    python3 tools/brand_audit.py                 # source checks (CI, fast)
    python3 tools/brand_audit.py --apk app.apk   # + compiled resource table and manifest of a built APK
                                                 #   (aapt2 from $AAPT2, $ANDROID_HOME/build-tools/*/aapt2 or PATH)

Exit 1 on any finding. Each check names the file so the fix is obvious. Run after every upstream merge.
What is deliberately NOT flagged: Timber/Log lines, comments, @HAPreviews text, the server-protocol constant
HOME_ASSISTANT_NAME, Kotlin package names, and contributors.home-assistant.io developer links in code.
"""
import argparse, glob, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAK = re.compile(r"Home(?: |\u00a0|\\u00A0)Assistant|Open Home Foundation|Nabu ?Casa|openhomefoundation|nabucasa|"
                  r"(?:companion|www|community)\.home-assistant\.io", re.I)
KT_SKIP = re.compile(r"Timber\.|Log\.[a-z]\(|^\s*(\*|//|/\*)|const val HOME_ASSISTANT_NAME|HOME_ASSISTANT_MANIFEST")
# (file suffix, text) pairs that are developer-facing, never shown to users. Keep this list short and justified.
ALLOW = [
    ("frontend/WebViewAction.kt", "Legacy fallback for Home Assistant servers"),   # KDoc-style deprecation reason
    ("onboarding/OnboardingActivity.kt", "requestInstances:"),                      # wear debug log text
]
KT_SRC = ["app/src/main", "common/src/main", "wear/src/main", "automotive/src/main"]
fails = []


def fail(check, where, what=""):
    fails.append(f"FAIL  {check}: {where} {what}".rstrip())


def strings_xml():
    """Every locale of every module: user-visible text."""
    for f in glob.glob(str(ROOT / "*/src/*/res/values*/*.xml")):
        t = Path(f).read_text(encoding="utf-8")
        for m in re.finditer(r'<string name="([^"]+)"[^>]*>(.*?)</string>', t, re.S):
            if LEAK.search(m.group(2)):
                fail("string resource", f"{os.path.relpath(f, ROOT)}:{m.group(1)}", m.group(2)[:70].replace("\n", " "))


def kotlin_literals():
    in_preview = False
    for d in KT_SRC:
        for f in glob.glob(str(ROOT / d / "**/*.kt"), recursive=True):
            lines = Path(f).read_text(encoding="utf-8").splitlines()
            preview_depth = None
            for n, line in enumerate(lines, 1):
                if "@HAPreviews" in line or "@Preview" in line:
                    preview_depth = n
                if preview_depth and n - preview_depth < 40:
                    continue  # preview text never ships to users
                if '"' in line and LEAK.search(line) and not KT_SKIP.search(line) \
                        and not any(f.endswith(a) and b in line for a, b in ALLOW):
                    fail("kotlin literal", f"{os.path.relpath(f, ROOT)}:{n}", line.strip()[:90])
            if "showBrand = true" in "\n".join(lines):
                fail("OHF footer", os.path.relpath(f, ROOT), "passes showBrand = true")


def identity():
    plugin = (ROOT / "build-logic/convention/src/main/kotlin/AndroidApplicationConventionPlugin.kt").read_text()
    if 'APPLICATION_ID = "in.tezsolutions.sentinel"' not in plugin:
        fail("identity", "AndroidApplicationConventionPlugin.kt", "applicationId is not in.tezsolutions.sentinel")
    names = [Path(f).read_text(encoding="utf-8") for f in glob.glob(str(ROOT / "common/src/main/res/values/strings.xml"))]
    if not names or not re.search(r'<string name="app_name"[^>]*>Sentinel</string>', names[0]):
        fail("identity", "common/.../values/strings.xml", "app_name is not Sentinel")
    man = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    if 'android:scheme="homeassistant"' in man:
        fail("deep link", "app/src/main/AndroidManifest.xml", "still handles the homeassistant:// scheme")


def apk(path):
    aapt2 = os.environ.get("AAPT2") or shutil.which("aapt2")
    if not aapt2:
        c = sorted(glob.glob(os.path.expandvars("$ANDROID_HOME/build-tools/*/aapt2")))
        aapt2 = c[-1] if c else None
    if not aapt2:
        fail("apk", path, "aapt2 not found (set AAPT2 or ANDROID_HOME)")
        return
    run = lambda *a: subprocess.run([aapt2, *a, path], capture_output=True, text=True).stdout
    badging = run("dump", "badging")
    if not re.search(r"^package: name='in\.tezsolutions\.sentinel", badging, re.M):
        fail("apk", "package", "not in.tezsolutions.sentinel*")
    if "application-label:'Sentinel'" not in badging:
        fail("apk", "label", "application-label is not Sentinel")
    for line in run("dump", "strings").splitlines():
        if LEAK.search(line):
            fail("apk resource table", line.strip()[:110])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk")
    a = ap.parse_args()
    strings_xml(); kotlin_literals(); identity()
    if a.apk:
        apk(a.apk)
    print("\n".join(fails) if fails else "PASS  brand audit: no Home Assistant / OHF / Nabu Casa text found")
    print(f"{len(fails)} finding(s)")
    sys.exit(1 if fails else 0)
