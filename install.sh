#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="dify-workflow-dsl"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PLATFORM=""
TARGET_DIR=""
FORCE=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Install dify-workflow-dsl into an agent skills directory.

Usage:
  bash install.sh --platform codex
  bash install.sh --platform claude
  bash install.sh --platform openclaw
  bash install.sh --platform hermes
  bash install.sh --platform opencode
  bash install.sh --platform all
  bash install.sh --platform codex --target-dir "$HOME/.codex/skills/dify-workflow-dsl"

Options:
  --platform <name>   codex | claude | openclaw | hermes | opencode | all
  --target-dir <dir>  Override install directory. Not supported with --platform all.
  --force             Overwrite managed files in the target directory.
  --dry-run           Print what would happen without copying files.
  -h, --help          Show this help.

Environment overrides:
  CODEX_HOME, CLAUDE_HOME, OPENCLAW_HOME, HERMES_HOME, OPENCODE_CONFIG_DIR
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$PLATFORM" ]]; then
  echo "Missing --platform." >&2
  usage
  exit 1
fi

default_target_dir() {
  local platform="$1"
  case "$platform" in
    codex)
      echo "${CODEX_HOME:-$HOME/.codex}/skills/$SKILL_NAME"
      ;;
    claude)
      echo "${CLAUDE_HOME:-$HOME/.claude}/skills/$SKILL_NAME"
      ;;
    openclaw)
      echo "${OPENCLAW_HOME:-$HOME/.openclaw}/skills/$SKILL_NAME"
      ;;
    hermes)
      echo "${HERMES_HOME:-$HOME/.hermes}/skills/$SKILL_NAME"
      ;;
    opencode)
      echo "${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}/skills/$SKILL_NAME"
      ;;
    *)
      echo "Unsupported platform: $platform" >&2
      return 1
      ;;
  esac
}

copy_skill() {
  local platform="$1"
  local target="$2"
  local items=(
    "SKILL.md"
    "agents"
    "examples"
    "references"
    "scripts"
  )

  echo "Installing $SKILL_NAME for $platform"
  echo "Source: $SOURCE_DIR"
  echo "Target: $target"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Dry run: no files copied."
    return 0
  fi

  mkdir -p "$target"

  if [[ "$FORCE" -eq 1 ]]; then
    for item in "${items[@]}"; do
      rm -rf "$target/$item"
    done
  fi

  for item in "${items[@]}"; do
    if [[ -e "$SOURCE_DIR/$item" ]]; then
      if [[ -e "$target/$item" && "$FORCE" -ne 1 ]]; then
        echo "Target already has $item. Re-run with --force to overwrite." >&2
        exit 1
      fi
      cp -R "$SOURCE_DIR/$item" "$target/"
    fi
  done

  echo "Installed. Restart or reload your agent if it does not pick up new skills automatically."
}

install_platform() {
  local platform="$1"
  local target
  target="$(default_target_dir "$platform")"
  copy_skill "$platform" "$target"
}

if [[ "$PLATFORM" == "all" ]]; then
  if [[ -n "$TARGET_DIR" ]]; then
    echo "--target-dir cannot be used with --platform all." >&2
    exit 1
  fi
  for platform in codex claude openclaw hermes opencode; do
    install_platform "$platform"
  done
else
  if [[ -n "$TARGET_DIR" ]]; then
    copy_skill "$PLATFORM" "$TARGET_DIR"
  else
    install_platform "$PLATFORM"
  fi
fi
