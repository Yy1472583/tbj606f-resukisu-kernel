#!/bin/sh
# 修复 LineageOS/Android 老内核在 Python3 环境编译失败的问题：
# 原 scripts/gcc-wrapper.py 是 Python2 脚本（print 无括号），
# 在 ubuntu-22.04（默认 python3）上会 SyntaxError，连带导致 Kconfig 解析失败。
# 这里把它替换成一个"直接透传调用真实编译器"的 Python3 版本，行为等价但不强制警告。
set -e
KDIR="${1:-kernel}"
F="$KDIR/scripts/gcc-wrapper.py"
if [ -f "$F" ]; then
  cat > "$F" <<'PYEOF'
#!/usr/bin/env python3
import sys, subprocess
# 原脚本为 Python2，仅用于强制无警告编译；此处改为直接透传调用真实编译器
sys.exit(subprocess.call(sys.argv[1:]))
PYEOF
  chmod +x "$F"
  echo "[+] gcc-wrapper.py 已替换为 py3 透传包装"
else
  echo "[*] 未发现 $F，跳过"
fi
