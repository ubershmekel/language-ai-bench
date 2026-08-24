#!/bin/sh
set -eu
case "${LANGUAGE:?}" in
  javascript) cp solution/server.js src/server.js ;;
  typescript) cp solution/server.ts src/server.ts ;;
  python) cp solution/server.py src/server.py ;;
  go) cp solution/main.go src/main.go ;;
esac

