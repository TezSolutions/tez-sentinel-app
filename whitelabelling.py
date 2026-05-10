import os
import re

# --- CONFIGURATION ---
# These are the values you provided
NEW_PACKAGE_ID = "in.tezsolutions.sentinel"
NEW_APP_NAME = "Tez Sentinel"
OLD_BRAND_NAME = "Home Assistant"

# Add your logo Hex codes here to update the theme!
# Example: COLORS_TO_REPLACE = {"#000000": "#FF5733"}
COLORS_TO_REPLACE = {} 
# ---------------------

def whitelabel_project(root_dir):
    if not os.path.exists(root_dir):
        print(f"Error: Directory '{root_dir}' not found.")
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

                original_content = content
                
                # 1. Replace Brand Name (Textual)
                if OLD_BRAND_NAME in content:
                    content = content.replace(OLD_BRAND_NAME, NEW_APP_NAME)
                    stats["replacements"] += 1

                # 2. Replace Package ID (for Gradle files)
                if ext in ['.kts', '.gradle']:
                    # Look for applicationId patterns
                    id_pattern = rf'applicationId\s*=\s*"[^"]+"'
                    new_id_line = f'applicationId = "{NEW_PACKAGE_ID}"'
                    content = re.sub(id_pattern, new_id_line, content)

                # 3. Replace App Name in strings.xml specifically
                if file == "strings.xml":
                    app_name_pattern = rf'(<string name="app_name">)(.*?)(</string>)'
                    content = re.sub(app_name_pattern, rf'\1{NEW_APP_NAME}\3', content)

                # 4. Apply Color Replacements (if user provided them)
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

    print(f"--------------------------------------------------")
    print(f"✨ Whitelabeling Complete!")
    print(f"📊 Files modified: {stats['files_changed']}")
    print(f"🔄 Total string replacements: {stats['replacements']}")

if __name__ == "__main__":
    # Run against the current directory (the project root)
    project_root = os.path.abspath(".")
    whitelabel_project(project_root)
