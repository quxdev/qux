#!/usr/bin/env bash
# Migrate a downstream project from `git submodule add qux` to `pip install -e <qux-path>`.
#
# What it does (in this order):
#   1. Detects the qux submodule in the current repo (`.gitmodules` + `git submodule status`).
#   2. Confirms with you before touching anything.
#   3. Removes the submodule from git's index, .gitmodules, and .git/config.
#   4. Removes the submodule's .git/modules/<path> entry.
#   5. Adds `-e <QUX_PATH>` to requirements.txt (or pyproject.toml [project] dependencies
#      if there's no requirements.txt). Falls back to creating requirements.txt.
#   6. Stages the changes for review. Does NOT commit — you commit when satisfied.
#
# Usage:
#   migrate_qux_submodule.sh                # auto-detect submodule path; assume QUX_PATH=../qux
#   migrate_qux_submodule.sh ../path/to/qux # explicit qux path
#   migrate_qux_submodule.sh --dry-run      # show what would happen, change nothing
#
# After the script runs:
#   pip install -e <QUX_PATH>[dev]    # install qux in editable mode in your venv
#   pip install -r requirements.txt   # picks up the new -e line
#   git diff                           # review changes
#   git commit -am "Replace qux submodule with editable install"

set -euo pipefail

DRY_RUN=0
QUX_PATH=""
for arg in "$@"; do
    case "$arg" in
        --dry-run|-n) DRY_RUN=1 ;;
        --help|-h)    sed -n '2,25p' "$0"; exit 0 ;;
        *)            QUX_PATH="$arg" ;;
    esac
done

# Default qux path: sibling directory `../qux` relative to the downstream repo.
QUX_PATH="${QUX_PATH:-../qux}"

# Sanity: must be run from the root of a git repo.
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "ERROR: not inside a git repository." >&2
    exit 1
fi
cd "$(git rev-parse --show-toplevel)"

# Locate the qux submodule. Look for a .gitmodules entry whose URL ends in qux.git
# or whose path name is exactly 'qux'.
if [[ ! -f .gitmodules ]]; then
    echo "No .gitmodules in this repo. Nothing to migrate." >&2
    exit 0
fi

SUB_PATH=$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' \
            | awk '$2 ~ /(^|\/)qux$/ { print $2; exit }')
if [[ -z "${SUB_PATH:-}" ]]; then
    echo "No qux submodule found in .gitmodules." >&2
    exit 0
fi

# Resolve qux path to an absolute one for clarity in messages and check it has pyproject.toml.
ABS_QUX_PATH=$(cd "$QUX_PATH" 2>/dev/null && pwd) || ABS_QUX_PATH="$QUX_PATH (does not currently exist)"
if [[ -d "$QUX_PATH" && ! -f "$QUX_PATH/pyproject.toml" ]]; then
    echo "WARNING: $QUX_PATH does not contain a pyproject.toml — confirm this is the qux repo root." >&2
fi

echo "About to migrate qux:"
echo "  submodule path : $SUB_PATH"
echo "  install source : $QUX_PATH  (absolute: $ABS_QUX_PATH)"
echo "  dry run        : $DRY_RUN"
echo
read -r -p "Proceed? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

run() {
    if (( DRY_RUN )); then
        echo "+ $*"
    else
        echo "+ $*"
        "$@"
    fi
}

# Sometimes the submodule isn't initialized; deinit is safe either way.
run git submodule deinit -f -- "$SUB_PATH" || true
run git rm -f "$SUB_PATH"
run rm -rf ".git/modules/$SUB_PATH"

# If .gitmodules is now empty (no other submodules), remove it.
if [[ ! -s .gitmodules ]] && (( ! DRY_RUN )); then
    run git rm -f .gitmodules || true
fi

# Wire up the editable install in whichever dependency file exists.
INSTALL_LINE="-e $QUX_PATH"
if [[ -f requirements.txt ]]; then
    if grep -q -E "^-e .*qux($|/|\[)" requirements.txt; then
        echo "requirements.txt already references qux as -e; not modifying."
    else
        if (( DRY_RUN )); then
            echo "+ append to requirements.txt: $INSTALL_LINE"
        else
            printf "\n# qux (editable install; replaces git submodule)\n%s\n" "$INSTALL_LINE" >> requirements.txt
            run git add requirements.txt
        fi
    fi
elif [[ -f pyproject.toml ]] && grep -q '^\[project\]' pyproject.toml; then
    echo "NOTE: no requirements.txt; you have pyproject.toml [project]. Add this manually:"
    echo "    pip install -e $QUX_PATH"
    echo "  pyproject.toml [project] dependencies cannot use editable installs directly;"
    echo "  consider adding a requirements.txt for dev or use [tool.uv.sources] / pip-tools."
else
    echo "NOTE: no requirements.txt or pyproject.toml found. Create requirements.txt with:"
    echo "    $INSTALL_LINE"
fi

echo
echo "Done. Review with: git diff && git status"
echo "Then install with:  pip install -e \"$QUX_PATH\"[dev]"
echo "And commit when satisfied."
