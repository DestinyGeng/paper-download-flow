#!/bin/sh
# 一条命令跑完整流程：检索 → 下载 → 定级 → 清单 → 统计
# 用法: sh run_all.sh [目标篇数] [页数]
set -eu
TARGET="$1"
PAGES="$2"
if [ -z "$TARGET" ]; then TARGET=500; fi
if [ -z "$PAGES" ]; then PAGES=3; fi
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE"

echo "[1/4] 检索 + 下载 OA ..."
python3 scripts/batch_collect.py --target "$TARGET" --pages "$PAGES" --out ../论文

echo "[2/4] 校准期刊（ablesci）..."
python3 scripts/verify_journals.py || true

echo "[3/4] 合并定级 ..."
python3 scripts/apply_levels.py

echo "[4/4] 生成清单 + 看板 + 汇总 ..."
python3 scripts/report_cli.py
python3 scripts/stats.py
python3 scripts/cleanup.py
python3 scripts/board.py