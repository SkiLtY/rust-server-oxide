#!/bin/bash
# Rust dedicated server entrypoint
# Sets up library paths and runs the server with provided arguments

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(dirname $0)/RustDedicated_Data/Plugins:$(dirname $0)/RustDedicated_Data/Plugins/x86_64

# Support Helm-style config/secret file injection
if [[ -n "${CONFIG_FILE_PATH}" && -f "${CONFIG_FILE_PATH}" ]]; then
    set -a; source "${CONFIG_FILE_PATH}"; set +a
fi

if [[ -n "${SECRET_FILE_PATH}" && -f "${SECRET_FILE_PATH}" ]]; then
    set -a; source "${SECRET_FILE_PATH}"; set +a
fi

# Expand environment variables in arguments
EXPANDED_ARGS=()
for ARG in "$@"; do
    EXPANDED_ARGS+=("$(printf '%s' "$ARG" | envsubst)")
done
set -- "${EXPANDED_ARGS[@]}"

# Run Rust dedicated server
./RustDedicated -batchmode -nographics "$@"
