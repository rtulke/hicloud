#!/usr/bin/env bash
# Installer for hicloud.
#
# Local:  ./setup.sh [OPTIONS]
# Remote: curl -fsSL https://raw.githubusercontent.com/rtulke/hicloud/main/setup.sh | bash
#
# Installs hicloud either system-wide (/opt/hicloud, launcher in
# /usr/local/bin) or for the current user (~/.local/share/hicloud, launcher
# in ~/.local/bin), resolves the Python dependencies via apt or a virtual
# environment, and creates ~/.hicloud.toml on first run. Safe to re-run:
# an existing checkout is updated, an existing configuration is kept.

set -euo pipefail

REPO_URL="https://github.com/rtulke/hicloud.git"
REPO_BRANCH="main"
CONFIG_FILE="$HOME/.hicloud.toml"
API_BASE_URL="https://api.hetzner.cloud/v1"

SYSTEM_PREFIX="/opt/hicloud"
SYSTEM_LAUNCHER="/usr/local/bin/hicloud"
USER_PREFIX="$HOME/.local/share/hicloud"
USER_LAUNCHER="$HOME/.local/bin/hicloud"

# Options (empty = ask interactively)
OPT_SCOPE=""        # system | user
OPT_DEPS=""         # apt | venv
OPT_DEV=0           # also install requirements-dev.txt
OPT_YES=0           # accept defaults, never prompt
OPT_PREFIX=""       # override the installation directory

# ---------------------------------------------------------------- output --

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_CYAN=$'\033[36m'
else
    C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_CYAN=""
fi

info()  { printf '%s\n' "$*"; }
step()  { printf '%s\n' "${C_CYAN}==>${C_RESET} ${C_BOLD}$*${C_RESET}"; }
ok()    { printf '%s\n' "  ${C_GREEN}OK${C_RESET}  $*"; }
warn()  { printf '%s\n' "  ${C_YELLOW}WARN${C_RESET}  $*" >&2; }
hint()  { printf '%s\n' "  ${C_DIM}$*${C_RESET}"; }
die()   { printf '%s\n' "${C_RED}ERROR${C_RESET}  $*" >&2; exit 1; }

# --------------------------------------------------------------- prompts --

# Read from the terminal, not from stdin: with `curl ... | bash` stdin is the
# pipe carrying this script, so a plain `read` would consume the script itself.
TTY="/dev/tty"
have_tty() { [ -r "$TTY" ] && [ -w "$TTY" ]; }

# The prompt helpers report through this variable instead of a command
# substitution: $(...) would run them in a subshell, where an abort could not
# stop the installer and a closed input would spin forever.
ANSWER=""

# read_tty <target-variable> [-s]  -> aborts when the input stream is closed
read_tty() {
    local __var="$1" silent="${2:-}" __value=""
    if [ "$silent" = "-s" ]; then
        IFS= read -r -s __value < "$TTY" || die "Input stream closed. Re-run with -y for a non-interactive install."
        printf '\n' > "$TTY"
    else
        IFS= read -r __value < "$TTY" || die "Input stream closed. Re-run with -y for a non-interactive install."
    fi
    printf -v "$__var" '%s' "$__value"
}

# ask <prompt> <default>  -> answer in $ANSWER, default on Enter
ask() {
    local prompt="$1" default="${2:-}"
    if [ "$OPT_YES" -eq 1 ] || ! have_tty; then
        ANSWER="$default"
        return 0
    fi
    if [ -n "$default" ]; then
        printf '%s [%s]: ' "$prompt" "$default" > "$TTY"
    else
        printf '%s: ' "$prompt" > "$TTY"
    fi
    read_tty ANSWER
    ANSWER="${ANSWER:-$default}"
}

# confirm <prompt> <y|n>  -> exit status 0 for yes
confirm() {
    local prompt="$1" default="${2:-y}"
    while true; do
        ask "$prompt (y/n)" "$default"
        # tr instead of ${var,,}: macOS still ships bash 3.2
        case "$(printf '%s' "$ANSWER" | tr '[:upper:]' '[:lower:]')" in
            y|yes|j|ja) return 0 ;;
            n|no|nein)  return 1 ;;
            *) warn "Please answer y or n." ;;
        esac
    done
}

