#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

info() {
  printf "[info] %s\n" "$*"
}

warn() {
  printf "[warn] %s\n" "$*" >&2
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

ensure_brew() {
  if require_cmd brew; then
    info "brew found: $(command -v brew)"
    return 0
  fi

  warn "brew not found. Please install Homebrew from https://brew.sh/"
  return 1
}

ensure_python() {
  if require_cmd python3; then
    info "python3 found: $(command -v python3)"
    return 0
  fi

  warn "python3 not found. Please install Python 3.11+ (brew install python)"
  return 1
}

ensure_uv() {
  if require_cmd uv; then
    info "uv found: $(command -v uv)"
    return 0
  fi

  warn "uv not found. Installing with curl..."
  if ! require_cmd curl; then
    warn "curl not found; please install curl and re-run."
    return 1
  fi

  curl -LsSf https://astral.sh/uv/install.sh | sh
  if ! require_cmd uv; then
    warn "uv install failed. Please install manually: https://github.com/astral-sh/uv"
    return 1
  fi
  info "uv installed: $(command -v uv)"
}

ensure_env_file() {
  if [[ -f .env ]]; then
    info ".env found."
    return 0
  fi

  if [[ -f .env.example ]]; then
    info "Creating .env from .env.example"
    cp .env.example .env
    warn "Update .env with your API keys before running AI features."
    return 0
  fi

  warn "Missing .env and .env.example."
  return 1
}

ensure_db_initialized() {
  local db_path="data/database/papers.db"
  if [[ -f "$db_path" ]]; then
    info "Database found at $db_path"
    return 0
  fi

  info "Initializing database..."
  uv run python -m src.utils.database init
}

main() {
  local ok=0

  ensure_brew || ok=1
  ensure_python || ok=1
  ensure_uv || ok=1

  if [[ $ok -ne 0 ]]; then
    warn "Missing required tools. Fix issues above and re-run."
    exit 1
  fi

  ensure_env_file

  info "Syncing dependencies..."
  uv sync --all-extras

  ensure_db_initialized

  info "Launching Streamlit UI..."
  uv run python3 run_ui.py
}

main "$@"
