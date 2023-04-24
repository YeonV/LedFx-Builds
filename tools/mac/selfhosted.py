#!/usr/bin/env python3

import platform
import shutil
import glob
import os

def link_homebrew_tool(dir, formula_dir):
  shutil.rmtree(dir, ignore_errors=True)
  os.makedirs(dir, exist_ok=True)
  x64_complete = os.path.join(tool_dir, 'x64.complete')
  x86_complete = os.path.join(tool_dir, 'x86.complete')
  open(x64_complete, 'x') if not os.path.isfile(x64_complete) else 0
  open(x86_complete, 'x') if not os.path.isfile(x86_complete) else 0

  os.symlink(formula_dir, os.path.join(dir, 'x64'), target_is_directory=True)
  os.symlink(formula_dir, os.path.join(dir, 'x86'), target_is_directory=True)
  return

tool_cache_dir = os.path.dirname(os.path.abspath(__file__))
homebrew_root = '/opt/homebrew' if platform.processor() == 'arm' else '/usr/local'
homebrew_cellar = os.path.join(homebrew_root, 'Cellar')
for formula in glob.glob(os.path.join(homebrew_cellar, '*/*/')):
  rel_dir = os.path.relpath(formula, homebrew_cellar)
  tool_dir = os.path.join(tool_cache_dir, rel_dir)
  link_homebrew_tool(tool_dir, formula)