# choose <prompt> <default-index> <option>...  -> chosen option in $ANSWER
choose() {
    local prompt="$1" default="$2"; shift 2
    local options=("$@") i

    if [ "$OPT_YES" -eq 1 ] || ! have_tty; then
        ANSWER="${options[$((default - 1))]}"
        return 0
    fi
    while true; do
        printf '%s\n' "$prompt" > "$TTY"
        for i in "${!options[@]}"; do
            printf '  %d) %s\n' "$((i + 1))" "${options[$i]}" > "$TTY"
        done
        printf 'Selection [%d]: ' "$default" > "$TTY"
        read_tty ANSWER
        ANSWER="${ANSWER:-$default}"
        if [[ "$ANSWER" =~ ^[0-9]+$ ]] && [ "$ANSWER" -ge 1 ] && [ "$ANSWER" -le "${#options[@]}" ]; then
            ANSWER="${options[$((ANSWER - 1))]}"
            return 0
        fi
        warn "Please enter a number between 1 and ${#options[@]}."
    done
}

# ------------------------------------------------------------------ args --

usage() {
    cat <<'EOF'
Usage: setup.sh [OPTIONS]

  --system         Install system-wide to /opt/hicloud (requires root/sudo)
  --user           Install for the current user to ~/.local/share/hicloud
  --prefix DIR     Install to DIR instead of the default location
  --apt            Resolve dependencies via apt (python3-requests, python3-toml)
  --venv           Resolve dependencies in a virtual environment via pip
  --dev            Additionally install the development tools (pytest, ruff)
  -y, --yes        Do not prompt; accept every default
  -h, --help       Show this help

Without options the installer asks for scope and dependency source.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --system) OPT_SCOPE="system" ;;
        --user)   OPT_SCOPE="user" ;;
        --prefix) shift; [ $# -gt 0 ] || die "--prefix requires a directory."; OPT_PREFIX="$1" ;;
        --apt)    OPT_DEPS="apt" ;;
        --venv|--pip) OPT_DEPS="venv" ;;
        --dev)    OPT_DEV=1 ;;
        -y|--yes) OPT_YES=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1 (see --help)" ;;
    esac
    shift
done

# ---------------------------------------------------------- environment ---

OS_NAME=""      # debian | ubuntu | fedora | arch | macos | ...
OS_PRETTY=""
OS_FAMILY=""    # apt | dnf | pacman | brew | unknown

detect_os() {
    if [ "$(uname -s)" = "Darwin" ]; then
        OS_NAME="macos"
        OS_PRETTY="macOS $(sw_vers -productVersion 2>/dev/null || true)"
        OS_FAMILY="brew"
        return
    fi
    if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_NAME="${ID:-unknown}"
        OS_PRETTY="${PRETTY_NAME:-$OS_NAME}"
        case " ${ID:-} ${ID_LIKE:-} " in
            *debian*|*ubuntu*) OS_FAMILY="apt" ;;
            *fedora*|*rhel*)   OS_FAMILY="dnf" ;;
            *arch*)            OS_FAMILY="pacman" ;;
            *)                 OS_FAMILY="unknown" ;;
        esac
        return
    fi
    OS_NAME="unknown"; OS_PRETTY="$(uname -s)"; OS_FAMILY="unknown"
}

SUDO=""
need_sudo() {
    [ "$(id -u)" -eq 0 ] && { SUDO=""; return 0; }
    command -v sudo >/dev/null 2>&1 || die "Root privileges required, but sudo is not available. Re-run as root or use --user."
    SUDO="sudo"
}

# ------------------------------------------------------------- installer --

SRC_DIR=""      # directory the installer runs from, if it is a checkout
INSTALL_DIR=""  # where hicloud ends up
LAUNCHER=""     # path of the executable wrapper
PYTHON_BIN=""   # interpreter the launcher uses

# The script may run from a checkout (./setup.sh) or standalone (curl | bash).
detect_source() {
    local self="${BASH_SOURCE[0]:-}"
    [ -n "$self" ] && [ -f "$self" ] || return 0
    local dir
    dir="$(cd "$(dirname "$self")" && pwd)"
    [ -f "$dir/hicloud.py" ] && SRC_DIR="$dir"
}

