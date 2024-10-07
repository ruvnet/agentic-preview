#!/bin/bash

# This script installs Fly.io CLI (flyctl) on your machine.

set -e

# Function to check if the script is run with sudo (for Linux)
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run this script with sudo or as root."
        exit 1
    fi
}

# Detect the OS
OS=$(uname -s)

if [ "$OS" == "Linux" ]; then
    echo "Installing flyctl for Linux..."
    check_sudo
    curl -L https://fly.io/install.sh | sh
    # Add flyctl to PATH for all users
    FLYCTL_INSTALL="/usr/local/bin"
    echo "export FLYCTL_INSTALL=\"$FLYCTL_INSTALL\"" | sudo tee /etc/profile.d/flyctl.sh > /dev/null
    echo "export PATH=\"\$FLYCTL_INSTALL:\$PATH\"" | sudo tee -a /etc/profile.d/flyctl.sh > /dev/null
    source /etc/profile.d/flyctl.sh
elif [ "$OS" == "Darwin" ]; then
    echo "Installing flyctl for macOS..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew is not installed. Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    brew install flyctl
elif [[ "$OS" == CYGWIN* || "$OS" == MINGW* || "$OS" == MSYS* ]]; then
    echo "Installing flyctl for Windows..."
    powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Verify installation
if command -v flyctl &> /dev/null; then
    echo "flyctl successfully installed."
    flyctl version
else
    echo "flyctl installation failed. Please check the above output for errors."
    exit 1
fi

echo "Installation complete. Please restart your terminal or run 'source /etc/profile.d/flyctl.sh' to use flyctl."
