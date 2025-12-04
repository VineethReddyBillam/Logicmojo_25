#!/usr/bin/env python3
"""
Simple file-watcher that auto-stages, commits and pushes changes to the repository.
Use with care — it will commit any non-ignored changes in the watched directory.

Usage:
  python tools/auto_git_sync.py --path . --remote origin --branch main

You can run it in background (launchd/systemd) or inside a tmux/screen session.
"""

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:
    print("Missing dependency: run 'pip install -r requirements.txt' first.")
    raise


class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, callback, debounce_seconds=2, ignore_paths=None):
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()
        self.ignore_paths = set(ignore_paths or [])

    def on_any_event(self, event):
        src = os.path.abspath(event.src_path)
        # ignore .git and ignored paths
        if any(p in src for p in (os.sep + '.git' + os.sep,)):
            return
        for ip in self.ignore_paths:
            if ip and ip in src:
                return

        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._run)
            self._timer.start()

    def _run(self):
        try:
            self.callback()
        except Exception as e:
            print("Auto-sync callback error:", e)


def run_git_command(args, cwd, check=True):
    print(f"Running: git {' '.join(args)}")
    return subprocess.run(["git"] + args, cwd=cwd, check=check)


class AutoGitSync:
    def __init__(self, path='.', remote='origin', branch=None, commit_template='autosync: {ts}', push=True):
        self.path = os.path.abspath(path)
        self.remote = remote
        self.branch = branch or get_current_branch(self.path)
        self.commit_template = commit_template
        self.push = push

    def sync(self):
        ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        msg = self.commit_template.format(ts=ts)
        try:
            # git add --all respects .gitignore
            run_git_command(["add", "-A"], cwd=self.path)
            # check if there is anything to commit
            res = subprocess.run(["git", "status", "--porcelain"], cwd=self.path, capture_output=True, text=True)
            if not res.stdout.strip():
                print("No changes to commit.")
                return
            run_git_command(["commit", "-m", msg], cwd=self.path)
            if self.push:
                run_git_command(["push", self.remote, self.branch], cwd=self.path)
            print(f"Synced at {ts}")
        except subprocess.CalledProcessError as e:
            print("Git command failed:", e)


def get_current_branch(cwd):
    try:
        out = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, text=True).strip()
        return out
    except Exception:
        return 'main'


def main():
    parser = argparse.ArgumentParser(description='Auto-commit & push changes in a git repo when files change')
    parser.add_argument('--path', default='.', help='Path to repository root to watch')
    parser.add_argument('--remote', default='origin', help='Remote name to push to')
    parser.add_argument('--branch', default=None, help='Branch name to push to (defaults to current branch)')
    parser.add_argument('--debounce', type=float, default=2.0, help='Seconds to wait for quiet before committing')
    parser.add_argument('--no-push', dest='push', action='store_false', help="Don't push, only commit locally")
    parser.add_argument('--ignore', action='append', help='Paths to ignore (substring match)')
    args = parser.parse_args()

    repo_path = os.path.abspath(args.path)
    if not os.path.isdir(os.path.join(repo_path, '.git')):
        print('Error: directory is not a git repository:', repo_path)
        sys.exit(2)

    ags = AutoGitSync(path=repo_path, remote=args.remote, branch=args.branch, push=args.push)

    def cb():
        print('Detected changes — committing...')
        ags.sync()

    handler = DebouncedHandler(cb, debounce_seconds=args.debounce, ignore_paths=args.ignore)
    observer = Observer()
    observer.schedule(handler, repo_path, recursive=True)
    observer.start()
    try:
        print('Watching', repo_path, 'branch=', ags.branch, 'remote=', ags.remote)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