# Locate a reusable virtual environment: inside the installation first, then
# the user-wide ones (those only make sense for a user installation).
find_venv() {
    local base="$1" candidate candidates
    candidates="$base/.venv $base/venv"
    [ "$OPT_SCOPE" = "user" ] && candidates="$candidates $HOME/.venv/hicloud $HOME/.venv"
    for candidate in $candidates; do
        [ -x "$candidate/bin/python" ] && { printf '%s' "$candidate"; return 0; }
    done
    return 1
}

resolve_scope() {
    if [ -z "$OPT_SCOPE" ]; then
        choose "Install hicloud system-wide or for the current user only?" 2 \
            "system-wide  ($SYSTEM_PREFIX, launcher $SYSTEM_LAUNCHER, needs sudo)" \
            "user only    ($USER_PREFIX, launcher $USER_LAUNCHER)"
        case "$ANSWER" in
            system*) OPT_SCOPE="system" ;;
            *)       OPT_SCOPE="user" ;;
        esac
    fi

    if [ "$OPT_SCOPE" = "system" ]; then
        INSTALL_DIR="${OPT_PREFIX:-$SYSTEM_PREFIX}"
        LAUNCHER="$SYSTEM_LAUNCHER"
        need_sudo
    else
        INSTALL_DIR="${OPT_PREFIX:-$USER_PREFIX}"
        LAUNCHER="$USER_LAUNCHER"
    fi
}

run() {
    if [ "$OPT_SCOPE" = "system" ] && [ -n "$SUDO" ]; then
        $SUDO "$@"
    else
        "$@"
    fi
}

fetch_sources() {
    step "Fetching sources"

    # Refuse to write into a directory that holds something else.
    if [ -d "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ] \
       && [ ! -f "$INSTALL_DIR/hicloud.py" ] && [ ! -d "$INSTALL_DIR/.git" ]; then
        die "$INSTALL_DIR exists and is not a hicloud installation. Use --prefix for a different location."
    fi

    # Running from the target checkout itself: nothing to fetch.
    if [ -n "$SRC_DIR" ] && [ "$SRC_DIR" = "$INSTALL_DIR" ]; then
        ok "Installing from the current checkout ($SRC_DIR)"
        return
    fi

    # Local checkout, different target: copy the working tree so local changes
    # are installed too. In a git checkout the tracked files are the source of
    # truth - that leaves out the virtual environment (which stores absolute
    # paths and would break at the new location), the caches and any local
    # scratch files. Without git, fall back to an explicit exclude list.
    if [ -n "$SRC_DIR" ]; then
        run mkdir -p "$INSTALL_DIR"
        if [ -d "$SRC_DIR/.git" ] && command -v git >/dev/null 2>&1; then
            ( cd "$SRC_DIR" && git ls-files -z | tar cf - --null -T - ) \
                | run tar xf - -C "$INSTALL_DIR" \
                || die "Copying from $SRC_DIR failed."
        else
            ( cd "$SRC_DIR" && tar cf - \
                --exclude='./.git' --exclude='./.venv' --exclude='./venv' \
                --exclude='./.claude' --exclude='.DS_Store' \
                --exclude='__pycache__' --exclude='./.pytest_cache' \
                --exclude='./.ruff_cache' . ) \
                | run tar xf - -C "$INSTALL_DIR" \
                || die "Copying from $SRC_DIR failed."
        fi
        ok "Copied $SRC_DIR to $INSTALL_DIR"
        return
    fi

    if [ -d "$INSTALL_DIR/.git" ]; then
        run git -C "$INSTALL_DIR" pull --ff-only --quiet \
            && ok "Updated existing checkout at $INSTALL_DIR" \
            || warn "Could not update $INSTALL_DIR - keeping the current state."
        return
    fi

    if [ -f "$INSTALL_DIR/hicloud.py" ]; then
        ok "Using existing installation at $INSTALL_DIR"
        return
    fi

    command -v git >/dev/null 2>&1 || die "git is required to download hicloud. Install git and re-run."
    run mkdir -p "$(dirname "$INSTALL_DIR")"
    run git clone --quiet --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR" \
        || die "Cloning $REPO_URL failed."
    ok "Cloned $REPO_URL to $INSTALL_DIR"
}

resolve_deps_choice() {
    [ -n "$OPT_DEPS" ] && return 0

    if [ "$OS_FAMILY" != "apt" ]; then
        OPT_DEPS="venv"
        return 0
    fi

    choose "How should the Python dependencies (requests, toml) be installed?" 1 \
        "virtual environment via pip  (recommended, isolated, matches the version pins)" \
        "system packages via apt      (python3-requests, python3-toml, shared with the system)"
    case "$ANSWER" in
        system*) OPT_DEPS="apt" ;;
        *)       OPT_DEPS="venv" ;;
    esac
}

