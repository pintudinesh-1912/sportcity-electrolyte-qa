#!/usr/bin/env bash
# Run the pytest suite and build the Allure report.
#
#   MOCK_DIR=/path/to/mock-server ./run-tests.sh   # suite starts its own fresh mock (recommended)
#   BASE_URL=http://host:3000 ./run-tests.sh       # run against an already-running API (fresh seed!)
#   ./run-tests.sh -k idempotency                  # extra args go to pytest
#
# Output: allure-results/ (raw) and allure-report/index.html (single-file report).
set -uo pipefail
cd "$(dirname "$0")"

# Interpreter: $PYTHON, else the active virtualenv, else the repo's ../.venv, else python3.
if [[ -n "${PYTHON:-}" ]]; then PY="$PYTHON"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then PY="$VIRTUAL_ENV/bin/python"
elif [[ -x ../.venv/bin/python ]]; then PY=../.venv/bin/python
else PY=python3; fi

"$PY" -m pytest "$@"
status=$?

# Allure 2 CLI needs Java; use Homebrew's keg-only openjdk if Java is not on PATH.
if ! java -version >/dev/null 2>&1 && [[ -d /opt/homebrew/opt/openjdk ]]; then
  export JAVA_HOME=/opt/homebrew/opt/openjdk
  export PATH="$JAVA_HOME/bin:$PATH"
fi
if command -v allure >/dev/null 2>&1; then
  allure generate allure-results --clean --single-file -o allure-report >/dev/null \
    && echo "Allure report: $(pwd)/allure-report/index.html"
else
  echo "Allure CLI not found: install it (brew install allure) to build the HTML report."
fi
exit $status
