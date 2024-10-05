#!/bin/bash

# This script installs Fly.io CLI (flyctl) on your machine.

set -e

# Detect the OS
OS=$(uname -s)

if [ "$OS" == "Linux" ]; then
    echo "Installing flyctl for Linux..."
    curl -L https://fly.io/install.sh | sh
    # Add flyctl to PATH
    export FLYCTL_INSTALL="$HOME/.fly"
    echo 'export FLYCTL_INSTALL="$HOME/.fly"' >> ~/.bash_profile
    echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bash_profile
    export PATH="$FLYCTL_INSTALL/bin:$PATH"
elif [ "$OS" == "Darwin" ]; then
    echo "Installing flyctl for macOS..."
    brew install flyctl
elif [[ "$OS" == CYGWIN* || "$OS" == MINGW* || "$OS" == MSYS* ]]; then
    echo "Installing flyctl for Windows..."
    iwr https://fly.io/install.ps1 -useb | iex
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Verify installation
if command -v flyctl &> /dev/null
then
    echo "flyctl successfully installed."
    flyctl version
else
    echo "flyctl installation failed. Please check the above output for errors."
    exit 1
fi