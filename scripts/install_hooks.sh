#!/usr/bin/env bash
# Uses the hooks committed in .githooks for this clone.
set -e
git config core.hooksPath .githooks
echo "Git hooks installed from .githooks"
