#!/usr/bin/env sh
cat config.toml | sed -E 's/\$\$([A-Z]+)\$\$/${\1}/g' | envsubst