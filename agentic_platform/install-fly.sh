#!/bin/bash

# install-fly.sh - Script to install flyctl and authenticate

# Download and install flyctl
curl -L https://fly.io/install.sh | sh

# Add flyctl to PATH (this will affect the current shell session)
export PATH="$HOME/.fly/bin:$PATH"

# Authenticate with Fly.io
flyctl auth login
