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

# Terminals without a UTF-8 locale would render the marks as garbage.
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
    *UTF-8*|*utf-8*|*UTF8*|*utf8*) M_OK="✓"; M_WARN="!"; M_ERR="✗"; M_RULE="─" ;;
    *)                             M_OK="+"; M_WARN="!"; M_ERR="x"; M_RULE="-" ;;
esac

# Two levels of indentation: headings sit at 2, their content at 4.
info()  { printf '    %s\n' "$*"; }
plain() { printf '%s\n' "$*"; }
blank() { printf '\n'; }
step()  { printf '\n  %s\n' "${C_BOLD}$*${C_RESET}"; }
ok()    { printf '    %s  %s\n' "${C_GREEN}${M_OK}${C_RESET}" "$*"; }
warn()  { printf '    %s  %s\n' "${C_YELLOW}${M_WARN}${C_RESET}" "$*" >&2; }
hint()  { printf '       %s\n' "${C_DIM}$*${C_RESET}"; }
die()   { printf '\n    %s  %s\n\n' "${C_RED}${M_ERR}${C_RESET}" "$*" >&2; exit 1; }

rule() {
    local width=64 out="" i=0
    while [ "$i" -lt "$width" ]; do out="$out$M_RULE"; i=$((i + 1)); done
    printf '%s' "$out"
}

banner() {
    printf '\n  %s\n  %s\n' "${C_BOLD}hicloud installer${C_RESET}" "${C_DIM}$(rule)${C_RESET}"
}

