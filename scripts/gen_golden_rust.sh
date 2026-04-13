#!/usr/bin/env bash
# 可选：在安装了 Rust 工具链时，用 sol-parser-sdk 生成 JSON 金样到 tests/fixtures/。
# 当前仓库未包含生成器二进制；占位脚本便于 CI 后续接入。
set -euo pipefail
echo "gen_golden_rust: 未实现；请用手写 fixtures 或在此调用 cargo run --manifest-path ../../sol-parser-sdk/Cargo.toml ..." >&2
exit 0
