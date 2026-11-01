#!/usr/bin/env bash
# ==============================================================================
# Urban Integrated Municipal ERP — Automatic Version & VersionCode Incrementer
# Updates frontend/urban-console/src/app/core/constants/version.ts and package.json
# Usage: ./scripts/bump_version.sh [patch|minor|major]
# ==============================================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUMP_TYPE="${1:-patch}"

python3 - <<EOF
import re
import os
import sys
from datetime import datetime

repo_root = "$REPO_ROOT"
bump_type = "$BUMP_TYPE".lower()
version_ts = os.path.join(repo_root, "frontend/urban-console/src/app/core/constants/version.ts")
package_json = os.path.join(repo_root, "frontend/urban-console/package.json")

# 1. Read version.ts
with open(version_ts, "r", encoding="utf-8") as f:
    ts_content = f.read()

ver_match = re.search(r"version:\s*'([^']+)'", ts_content)
code_match = re.search(r"versionCode:\s*([0-9]+)", ts_content)

if not ver_match or not code_match:
    print("Error: Could not parse version or versionCode from version.ts", file=sys.stderr)
    sys.exit(1)

old_ver = ver_match.group(1)
old_code = int(code_match.group(1))

major, minor, patch = map(int, old_ver.split("."))
new_code = old_code + 1

if bump_type == "major":
    new_ver = f"{major + 1}.0.0"
elif bump_type == "minor":
    new_ver = f"{major}.{minor + 1}.0"
else:  # patch
    new_ver = f"{major}.{minor}.{patch + 1}"

now_str = datetime.now().strftime("%B %Y")

# 2. Update version.ts
ts_content = re.sub(r"version:\s*'[^']+'", f"version: '{new_ver}'", ts_content)
ts_content = re.sub(r"versionCode:\s*[0-9]+", f"versionCode: {new_code}", ts_content)
ts_content = re.sub(r"releaseDate:\s*'[^']+'", f"releaseDate: '{now_str}'", ts_content)

with open(version_ts, "w", encoding="utf-8") as f:
    f.write(ts_content)

# 3. Update package.json
with open(package_json, "r", encoding="utf-8") as f:
    pkg_content = f.read()

pkg_content = re.sub(r'"version":\s*"[^"]+"', f'"version": "{new_ver}"', pkg_content)
pkg_content = re.sub(r'"versionCode":\s*[0-9]+', f'"versionCode": {new_code}', pkg_content)

with open(package_json, "w", encoding="utf-8") as f:
    f.write(pkg_content)

print(f"✓ Bumped version: {old_ver} -> {new_ver}")
print(f"✓ Bumped versionCode: {old_code} -> {new_code}")
print(f"✓ Release Date: {now_str}")
EOF
