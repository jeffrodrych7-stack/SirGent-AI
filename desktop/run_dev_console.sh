#!/usr/bin/env sh
# Dev helper: compile-check every sirgent module.
python3 -m compileall -q sirgent && echo "sirgent: all modules compile OK"
