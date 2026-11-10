#!/usr/bin/env bash

# Check that the source distribution can be installed from, and that
# the resulting git-dendrify script runs.

set -x

D=$(mktemp -d)
function rm_tmpdir {
    rm -rf "$D"
}
trap rm_tmpdir EXIT

poetry build --format sdist --output "$D"/dist \
    && python3 -m venv "$D"/venv \
    && cd / \
    && ( source "$D"/venv/bin/activate \
             && pip install "$D"/dist/gitdendrify-*.tar.gz \
             && git-dendrify --version ) \
    && echo Success
