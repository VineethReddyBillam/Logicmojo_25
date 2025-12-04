Auto Git Sync

What this does
- Watches your repository for file changes.
- Runs `git add -A`, `git commit -m "autosync: <timestamp>"` and `git push origin <branch>` when changes occur.

Important safety notes
- This will commit any non-ignored changes automatically. Review whether this behaviour fits your workflow.
- Large files, notebooks with outputs, or temporary files may be committed unless listed in `.gitignore`.

Quick start
1. Install dependency (prefer a venv):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the watcher from your repo root:

```bash
python tools/auto_git_sync.py --path . --remote origin --branch main
```

3. To run in background on macOS, create a `launchd` job (example below), or run inside `tmux`/`screen`.

Example `launchd` plist (save as `~/Library/LaunchAgents/com.user.autogitsync.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.autogitsync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/PATH/TO/REPO/tools/auto_git_sync.py</string>
        <string>--path</string>
        <string>/PATH/TO/REPO</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/autogitsync.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/autogitsync.err</string>
</dict>
</plist>
```

Replace `/PATH/TO/REPO` with `/Users/vineethreddy/Desktop/Logicmojo_25` or your repo path.

If you want safer behaviour (e.g., only auto-commit certain file types), run the script with `--ignore` options or edit the script to filter events.