install_deps_apt() {
    step "Installing dependencies via apt"
    need_sudo
    $SUDO apt-get update -qq || warn "apt-get update failed - continuing with the cached package lists."
    $SUDO apt-get install -y python3 python3-requests python3-toml \
        || die "Installing the apt packages failed."
    PYTHON_BIN="$(command -v python3)"
    ok "Installed python3-requests and python3-toml"

    # Debian 12 ships requests 2.28 while requirements.txt asks for >= 2.32.
    local version
    version="$("$PYTHON_BIN" -c 'import requests; print(requests.__version__)' 2>/dev/null || true)"
    if [ -n "$version" ]; then
        case "$version" in
            2.3[2-9]*|2.[4-9]*|[3-9].*) ok "requests $version" ;;
            *) warn "requests $version is older than the pinned >= 2.32. hicloud works, but use --venv if you need the exact versions." ;;
        esac
    fi

    if [ "$OPT_DEV" -eq 1 ]; then
        $SUDO apt-get install -y python3-pytest ruff \
            || warn "pytest/ruff not available via apt - install them with pip if you need them."
    fi
}

install_deps_venv() {
    step "Setting up the virtual environment"

    local venv_dir
    if venv_dir="$(find_venv "$INSTALL_DIR")"; then
        ok "Reusing existing environment at $venv_dir"
    else
        venv_dir="$INSTALL_DIR/.venv"
        info "  Creating $venv_dir ..."
        if ! run python3 -m venv "$venv_dir" 2>/dev/null; then
            # Debian and Ubuntu split venv out of the python3 package.
            if [ "$OS_FAMILY" = "apt" ]; then
                warn "python3 -m venv failed - installing python3-venv."
                need_sudo
                $SUDO apt-get install -y python3-venv || die "Installing python3-venv failed."
                run python3 -m venv "$venv_dir" || die "Could not create the virtual environment."
            else
                die "Could not create the virtual environment at $venv_dir."
            fi
        fi
        ok "Created $venv_dir"
    fi

    PYTHON_BIN="$venv_dir/bin/python"
    [ -x "$PYTHON_BIN" ] || die "No interpreter found at $PYTHON_BIN."

    info "  Installing dependencies ..."
    run "$PYTHON_BIN" -m pip install --quiet --upgrade pip \
        || warn "Could not update pip - continuing."

    local requirements="requirements.txt"
    [ "$OPT_DEV" -eq 1 ] && requirements="requirements-dev.txt"
    run "$PYTHON_BIN" -m pip install --quiet -r "$INSTALL_DIR/$requirements" \
        || die "Installing the dependencies failed."
    ok "Installed dependencies from $requirements"
}

install_launcher() {
    step "Installing the launcher"

    local tmp
    tmp="$(mktemp)"
    cat > "$tmp" <<EOF
#!/bin/sh
# hicloud launcher - generated by setup.sh
exec "$PYTHON_BIN" "$INSTALL_DIR/hicloud.py" "\$@"
EOF
    chmod 755 "$tmp"

    run mkdir -p "$(dirname "$LAUNCHER")"
    run cp "$tmp" "$LAUNCHER" || die "Could not write the launcher to $LAUNCHER."
    rm -f "$tmp"
    ok "Launcher installed at $LAUNCHER"

    case ":$PATH:" in
        *":$(dirname "$LAUNCHER"):"*) ;;
        *)
            warn "$(dirname "$LAUNCHER") is not in your PATH."
            hint "Add it, e.g.: echo 'export PATH=\"\$PATH:$(dirname "$LAUNCHER")\"' >> ~/.bashrc"
            ;;
    esac
}

# ---------------------------------------------------------- configuration --

