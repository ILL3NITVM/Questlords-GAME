#!/usr/bin/env bash
# Octavia Studio — offline-first setup.
#
# Installs from the vendored wheels in vendor/wheels/ when they match this
# platform, and falls back to PyPI otherwise. The vendored set is Linux
# x86_64 / CPython 3.11; on any other platform the fallback is used.
set -euo pipefail

cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "Octavia Studio setup"
echo "  python: $($PY --version 2>&1)"

if [ -d vendor/wheels ] && [ -n "$(ls -A vendor/wheels 2>/dev/null)" ]; then
  echo "  trying vendored wheels (offline)..."
  if $PY -m pip install --quiet --no-index --find-links vendor/wheels \
        -r requirements.txt 2>/dev/null; then
    echo "  installed from vendor/wheels"
  else
    echo "  vendored wheels do not match this platform; falling back to PyPI"
    $PY -m pip install --quiet -r requirements.txt
  fi
else
  $PY -m pip install --quiet -r requirements.txt
fi

echo
echo "Verifying..."
$PY -c "import yaml, PIL; print('  PyYAML', yaml.__version__, '| Pillow', PIL.__version__)"
$PY studio.py doctor >/dev/null 2>&1 && echo "  studio.py doctor: ok" \
  || echo "  studio.py doctor returned non-zero (expected until a backend is configured)"

echo
echo "Next:"
echo "  python studio.py doctor"
echo "  python studio.py generate --count 8        # mock renderer, zero cost"
echo "  python -m pytest tests/ -q -m 'not slow'"
echo
echo "The local rendering backend is optional and large:"
echo "  pip install -r requirements-local.txt"
