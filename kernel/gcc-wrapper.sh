#!/bin/bash
# Wrapper script to filter out gcc-12 specific flags for gcc-11

# Filter out -ftrivial-auto-var-init=zero which is not supported by gcc-11
args=()
for arg in "$@"; do
    if [[ "$arg" != *"-ftrivial-auto-var-init"* ]]; then
        args+=("$arg")
    fi
done

# Call real gcc with filtered arguments
exec /usr/bin/gcc "${args[@]}"
