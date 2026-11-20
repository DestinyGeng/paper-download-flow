#!/usr/bin/env python3
"""全局配置：输出目录、年份范围。

优先级：环境变量 > 默认值。
"""
import os

# 论文输出目录（PDF + metadata.json + 清单）
D = os.environ.get('PAPER_OUT') or os.path.expanduser('~/论文')

# 年份范围（0 = 不限）
YEARS = int(os.environ.get('PAPER_YEARS') or 0)
