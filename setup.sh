#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# setup.sh — one-shot project setup for Linux, macOS and Windows (Git Bash/WSL)
#
#   ./setup.sh             full setup (re-running removes old setup and redoes it)
#   ./setup.sh --no-docker skip docker compose
#   ./setup.sh --remove    undo everything (env vars, venv) and stop
#
# What it does:
#   1. Removes any previous setup (shell rc block, Windows user env vars, .venv)
#   2. Creates .venv and installs requirements
#   3. Makes db.py / vector_db.py importable from any folder (PYTHONPATH + .pth)
#   4. Exports every variable in .env to your shell profile (and Windows user env)
#   5. Starts docker compose and waits for the database to be healthy
#   6. Runs the utilities' health checks
# ------------------------------------------------------------------------------
set -euo pipefail

PROJECT_NAME="shop-agent"
HOME_VAR="SHOP_AGENT_HOME"
DB_CONTAINER="shop-db"
MIN_PY_MINOR=10                      # Python 3.10+

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/.env"
STATE_FILE="$PROJECT_DIR/.setup_state"   # remembers Windows vars we set
MARK_START="# >>> $PROJECT_NAME setup >>>"
MARK_END="# <<< $PROJECT_NAME setup <<<"

RUN_DOCKER=1
MODE="install"
for arg in "$@"; do
  case "$arg" in
    --no-docker) RUN_DOCKER=0 ;;
    --remove)    MODE="remove" ;;
    -h|--help)   sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

info() { printf '\033[1;34m[setup]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ ok  ]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn ]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[fail ]\033[0m %s\n' "$*"; exit 1; }

# ---------- OS detection ------------------------------------------------------
case "$(uname -s)" in
  Linux*)               OS="linux" ;;
  Darwin*)              OS="mac" ;;
  MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
  *) die "Unsupported OS: $(uname -s)" ;;
esac
info "Detected OS: $OS"

if [[ "$OS" == "windows" ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
  VENV_ACTIVATE="$VENV_DIR/Scripts/activate"
  PATH_SEP=";"
else
  VENV_PY="$VENV_DIR/bin/python"
  VENV_ACTIVATE="$VENV_DIR/bin/activate"
  PATH_SEP=":"
fi

# ---------- shell profile files ----------------------------------------------
rc_files() {
  local files=()
  case "$OS" in
    mac)     files=("$HOME/.zshrc" "$HOME/.bash_profile") ;;
    linux)   files=("$HOME/.bashrc"); [[ -f "$HOME/.zshrc" ]] && files+=("$HOME/.zshrc") ;;
    windows) files=("$HOME/.bashrc") ;;   # Git Bash
  esac
  printf '%s\n' "${files[@]}"
}

remove_rc_block() {
  local rc="$1"
  [[ -f "$rc" ]] || return 0
  # awk instead of sed -i: works the same on GNU (Linux) and BSD (macOS)
  awk -v s="$MARK_START" -v e="$MARK_END" '
    $0==s {skip=1; next}
    $0==e {skip=0; next}
    !skip
  ' "$rc" > "$rc.tmp" && mv "$rc.tmp" "$rc"
}

# ---------- Windows user env vars (seen by PowerShell / cmd) ------------------
remove_windows_vars() {
  [[ "$OS" == "windows" && -f "$STATE_FILE" ]] || return 0
  while IFS= read -r name; do
    [[ -n "$name" ]] && reg delete 'HKCU\Environment' /v "$name" /f >/dev/null 2>&1 || true
  done < "$STATE_FILE"
  rm -f "$STATE_FILE"
}

