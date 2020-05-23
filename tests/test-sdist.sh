#!/usr/bin/env bash

set -x

PYTHON_VER=$(python3 -c 'if True:
    import sys
    v = sys.version_info
    print(".".join(map(str,[v.major,v.minor,v.micro])))')

OPT_PYTHON=/opt/python/$PYTHON_VER/bin/python3
if [ -x $OPT_PYTHON ]; then
    PYTHON=$OPT_PYTHON
else
    PYTHON=$(which python3)
fi

D=$(mktemp -d)
function rm_tmpdir {
    rm -rf "$D"
}
trap rm_tmpdir EXIT

SRCDIR=$(pwd)

python3 setup.py sdist -d $D \
    && $PYTHON -m venv $D \
    && cd / \
    && ( source $D/bin/activate \
             && python3 -m ensurepip \
             && pip3 install -r "$SRCDIR"/requirements.txt \
             && pip3 install $D/gitdendrify-*.tar.gz ) \
    && echo Success

