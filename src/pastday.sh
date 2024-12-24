#!/usr/bin/env bash

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)

pushd "${HERE}" >/dev/null || exit 1
    echo "no graphs available"
    # ./ms-trend.py --hours 0
    # ./me-trend.py --hours 0
    # ./lg-trend.py --hours 0
popd >/dev/null || exit