# ---------- .env parsing ------------------------------------------------------
# prints KEY<TAB>VALUE for every valid line, quotes stripped
read_env() {
  [[ -f "$ENV_FILE" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"                               # Windows line endings
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    line="${line#export }"
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    local key="${BASH_REMATCH[1]}" val="${BASH_REMATCH[2]}"
    val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
    printf '%s\t%s\n' "$key" "$val"
  done < "$ENV_FILE"
}

# ---------- remove previous setup ---------------------------------------------
cleanup() {
  info "Removing previous setup (if any)"
  while IFS= read -r rc; do remove_rc_block "$rc"; done < <(rc_files)
  remove_windows_vars
  if [[ -d "$VENV_DIR" ]]; then
    rm -rf "$VENV_DIR"
  fi
  ok "Previous setup removed"
}

cleanup
if [[ "$MODE" == "remove" ]]; then
  ok "Done. Open a new terminal for the change to apply."
  exit 0
fi

if [[ ! -f "$ENV_FILE" && -f "$PROJECT_DIR/.env.example" ]]; then
  cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
  ok "Created .env with local Docker database settings"
fi

# ---------- find Python -------------------------------------------------------
find_python() {
  local candidates=(python3 python)
  [[ "$OS" == "windows" ]] && candidates=("py -3" python python3)
  for cand in "${candidates[@]}"; do
    # shellcheck disable=SC2086
    if $cand -c "import sys; sys.exit(0 if sys.version_info >= (3, $MIN_PY_MINOR) else 1)" >/dev/null 2>&1; then
      echo "$cand"; return 0
    fi
  done
  return 1
}

PY="$(find_python)" || die "Python 3.$MIN_PY_MINOR+ not found. Install it and re-run."
ok "Using Python: $($PY --version 2>&1) ($PY)"

# ---------- venv + dependencies ----------------------------------------------
# Allow slower package downloads while preserving caller-provided pip settings.
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
export PIP_RETRIES="${PIP_RETRIES:-5}"
export PIP_DISABLE_PIP_VERSION_CHECK=1

info "Creating virtual environment in .venv"
# shellcheck disable=SC2086
$PY -m venv "$VENV_DIR"
info "Upgrading pip (download timeout: ${PIP_DEFAULT_TIMEOUT}s)"
if ! "$VENV_PY" -m pip install --upgrade pip; then
  warn "Could not upgrade pip; continuing with the version bundled with Python."
fi

if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
  info "Installing requirements.txt"
  "$VENV_PY" -m pip install -r "$PROJECT_DIR/requirements.txt"
else
  info "No requirements.txt found, installing defaults"
  "$VENV_PY" -m pip install \
    sqlalchemy "psycopg[binary]" python-dotenv \
    langchain langchain-openai langchain-postgres langchain-tavily
fi
ok "Dependencies installed"

# Make db.py / vector_db.py importable by the venv's python from any folder
SITE_PACKAGES="$("$VENV_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "$PROJECT_DIR" > "$SITE_PACKAGES/$PROJECT_NAME.pth"
ok "Utilities importable inside .venv (from any folder)"

# ---------- environment variables ---------------------------------------------
[[ -f "$ENV_FILE" ]] || warn ".env not found — only project paths will be exported"

# Windows path form for setx / PowerShell (C:\... instead of /c/...)
if [[ "$OS" == "windows" ]]; then
  WIN_PROJECT_DIR="$(cygpath -w "$PROJECT_DIR")"
fi

info "Writing environment block to shell profile(s)"
while IFS= read -r rc; do
  touch "$rc"
  {
    echo "$MARK_START"
    echo "export $HOME_VAR=\"$PROJECT_DIR\""
    echo "export PYTHONPATH=\"$PROJECT_DIR\${PYTHONPATH:+$PATH_SEP\$PYTHONPATH}\""
    echo "if [ -f \"$ENV_FILE\" ]; then set -a; . <(tr -d '\\r' < \"$ENV_FILE\"); set +a; fi"
    echo "alias agentenv='. \"$VENV_ACTIVATE\"'"
    echo "$MARK_END"
  } >> "$rc"
  ok "Updated $rc"
done < <(rc_files)

if [[ "$OS" == "windows" ]]; then
  info "Setting Windows user environment variables (for PowerShell / cmd)"
  : > "$STATE_FILE"
  setx "$HOME_VAR" "$WIN_PROJECT_DIR" >/dev/null
  echo "$HOME_VAR" >> "$STATE_FILE"
  while IFS=$'\t' read -r key val; do
    setx "$key" "$val" >/dev/null
    echo "$key" >> "$STATE_FILE"
  done < <(read_env)
  warn "PYTHONPATH is not set globally on Windows (it would affect every Python)."
  warn "Use the .venv python, where the utilities are already importable."
  ok "Windows variables set"
fi

# ---------- docker compose ----------------------------------------------------
if [[ "$RUN_DOCKER" == "1" ]]; then
  command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker or use --no-docker."
  info "Starting docker compose"
  (cd "$PROJECT_DIR" && docker compose up -d --build)

  info "Waiting for $DB_CONTAINER to be healthy"
  for _ in $(seq 1 30); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo starting)"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
  [[ "${status:-}" == "healthy" ]] || die "Database did not become healthy. Check: docker logs $DB_CONTAINER"
  ok "Database is healthy"

  # ---------- utility health checks -------------------------------------------
  cd "$PROJECT_DIR"
  if [[ -f utility/db.py ]]; then
    info "Checking utility/db.py"
    "$VENV_PY" -c "from utility import db; print(db.health_check())" \
      || warn "utility/db.py health check failed"
  fi
  if [[ -f utility/vector_db.py ]]; then
    info "Checking utility/vector_db.py"
    "$VENV_PY" -c "from utility import vector_db; vector_db.ensure_table(); print('vector table ready')" \
      || warn "utility/vector_db.py check failed; check VECTOR_DB_* settings and database access."
  fi
fi

echo
ok "Setup complete."
echo "  Open a new terminal (or run: source $(rc_files | head -n1)), then:"
echo "    agentenv                         # activate the venv"
echo "    python -c 'from utility import db, vector_db'   # works from any folder"
