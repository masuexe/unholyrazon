#!/usr/bin/env python3
"""
Publishes a GitHub Release (or Pre-release) with assets via GitHub REST API.
Reads token from:
1. --token argument
2. GITHUB_TOKEN environment variable
3. ~/.github_token file
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = "https://api.github.com"
REPO = "masuexe/unholyrazon"

def get_token(args_token=None):
    if args_token:
        return args_token.strip()
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()
    token_file = os.path.expanduser("~/.github_token")
    if os.path.isfile(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    return None

def main():
    parser = argparse.ArgumentParser(description="Publish GitHub release")
    parser.add_argument("--tag", required=True, help="Tag name (e.g. v4.0.0-beta.261019)")
    parser.add_argument("--title", required=True, help="Release title")
    parser.add_argument("--notes-file", required=True, help="Path to markdown release notes file")
    parser.add_argument("--asset", action="append", default=[], help="Path to binary asset(s) to attach")
    parser.add_argument("--prerelease", action="store_true", default=True, help="Mark as prerelease (default: True)")
    parser.add_argument("--token", help="GitHub Personal Access Token")
    args = parser.parse_args()

    token = get_token(args.token)
    if not token:
        print("ERROR: GitHub token not found. Provide via --token, GITHUB_TOKEN env, or ~/.github_token.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.notes_file):
        print(f"ERROR: Notes file not found: {args.notes_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.notes_file, "r", encoding="utf-8") as f:
        body = f.read()

    # 1. Create Release
    create_url = f"{API_BASE}/repos/{REPO}/releases"
    payload = {
        "tag_name": args.tag,
        "name": args.title,
        "body": body,
        "draft": False,
        "prerelease": args.prerelease
    }

    req = urllib.request.Request(
        create_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "UnholyRazon-Release-Tool"
        },
        method="POST"
    )

    print(f"Creating pre-release '{args.title}' for tag '{args.tag}'...")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"ERROR creating release: HTTP {e.code}: {err_msg}", file=sys.stderr)
        sys.exit(1)

    release_id = data["id"]
    html_url = data["html_url"]
    upload_url_template = data["upload_url"] # e.g. https://uploads.github.com/.../assets{?name,label}
    upload_base = upload_url_template.split("{")[0]

    print(f"Release created: {html_url}")

    # 2. Upload Assets
    for asset_path in args.asset:
        if not os.path.isfile(asset_path):
            print(f"WARNING: Asset not found, skipping: {asset_path}", file=sys.stderr)
            continue
        asset_name = os.path.basename(asset_path)
        upload_url = f"{upload_base}?name={asset_name}"
        file_size = os.path.getsize(asset_path)
        print(f"Uploading asset '{asset_name}' ({file_size / (1024*1024):.2f} MB)...")

        # Use curl if available for reliable streaming of large binary assets
        import shutil
        import subprocess

        if shutil.which("curl"):
            cmd = [
                "curl", "-s", "-S", "-X", "POST",
                "-H", f"Authorization: Bearer {token}",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{asset_path}",
                upload_url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"ERROR uploading asset {asset_name} via curl: {res.stderr}", file=sys.stderr)
                sys.exit(1)
            try:
                u_data = json.loads(res.stdout)
                if "browser_download_url" in u_data:
                    print(f"Uploaded: {u_data['browser_download_url']}")
                else:
                    print(f"Uploaded: {asset_name} (response: {res.stdout[:100]}...)")
            except Exception:
                print(f"Uploaded: {asset_name}")
        else:
            with open(asset_path, "rb") as af:
                file_data = af.read()

            upload_req = urllib.request.Request(
                upload_url,
                data=file_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "UnholyRazon-Release-Tool"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(upload_req) as u_resp:
                    u_data = json.loads(u_resp.read().decode("utf-8"))
                    print(f"Uploaded: {u_data.get('browser_download_url', asset_name)}")
            except urllib.error.HTTPError as ue:
                u_err = ue.read().decode("utf-8")
                print(f"ERROR uploading asset {asset_name}: HTTP {ue.code}: {u_err}", file=sys.stderr)
                sys.exit(1)

    print("\nRelease published successfully!")
    print(f"URL: {html_url}")

if __name__ == "__main__":
    main()