print_token_instructions() {
    cat <<EOF

  ${C_BOLD}Where do I get an API token?${C_RESET}
    1. Sign in at https://console.hetzner.com/projects
    2. Select the project the token should belong to
    3. Left-hand menu: "Security" -> tab "API tokens"
    4. Top right: "Generate API token"
    5. Enter a description and pick permissions ${C_BOLD}Read & Write${C_RESET}
    6. Copy the token - it is shown exactly once

EOF
}

# Verify the token against the Hetzner API. 0 = valid, 1 = rejected, 2 = unknown.
verify_token() {
    local token="$1" code=""
    command -v curl >/dev/null 2>&1 || return 2
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
        -H "Authorization: Bearer $token" "$API_BASE_URL/locations" 2>/dev/null || true)"
    case "$code" in
        200) return 0 ;;
        401|403) return 1 ;;
        *) return 2 ;;
    esac
}

configure() {
    step "Configuration"

    if [ -f "$CONFIG_FILE" ]; then
        ok "Configuration found at $CONFIG_FILE - keeping it unchanged"
        return
    fi

    info "  No configuration at $CONFIG_FILE yet."
    if ! have_tty || [ "$OPT_YES" -eq 1 ]; then
        warn "Not running interactively - skipping the configuration."
        hint "Create it later with: hicloud --gen-config $CONFIG_FILE"
        return
    fi
    if ! confirm "  Create the configuration now?" "y"; then
        hint "Create it later with: hicloud --gen-config $CONFIG_FILE"
        return
    fi

    print_token_instructions

    local token="" project="" attempt=0
    while true; do
        attempt=$((attempt + 1))
        printf 'API token (input hidden): ' > "$TTY"
        read_tty token -s

        if [ -z "$token" ]; then
            if [ "$attempt" -ge 3 ]; then
                warn "No token entered - skipping the configuration."
                hint "Create it later with: hicloud --gen-config $CONFIG_FILE"
                return
            fi
            warn "No token entered. Please paste the token or press Ctrl-C to abort."
            continue
        fi

        # Hetzner tokens are 64 alphanumeric characters.
        if ! printf '%s' "$token" | grep -qE '^[A-Za-z0-9]{64}$'; then
            warn "That does not look like a Hetzner token (expected 64 alphanumeric characters)."
            confirm "  Use it anyway?" "n" || continue
        fi

        info "  Verifying the token ..."
        set +e
        verify_token "$token"
        local result=$?
        set -e
        case "$result" in
            0) ok "Token accepted by the Hetzner API"; break ;;
            1) warn "The API rejected the token (401/403). Please check it and try again."
               confirm "  Enter a different token?" "y" && continue
               # Writing a token the API already refused would only produce a
               # configuration that fails on the first command.
               hint "Skipping the configuration. Create it later with: hicloud --gen-config $CONFIG_FILE"
               return ;;
            2) warn "Could not verify the token (no network or curl). Using it unchecked."
               break ;;
        esac
    done

    ask "  Project name" "default"
    project="$ANSWER"

    local old_umask
    old_umask="$(umask)"
    umask 077
    cat > "$CONFIG_FILE" <<EOF
[default]
api_token = "$token"
project_name = "$project"
EOF
    umask "$old_umask"
    chmod 600 "$CONFIG_FILE"
    ok "Wrote $CONFIG_FILE with permissions 600"
    hint "Add more projects as further [name] sections in that file."
}

# ------------------------------------------------------------------ main --

main() {
    info ""
    info "${C_BOLD}hicloud installer${C_RESET}"
    info ""

    detect_os
    detect_source
    step "Environment"
    ok "System: $OS_PRETTY"
    command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.9 or newer and re-run."
    ok "Python: $(python3 --version 2>&1)"

    resolve_scope
    ok "Target: $INSTALL_DIR (launcher $LAUNCHER)"

    fetch_sources
    resolve_deps_choice

    if [ "$OPT_DEPS" = "apt" ]; then
        install_deps_apt
    else
        install_deps_venv
    fi

    install_launcher
    configure

    info ""
    info "${C_GREEN}${C_BOLD}hicloud is ready.${C_RESET}"
    info ""
    info "  Start it with:   ${C_BOLD}hicloud${C_RESET}"
    info "  Show the help:   hicloud --help"
    info "  Configuration:   $CONFIG_FILE"
    info ""
}

main "$@"