# Paths are long enough without spelling out the home directory every time.
tilde() {
    case "$1" in
        "$HOME"/*) printf '~%s' "${1#"$HOME"}" ;;
        "$HOME")   printf '~' ;;
        *)         printf '%s' "$1" ;;
    esac
}

# label <name> <value> - aligned two-column output for the summary lines
label() { printf '    %-14s %s\n' "$1" "$2"; }

# Run a command without its chatter. Package managers report every unrelated
# detail of the system; that is only worth showing when something failed, so
# the output is held back and printed on failure.
quiet() {
    local output=""
    if output="$("$@" 2>&1)"; then
        return 0
    fi
    printf '%s\n' "$output" >&2
    return 1
}

# --------------------------------------------------------------- prompts --

# Read from the terminal, not from stdin: with `curl ... | bash` stdin is the
# pipe carrying this script, so a plain `read` would consume the script itself.
TTY="/dev/tty"
have_tty() { [ -r "$TTY" ] && [ -w "$TTY" ]; }

# The prompt helpers report through this variable instead of a command
# substitution: $(...) would run them in a subshell, where an abort could not
# stop the installer and a closed input would spin forever.
ANSWER=""

# read_tty <target-variable>  -> aborts when the input stream is closed
read_tty() {
    local __var="$1" __value=""
    IFS= read -r __value < "$TTY" || die "Input stream closed. Re-run with -y for a non-interactive install."
    printf -v "$__var" '%s' "$__value"
}

# read_secret <target-variable>  -> reads without echoing the characters, but
# prints one * per character: a terminal that shows nothing at all looks like
# a hung script, and people stop typing.
read_secret() {
    local __var="$1" prompt="${2:-}" char="" value="" finished=0 tty_state=""

    # Turning the echo off per character (read -s) would leave it on between
    # the reads - a pasted token arrives faster than that and the terminal
    # would print it. So the echo stays off for the whole input.
    if tty_state="$(stty -g < "$TTY" 2>/dev/null)"; then
        stty -echo < "$TTY" 2>/dev/null || tty_state=""
    else
        tty_state=""
    fi
    [ -n "$tty_state" ] && trap 'stty "$tty_state" < "$TTY" 2>/dev/null; exit 130' INT

    # The prompt comes after the echo is off: anything typed in between would
    # otherwise be echoed by the terminal before the first read.
    [ -n "$prompt" ] && printf '%s' "$prompt" > "$TTY"

    while true; do
        IFS= read -r -n 1 char < "$TTY" || break
        case "$char" in
            ""|$'\r'|$'\n')
                finished=1
                break
                ;;
            $'\177'|$'\b')
                if [ -n "$value" ]; then
                    value="${value%?}"
                    # Erase the last star: back up, overwrite, back up again.
                    printf '\b \b' > "$TTY"
                fi
                ;;
            *)
                value="$value$char"
                printf '*' > "$TTY"
                ;;
        esac
    done
    if [ -n "$tty_state" ]; then
        trap - INT
        stty "$tty_state" < "$TTY" 2>/dev/null || true
    fi
    printf '\n' > "$TTY"

    [ "$finished" -eq 1 ] \
        || die "Input stream closed. Re-run with -y for a non-interactive install."
    printf -v "$__var" '%s' "$value"
}

# ask <prompt> <default>  -> answer in $ANSWER, default on Enter
ask() {
    local prompt="$1" default="${2:-}"
    if [ "$OPT_YES" -eq 1 ] || ! have_tty; then
        ANSWER="$default"
        return 0
    fi
    if [ -n "$default" ]; then
        printf '    %s [%s]: ' "$prompt" "$default" > "$TTY"
    else
        printf '    %s: ' "$prompt" > "$TTY"
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
# An option is "label|explanation"; only the label is returned.
choose() {
    local prompt="$1" default="$2"; shift 2
    local options=("$@") i entry

    if [ "$OPT_YES" -eq 1 ] || ! have_tty; then
        ANSWER="${options[$((default - 1))]%%|*}"
        return 0
    fi
    while true; do
        printf '\n    %s\n\n' "${C_BOLD}$prompt${C_RESET}" > "$TTY"
        for i in "${!options[@]}"; do
            entry="${options[$i]}"
            printf '      %d)  %s\n' "$((i + 1))" "${entry%%|*}" > "$TTY"
            case "$entry" in
                *"|"*) printf '          %s\n' "${C_DIM}${entry#*|}${C_RESET}" > "$TTY" ;;
            esac
        done
        printf '\n    Selection [%d]: ' "$default" > "$TTY"
        read_tty ANSWER
        ANSWER="${ANSWER:-$default}"
        if [[ "$ANSWER" =~ ^[0-9]+$ ]] && [ "$ANSWER" -ge 1 ] && [ "$ANSWER" -le "${#options[@]}" ]; then
            ANSWER="${options[$((ANSWER - 1))]%%|*}"
            printf '\n' > "$TTY"
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
  --dev            Additionally install the development tools (pytest, ruff)
  -y, --yes        Do not prompt; accept every default
  -h, --help       Show this help

Override the automatic dependency choice (apt for a system-wide install on
Debian and Ubuntu, a virtual environment everywhere else):

  --apt            Use the apt packages python3-requests and python3-toml
  --venv           Use a virtual environment and pip

The installer only asks two things: where to install, and - if it does not
exist yet - how to create ~/.hicloud.toml.
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
CAN_SYSTEM=0       # is a system-wide installation possible at all?
PRIV_NOTE=""       # how that was determined, for the environment summary

# Determined up front: without root or sudo a system-wide install cannot work,
# and offering it anyway would only fail halfway through.
detect_privileges() {
    if [ "$(id -u)" -eq 0 ]; then
        SUDO=""; CAN_SYSTEM=1; PRIV_NOTE="running as root"
        return
    fi
    if ! command -v sudo >/dev/null 2>&1; then
        CAN_SYSTEM=0; PRIV_NOTE="no sudo installed - user installation only"
        return
    fi
    SUDO="sudo"; CAN_SYSTEM=1
    # -n never prompts: it only tells us whether a password will be needed.
    if sudo -n true 2>/dev/null; then
        PRIV_NOTE="sudo available"
    else
        PRIV_NOTE="sudo available, will ask for your password"
    fi
}

need_sudo() {
    [ "$CAN_SYSTEM" -eq 1 ] \
        || die "Root privileges required, but sudo is not installed. Re-run as root or use --user."
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
    if [ -z "$OPT_SCOPE" ] && [ "$CAN_SYSTEM" -eq 0 ]; then
        OPT_SCOPE="user"
    fi

    if [ -z "$OPT_SCOPE" ]; then
        # Running as root almost always means a system-wide install is wanted.
        local default=2
        [ "$(id -u)" -eq 0 ] && default=1
        choose "Where should hicloud be installed?" "$default" \
            "system-wide, for all users|$SYSTEM_PREFIX, command in /usr/local/bin" \
            "for the current user only|$(tilde "$USER_PREFIX"), command in ~/.local/bin"
        case "$ANSWER" in
            system*) OPT_SCOPE="system" ;;
            *)       OPT_SCOPE="user" ;;
        esac
    fi

    if [ "$OPT_SCOPE" = "system" ]; then
        need_sudo
        INSTALL_DIR="${OPT_PREFIX:-$SYSTEM_PREFIX}"
        LAUNCHER="$SYSTEM_LAUNCHER"
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
        ok "Installing from the current checkout ($(tilde "$SRC_DIR"))"
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
                --exclude='.DS_Store' \
                --exclude='__pycache__' --exclude='./.pytest_cache' \
                --exclude='./.ruff_cache' . ) \
                | run tar xf - -C "$INSTALL_DIR" \
                || die "Copying from $SRC_DIR failed."
        fi
        ok "Copied $(tilde "$SRC_DIR") to $(tilde "$INSTALL_DIR")"
        return
    fi

    if [ -d "$INSTALL_DIR/.git" ]; then
        run git -C "$INSTALL_DIR" pull --ff-only --quiet \
            && ok "Updated existing checkout at $(tilde "$INSTALL_DIR")" \
            || warn "Could not update $(tilde "$INSTALL_DIR") - keeping the current state."
        return
    fi

    if [ -f "$INSTALL_DIR/hicloud.py" ]; then
        ok "Using existing installation at $(tilde "$INSTALL_DIR")"
        return
    fi

    command -v git >/dev/null 2>&1 || die "git is required to download hicloud. Install git and re-run."
    run mkdir -p "$(dirname "$INSTALL_DIR")"
    run git clone --quiet --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR" \
        || die "Cloning $REPO_URL failed."
    ok "Cloned $REPO_URL to $(tilde "$INSTALL_DIR")"
}

# No question here - the sensible route follows from the system and the scope:
# apt packages belong to a system-wide install on Debian and Ubuntu, everything
# else gets an isolated virtual environment. --apt / --venv override it.
resolve_deps() {
    [ -n "$OPT_DEPS" ] && return 0

    if [ "$OS_FAMILY" = "apt" ] && [ "$OPT_SCOPE" = "system" ]; then
        OPT_DEPS="apt"
    else
        OPT_DEPS="venv"
    fi
}

install_deps_apt() {
    step "Installing dependencies"
    need_sudo

    # Nobody needs to read apt's package bookkeeping. The output is kept and
    # printed only when the command actually fails.
    export DEBIAN_FRONTEND=noninteractive

    info "Reading package lists ..."
    quiet $SUDO apt-get update \
        || warn "apt-get update failed - continuing with the cached package lists."

    info "Installing python3-requests and python3-toml ..."
    quiet $SUDO apt-get install -y python3 python3-requests python3-toml \
        || die "Installing the apt packages failed (output above)."

    PYTHON_BIN="$(command -v python3)"

    # Debian 12 ships requests 2.28 while requirements.txt asks for >= 2.32.
    local version
    version="$("$PYTHON_BIN" -c 'import requests; print(requests.__version__)' 2>/dev/null || true)"
    case "$version" in
        "") ok "Installed python3-requests and python3-toml" ;;
        2.3[2-9]*|2.[4-9]*|[3-9].*) ok "Installed requests $version and python3-toml" ;;
        *)  ok "Installed requests $version and python3-toml"
            hint "requests $version is older than the pinned >= 2.32 - use --venv if you need the exact versions" ;;
    esac

    if [ "$OPT_DEV" -eq 1 ]; then
        info "Installing pytest and ruff ..."
        quiet $SUDO apt-get install -y python3-pytest ruff \
            && ok "Installed python3-pytest and ruff" \
            || warn "pytest/ruff not available via apt - install them with pip if you need them."
    fi
}

install_deps_venv() {
    step "Setting up the virtual environment"

    local venv_dir venv_error=""
    if venv_dir="$(find_venv "$INSTALL_DIR")"; then
        ok "Reusing existing environment at $(tilde "$venv_dir")"
    else
        venv_dir="$INSTALL_DIR/.venv"
        info "Creating $(tilde "$venv_dir") ..."
        if ! venv_error="$(run python3 -m venv "$venv_dir" 2>&1)"; then
            # Debian and Ubuntu split venv out of the python3 package, so this
            # first failure is expected there and not worth showing.
            if [ "$OS_FAMILY" = "apt" ]; then
                info "Installing python3-venv ..."
                [ "$CAN_SYSTEM" -eq 1 ] \
                    || die "python3-venv is missing and cannot be installed without root. Install it with: apt install python3-venv"
                quiet $SUDO apt-get install -y python3-venv || die "Installing python3-venv failed (output above)."
                quiet run python3 -m venv "$venv_dir" || die "Could not create the virtual environment."
            else
                printf '%s\n' "$venv_error" >&2
                die "Could not create the virtual environment at $venv_dir."
            fi
        fi
        ok "Created $(tilde "$venv_dir")"
    fi

    PYTHON_BIN="$venv_dir/bin/python"
    [ -x "$PYTHON_BIN" ] || die "No interpreter found at $PYTHON_BIN."

    local requirements="requirements.txt"
    [ "$OPT_DEV" -eq 1 ] && requirements="requirements-dev.txt"

    info "Installing dependencies ..."
    quiet run "$PYTHON_BIN" -m pip install --upgrade pip \
        || warn "Could not update pip - continuing."
    quiet run "$PYTHON_BIN" -m pip install -r "$INSTALL_DIR/$requirements" \
        || die "Installing the dependencies failed (output above)."
    ok "Installed dependencies from $requirements"
}

install_command() {
    step "Installing the hicloud command"

    run mkdir -p "$(dirname "$LAUNCHER")"
    run rm -f "$LAUNCHER"

    # With the apt route the dependencies live in the system interpreter, so a
    # symlink is enough - Python resolves the link and finds lib/ next to the
    # real hicloud.py. A virtual environment needs its own interpreter, which
    # only a wrapper can select.
    if [ "$OPT_DEPS" = "apt" ]; then
        run ln -s "$INSTALL_DIR/hicloud.py" "$LAUNCHER" \
            || die "Could not create the symlink $LAUNCHER."
        run chmod 755 "$INSTALL_DIR/hicloud.py"
        ok "Symlink $(tilde "$LAUNCHER") -> $(tilde "$INSTALL_DIR")/hicloud.py"
    else
        local tmp
        tmp="$(mktemp)"
        cat > "$tmp" <<EOF
#!/bin/sh
# hicloud launcher - generated by setup.sh
exec "$PYTHON_BIN" "$INSTALL_DIR/hicloud.py" "\$@"
EOF
        chmod 755 "$tmp"
        run cp "$tmp" "$LAUNCHER" || die "Could not write the launcher to $LAUNCHER."
        rm -f "$tmp"
        ok "Installed $(tilde "$LAUNCHER")"
    fi

    ensure_path "$(dirname "$LAUNCHER")"
}

# Determine the login shell's startup file, so an added PATH actually survives.
shell_rc() {
    case "$(basename "${SHELL:-/bin/sh}")" in
        zsh)  printf '%s' "${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) if [ -f "$HOME/.bashrc" ]; then printf '%s' "$HOME/.bashrc"
              elif [ "$(uname -s)" = "Darwin" ]; then printf '%s' "$HOME/.bash_profile"
              else printf '%s' "$HOME/.bashrc"; fi ;;
        fish) printf '%s' "$HOME/.config/fish/config.fish" ;;
        *)    printf '%s' "$HOME/.profile" ;;
    esac
}

PATH_NEEDS_RELOAD=0

ensure_path() {
    local bindir="$1" rc marker

    case ":$PATH:" in
        *":$bindir:"*) ok "$(tilde "$bindir") is already in your PATH"; return 0 ;;
    esac

    # A system-wide install lands in /usr/local/bin, which every sane PATH
    # already contains - if it does not, that is a system decision to respect.
    if [ "$OPT_SCOPE" = "system" ]; then
        warn "$(tilde "$bindir") is not in your PATH - start hicloud via $LAUNCHER."
        return 0
    fi

    rc="$(shell_rc)"
    marker="# added by hicloud setup.sh"

    if [ -f "$rc" ] && grep -qF "$marker" "$rc"; then
        ok "PATH entry already present in $(tilde "$rc")"
        PATH_NEEDS_RELOAD=1
        return 0
    fi

    mkdir -p "$(dirname "$rc")"
    if [ "$(basename "$rc")" = "config.fish" ]; then
        printf '\n%s\nfish_add_path -g %s\n' "$marker" "$bindir" >> "$rc"
    else
        printf '\n%s\ncase ":$PATH:" in *":%s:"*) ;; *) PATH="%s:$PATH" ;; esac\nexport PATH\n' \
            "$marker" "$bindir" "$bindir" >> "$rc"
    fi
    ok "Added $(tilde "$bindir") to your PATH in $(tilde "$rc")"

    # Make the command usable for the rest of this run, e.g. the smoke test.
    PATH="$bindir:$PATH"
    export PATH
    PATH_NEEDS_RELOAD=1
}

# An installation that reports success but cannot start is worse than a clear
# error, so run the real command once.
verify_install() {
    step "Checking the installation"
    local output=""
    if output="$("$LAUNCHER" --version 2>&1)"; then
        ok "$output"
    else
        printf '%s\n' "$output" >&2
        die "The installation is not runnable: $LAUNCHER --version failed."
    fi
}

# ---------------------------------------------------------- configuration --

print_token_instructions() {
    cat <<EOF

    ${C_BOLD}Where do I get an API token?${C_RESET}

      1.  Sign in at https://console.hetzner.com/projects
      2.  Select the project the token should belong to
      3.  Bottom of the left sidebar: "Security"
      4.  Tab bar at the top: "API tokens"
      5.  Red button in the top right: "Add API token"
      6.  Enter a description, pick permissions ${C_BOLD}Read & Write${C_RESET},
          then copy the token - it is shown exactly once

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
        ok "Found $(tilde "$CONFIG_FILE") - keeping it unchanged"
        return
    fi

    info "No configuration at $(tilde "$CONFIG_FILE") yet."
    if ! have_tty || [ "$OPT_YES" -eq 1 ]; then
        warn "Not running interactively - skipping the configuration."
        hint "Create it later with: hicloud --gen-config $(tilde "$CONFIG_FILE")"
        return
    fi
    if ! confirm "Create the configuration now?" "y"; then
        hint "Create it later with: hicloud --gen-config $(tilde "$CONFIG_FILE")"
        return
    fi

    print_token_instructions

    local token="" project="" attempt=0
    while true; do
        attempt=$((attempt + 1))
        read_secret token '    API token: '

        if [ -z "$token" ]; then
            if [ "$attempt" -ge 3 ]; then
                warn "No token entered - skipping the configuration."
                hint "Create it later with: hicloud --gen-config $(tilde "$CONFIG_FILE")"
                return
            fi
            warn "No token entered. Please paste the token or press Ctrl-C to abort."
            continue
        fi

        # Hetzner tokens are 64 alphanumeric characters.
        if ! printf '%s' "$token" | grep -qE '^[A-Za-z0-9]{64}$'; then
            warn "That does not look like a Hetzner token (expected 64 alphanumeric characters)."
            confirm "Use it anyway?" "n" || continue
        fi

        info "Verifying the token ..."
        set +e
        verify_token "$token"
        local result=$?
        set -e
        case "$result" in
            0) ok "Token accepted by the Hetzner API"; break ;;
            1) warn "The API rejected the token (401/403). Please check it and try again."
               confirm "Enter a different token?" "y" && continue
               # Writing a token the API already refused would only produce a
               # configuration that fails on the first command.
               hint "Skipping the configuration. Create it later with: hicloud --gen-config $(tilde "$CONFIG_FILE")"
               return ;;
            2) warn "Could not verify the token (no network or curl). Using it unchecked."
               break ;;
        esac
    done

    ask "Project name" "default"
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
    ok "Wrote $(tilde "$CONFIG_FILE") with permissions 600"
    hint "Add more projects as further [name] sections in that file."
}

# ------------------------------------------------------------------ main --

main() {
    banner

    detect_os
    detect_privileges
    detect_source

    step "Environment"
    label "System" "$OS_PRETTY"
    command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.9 or newer and re-run."
    label "Python" "$(python3 --version 2>&1 | sed 's/^Python //')"
    label "Privileges" "$PRIV_NOTE"

    resolve_scope
    resolve_deps

    step "Installation plan"
    label "Location" "$(tilde "$INSTALL_DIR")"
    label "Command" "$(tilde "$LAUNCHER")"
    if [ "$OPT_DEPS" = "apt" ]; then
        label "Dependencies" "apt packages (python3-requests, python3-toml)"
    else
        label "Dependencies" "virtual environment (pip)"
    fi

    fetch_sources

    if [ "$OPT_DEPS" = "apt" ]; then
        install_deps_apt
    else
        install_deps_venv
    fi

    install_command
    verify_install
    configure

    blank
    plain "  ${C_GREEN}${C_BOLD}hicloud is ready${C_RESET}"
    blank
    if [ "$PATH_NEEDS_RELOAD" -eq 1 ]; then
        label "Start" "open a new terminal, then run: ${C_BOLD}hicloud${C_RESET}"
        label "" "${C_DIM}or right now: source $(tilde "$(shell_rc)")${C_RESET}"
    else
        label "Start" "${C_BOLD}hicloud${C_RESET}"
    fi
    label "Help" "hicloud --help"
    label "Configuration" "$(tilde "$CONFIG_FILE")"
    blank
}

main "$@"
