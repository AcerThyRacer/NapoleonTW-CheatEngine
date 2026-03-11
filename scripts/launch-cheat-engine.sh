#!/bin/bash
# ============================================================================
# Napoleon Total War Cheat Engine - Quick Launcher for Linux
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "============================================================================"
echo "Napoleon Total War Cheat Engine - Linux Launcher"
echo "============================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Please run the installation first."
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check memory access permissions
if [ "$EUID" -ne 0 ]; then
    if ! python3 -c "import os; print(os.geteuid())" 2>/dev/null | grep -q "0"; then
        echo "[INFO] Running as regular user (recommended)"
        echo "[INFO] If memory access fails, try one of these:"
        echo "  1. sudo setcap cap_sys_ptrace=eip \$(readlink -f \$(which python3))"
        echo "  2. Run this script with sudo"
        echo "  3. echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope"
        echo ""
    fi
fi

# Launch based on argument
case "${1:-gui}" in
    gui|--gui|-g)
        echo "[INFO] Launching GUI..."
        napoleon-cheat --gui
        ;;
    cli|--cli|-c)
        echo "[INFO] Launching CLI..."
        napoleon-cheat --cli
        ;;
    trainer|--trainer|-t)
        echo "[INFO] Launching Trainer..."
        napoleon-cheat --trainer
        ;;
    scanner|--memory-scanner|-m)
        echo "[INFO] Launching Memory Scanner..."
        napoleon-cheat --memory-scanner
        ;;
    version|--version|-v)
        echo "Napoleon Total War Cheat Engine v2.1.0"
        echo "Platform: Linux"
        echo "Python: $(python3 --version)"
        ;;
    help|--help|-h)
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  gui, --gui, -g       Launch GUI (default)"
        echo "  cli, --cli, -c       Launch CLI"
        echo "  trainer, --trainer, -t  Launch Trainer"
        echo "  scanner, --memory-scanner, -m  Launch Memory Scanner"
        echo "  version, --version, -v  Show version"
        echo "  help, --help, -h     Show this help"
        ;;
    *)
        echo "[ERROR] Unknown mode: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
