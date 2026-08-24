#!/bin/sh
set -eu
# A plausible incomplete attempt: preserve the baseline after inspecting it.
find src -type f -maxdepth 2 -print
