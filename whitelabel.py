import os
import re

# --- CONFIGURATION ---
# These are the values you provided
NEW_PACKAGE_ID = "in.tezsolutions.sentinel"
NEW_APP_NAME = "Tez Sentinel"
OLD_BRAND_NAME = "Home Assistant"

# Updated with the color from your logo!
# This will replace the old blue (#03A9F4) with your new gold (#f2c588)
COLORS_TO_REPLACE = {
    "#03A9F4": "#f2c588"
}
# ---------------------

def whitelabel_project(root_dir):
    if not os.path.exists(root_dir):
        print(f"Error: Directory '{root_dir}' not enough.")
        return

    print(f"🚀 Starting whitelabeling for: {NEW_APP_NAME}")
    print(f"📦 Target Package ID: {NEW_PACKAGE_ID}")
    print("--------------------------------------------------")

    stats = {"files_changed": 0, "replacements": 0}

    for root, dirs, files in os.walk(root_dir):
        # Skip build and git directories
        if any(exclude in root for exclude in ['.git', '.gradle', 'build', 'out', 'bin']):
            continue

        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1]

            # We only care about text-based configuration/resource files
            if ext not in ['.kts', '.gradle', '.xml', '.kt', '.java', '.properties']:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if not content:
                    continue
                    
                original_content = content
                
                # 1. Replace Brand Name (Textual)
                if OLD_BRAND_NAME in content:
                    content = content.replace(OLD_BRAND_NAME, NEW_APP_NAME)
                    stats["replacements"] += 1

                # 2. Replace Package ID (for Gradle files)
                if ext in ['.kts', '.gradle']:
                    id_pattern = r'applicationId\s*\(?["\']([^"\']+)["\']\)?'
                    match = re.search(id_pattern, content)
                    if match:
                        old_id = match.param if hasattr(match, 'param') else match.group(1)
                        # Simple replacement for the specific ID
                        content = content.replace(f'"{old_id}"', f'"{NEW_PACKAGE_ID}"')
                        content = content.replace(f"'{old_id}'", f"'{NEW_PACKAGE_ID}'")
                        stats["replacements"] += 1

                # 3. Replace App Name in strings.xml specifically
                if file == "strings.xml":
                    app_name_pattern = r'(<string name="app_name">)(.*?)(</string>)'
                    content = re.sub(app_name_pattern, rf'\1{NEW_APP_NAME}\3', content)

                # 4. Apply Color Replacements
                for old_hex, new_hex in COLORS_TO_REPLACE.items():
                    if old_hex in content:
                        content = content.replace(old_hex, new_hex)
                        stats["replacements"] += 1

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Updated: {os.path.relpath(file_path, root_dir)}")
                    stats["files_changed"] += 1

            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")

    print("--------------------------------------------------")
    print(f"✨ Whitelabeling Complete!")
    print(f"📊 Files modified: {stats['files_changed']}")
    print(f"🔄 Total string replacements: {stats['replacements']}")

if __name__ == "__main__":
    # Run against the current directory (the project root)
    project_root = os.path.abspath(".")
    whitelabel_project(project_root)
