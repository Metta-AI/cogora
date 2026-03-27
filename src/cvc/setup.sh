# One-time setup
uv python install 3.12
uv venv --python 3.12 .venv-cogames
uv pip install cogames --python .venv-cogames/bin/python
uv pip install -e . --python .venv-cogames/bin/python

# Everything via the venv
alias cogames='.venv-cogames/bin/cogames'

# Play / upload / check
cogames auth set-token $COGAMES_TOKEN
cogames status
cogames matches
