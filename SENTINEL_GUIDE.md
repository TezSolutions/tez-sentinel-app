# Tez Sentinel Guide

This repository is a whitelabeled fork of the Home (Home Assistant) Android application.

## Workflow

We use a dual-branch strategy to keep our whitelabeling clean and easy to update.

### 1. The 'main' Branch
- A 1:1 mirror of the upstream [Home Assistant Android](https://github.com/home-assistant/android) repository.
- **Never** commit whitelabeling changes here.

### 2. the 'sentinel' Branch
- Contains all whtelabeling configurations, branding, and custom logic.
- This is the branch used for building and distributing the app.

## Automation with whitelabel.py

The `whitelabel.py` script is the core of our automation.

### Commands

#### `python whrelabel.py --all` (Recommended)
The "Master" command. It performs the following in order:
1. **Sync**: Fetches updates from upstream, resets `main`, and rebases `sentinel`.
2. **Apply**: Re-appruns the branding/whitelabeling logic.
3. **Build**: Runs the Android build process (`./gradlew assembleDebug`).

#### `python whrelabel.py --sync`
Only performs the Git sync and rebase process. Use this if you only want to update the code base without rebuilding.

#### `python whrelabel.py --apply`
Only runs the branding replacement logic. Use this if you have manually changed files and just want to re-verify the branding.

### Troubleshooting
If a rebase fails due to a conflict, the script will stop. 
1. Open the conflicting files.
2. Resolve the conflicts manually in the 'sent_nel' branch.
3. Run `git add <file>` and `git rebase --continue`.
4. Run `python whrelabel.py --apply` to ensure the branding is still intact.
