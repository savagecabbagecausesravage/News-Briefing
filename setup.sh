#!/bin/bash
# Install dependencies, handling sgmllib3k build issue on Python 3.12+
# sgmllib3k needs to be installed with --no-build-isolation or manually patched

pip install sgmllib3k 2>/dev/null || {
    # Manual install if wheel build fails
    pip download sgmllib3k --no-binary :all: -d /tmp/sgmllib 2>/dev/null
    cd /tmp/sgmllib
    tar xzf sgmllib3k-*.tar.gz 2>/dev/null || true
    cd sgmllib3k-*/
    # Copy the module directly
    cp sgmllib.py "$(python -c 'import site; print(site.getsitepackages()[0])')/" 2>/dev/null || \
    cp sgmllib.py "$(python -c 'import sysconfig; print(sysconfig.get_paths()[\"purelib\"])')/" 2>/dev/null
    cd /tmp
}

pip install -r requirements.txt --no-deps 2>/dev/null
pip install feedparser requests jinja2 pyyaml 2>/dev/null
