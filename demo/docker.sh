#!/bin/bash
set -ex pipefail

curl -fsSL get.docker.com | sh
sudo usermod -aG docker vagrant
sudo systemctl enable docker