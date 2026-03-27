#!/bin/bash
set -e

# One-time setup
uv python install 3.12
uv venv --python 3.12 .venv-cogames
uv pip install cogames --python .venv-cogames/bin/python

# Auth & status
.venv-cogames/bin/cogames auth set-token $COGAMES_TOKEN
.venv-cogames/bin/cogames status
.venv-cogames/bin/cogames matches
