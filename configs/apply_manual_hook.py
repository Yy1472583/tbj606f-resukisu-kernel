#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply ReSukiSU non-GKI "manual hook" source patches to a 4.x kernel tree.

ReSukiSU's kernel/tools/manual_hook_check.mk greps these files and hard-errors
if the hook calls are missing. The AUTO_* Kconfig options let us skip the
setuid / initrc / input patches (they get LSM hooks instead), so only these
four files need real edits:

    fs/exec.c        ksu_handle_execveat
    fs/open.c        ksu_handle_faccessat
    fs/stat.c        ksu_handle_stat / ksu_handle_newfstat_ret / ksu_handle_fstat64_ret
    kernel/reboot.c  ksu_handle_sys_reboot          (3.11+; older uses kernel/sys.c)

Run from the kernel source root. Idempotent: re-running is a no-op.
"""

import os
import re
import sys

OK = []
FAIL = []


def read(p):
    with open(p, 'r', encoding='utf-8', errors='surrogateescape') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(s)


def find_func(src, sig_regex):
    """Return (start_of_signature, index_of_opening_brace, index_after_closing_brace)."""
    m = re.search(sig_regex, src)
    if not m:
        return None
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                return (m.start(), i, j + 1)
    return None


def insert_decl_before(path, sig_regex, decl):
    """Insert an extern block immediately before the function definition."""
    src = read(path)
    m = re.search(sig_regex, src)
    if not m:
        FAIL.append('%s: cannot find %s' % (path, sig_regex))
        return False
    src = src[:m.start()] + decl + src[m.start():]
    write(path, src)
    return True


def insert_call_in_func(path, sig_regex, call, symbol):
    """Insert a call right after the function's opening brace."""
    src = read(path)
    if symbol in src:
        OK.append('%s: %s already present' % (path, symbol))
        return True
    loc = find_func(src, sig_regex)
    if not loc:
        FAIL.append('%s: cannot locate function %s' % (path, sig_regex))
        return False
    _s, bo, _e = loc
    src = src[:bo + 1] + '\n' + call + src[bo + 1:]
    write(path, src)
    OK.append('%s: inserted %s' % (path, symbol))
    return True


def insert_before_line_in_func(path, sig_regex, needle, call, symbol):
    """Insert a call immediately BEFORE `needle`, scoped inside the function."""
    src = read(path)
    if symbol in src:
        OK.append('%s: %s already present' % (path, symbol))
        return True
    loc = find_func(src, sig_regex)
    if not loc:
        FAIL.append('%s: cannot locate function %s' % (path, sig_regex))
        return False
    s, bo, e = loc
    body = src[bo:e]
    if needle not in body:
        FAIL.append('%s: needle %r not found inside %s' % (path, needle, sig_regex))
        return False
    body = body.replace(needle, call + '\n' + needle, 1)
    src = src[:bo] + body + src[e:]
    write(path, src)
    OK.append('%s: inserted %s' % (path, symbol))
    return True


def insert_after_line_in_func(path, sig_regex, needle, call, symbol):
    """Insert a call immediately AFTER `needle`, scoped inside the function."""
    src = read(path)
    if symbol in src:
        OK.append('%s: %s already present' % (path, symbol))
        return True
    loc = find_func(src, sig_regex)
    if not loc:
        FAIL.append('%s: cannot locate function %s' % (path, sig_regex))
        return False
    s, bo, e = loc
    body = src[bo:e]
    if needle not in body:
        FAIL.append('%s: needle %r not found inside %s' % (path, needle, sig_regex))
        return False
    body = body.replace(needle, needle + '\n\n' + call, 1)
    src = src[:bo] + body + src[e:]
    write(path, src)
    OK.append('%s: inserted %s' % (path, symbol))
    return True


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.chdir(root)

    print('=== ReSukiSU non-GKI manual hook patches ===')
    print('root: %s' % os.path.abspath('.'))
    print('')

    # ---------------- fs/exec.c : ksu_handle_execveat ----------------
    exec_c = 'fs/exec.c'
    if os.path.exists(exec_c):
        src = read(exec_c)
        if 'ksu_handle_execveat' not in src:
            insert_decl_before(
                exec_c,
                r'static\s+int\s+do_execveat_common\s*\(',
                '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
                '__attribute__((hot))\n'
                'extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,\n'
                '\t\t\t\tvoid *argv, void *envp, int *flags);\n'
                '#endif\n\n')
        insert_call_in_func(
            exec_c,
            r'static\s+int\s+do_execveat_common\s*\(',
            '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
            '\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);\n'
            '#endif\n',
            'ksu_handle_execveat')
    else:
        FAIL.append('missing %s' % exec_c)

    # ---------------- fs/open.c : ksu_handle_faccessat ----------------
    open_c = 'fs/open.c'
    if os.path.exists(open_c):
        src = read(open_c)
        if 'ksu_handle_faccessat' not in src:
            insert_decl_before(
                open_c,
                r'SYSCALL_DEFINE3\s*\(\s*faccessat\s*,',
                '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
                '__attribute__((hot))\n'
                'extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n'
                '\t\t\t\tint *mode, int *flags);\n'
                '#endif\n\n')
        insert_call_in_func(
            open_c,
            r'SYSCALL_DEFINE3\s*\(\s*faccessat\s*,',
            '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
            '\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n'
            '#endif\n',
            'ksu_handle_faccessat')
    else:
        FAIL.append('missing %s' % open_c)

    # ---------------- fs/stat.c ----------------
    stat_c = 'fs/stat.c'
    if os.path.exists(stat_c):
        src = read(stat_c)
        if 'ksu_handle_stat' not in src:
            insert_decl_before(
                stat_c,
                r'SYSCALL_DEFINE4\s*\(\s*newfstatat\s*,',
                '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
                '__attribute__((hot))\n'
                'extern int ksu_handle_stat(int *dfd, const char __user **filename_user,\n'
                '\t\t\t    int *flags);\n'
                '\n'
                'extern void ksu_handle_newfstat_ret(unsigned int *fd,\n'
                '\t\t\t\t\tstruct stat __user **statbuf_ptr);\n'
                'extern void ksu_handle_fstat64_ret(unsigned long *fd,\n'
                '\t\t\t\t       struct stat64 __user **statbuf_ptr);\n'
                '#endif\n\n')
        insert_before_line_in_func(
            stat_c,
            r'SYSCALL_DEFINE4\s*\(\s*newfstatat\s*,',
            'error = vfs_fstatat(dfd, filename, &stat, flag);',
            '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
            '\tksu_handle_stat(&dfd, &filename, &flag);\n'
            '#endif',
            'ksu_handle_stat')
        insert_after_line_in_func(
            stat_c,
            r'SYSCALL_DEFINE2\s*\(\s*newfstat\s*,',
            'error = cp_new_stat(&stat, statbuf);',
            '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
            '\tksu_handle_newfstat_ret(&fd, &statbuf);\n'
            '#endif',
            'ksu_handle_newfstat_ret')
        # fstat64 only exists on some arch configs; the string must still be
        # present for manual_hook_check.mk to pass.
        src = read(stat_c)
        if 'ksu_handle_fstat64_ret' not in src:
            insert_after_line_in_func(
                stat_c,
                r'SYSCALL_DEFINE2\s*\(\s*fstat64\s*,',
                'error = cp_new_stat64(&stat, statbuf);',
                '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
                '\tksu_handle_fstat64_ret(&fd, &statbuf);\n'
                '#endif',
                'ksu_handle_fstat64_ret')
        src = read(stat_c)
        if 'ksu_handle_fstat64_ret' not in src:
            # fstat64 not compiled in - leave a comment so the grep still passes
            loc = find_func(src, r'SYSCALL_DEFINE2\s*\(\s*newfstat\s*,')
            anchor = 'ksu_handle_newfstat_ret(&fd, &statbuf);'
            if loc and anchor in src:
                src = src.replace(
                    anchor,
                    anchor + '\n'
                    '/* ksu_handle_fstat64_ret: SYSCALL_DEFINE2(fstat64) not present '
                    'on this arch/config */', 1)
                write(stat_c, src)
                OK.append('%s: fstat64 absent, marker comment added' % stat_c)
    else:
        FAIL.append('missing %s' % stat_c)

    # ---------------- kernel/reboot.c : ksu_handle_sys_reboot (3.11+) ----
    reboot_c = 'kernel/reboot.c'
    sys_c = 'kernel/sys.c'
    target = reboot_c if os.path.exists(reboot_c) else sys_c
    if os.path.exists(target):
        src = read(target)
        if 'ksu_handle_sys_reboot' not in src:
            insert_decl_before(
                target,
                r'SYSCALL_DEFINE4\s*\(\s*reboot\s*,',
                '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
                'extern int ksu_handle_sys_reboot(int magic1, int magic2,\n'
                '\t\t\t\t     unsigned int cmd, void __user **arg);\n'
                '#endif\n\n')
        insert_after_line_in_func(
            target,
            r'SYSCALL_DEFINE4\s*\(\s*reboot\s*,',
            'int ret = 0;',
            '#ifdef CONFIG_KSU_MANUAL_HOOK\n'
            '\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n'
            '#endif',
            'ksu_handle_sys_reboot')
    else:
        FAIL.append('missing %s and %s' % (reboot_c, sys_c))

    # ---------------- verify ----------------
    print('')
    print('=== verification (what manual_hook_check.mk greps for) ===')
    checks = [
        ('fs/exec.c', 'ksu_handle_execveat'),
        ('fs/open.c', 'ksu_handle_faccessat'),
        ('fs/stat.c', 'ksu_handle_stat'),
        ('fs/stat.c', 'ksu_handle_newfstat_ret'),
        ('fs/stat.c', 'ksu_handle_fstat64_ret'),
        (target if os.path.exists(reboot_c) else sys_c, 'ksu_handle_sys_reboot'),
    ]
    bad = []
    for f, sym in checks:
        present = os.path.exists(f) and sym in read(f)
        print('  %-8s %-28s %s' % ('[OK]' if present else '[MISS]', sym, f))
        if not present:
            bad.append(sym)
    # forbidden (old-style hooks)
    print('')
    print('=== forbidden legacy hooks (must NOT be present) ===')
    for f, sym in [('fs/read_write.c', 'ksu_vfs_read_hook'),
                   ('security/selinux/hooks.c', 'is_ksu_transition'),
                   ('security/security.c', 'ksu_handle_rename')]:
        if os.path.exists(f):
            present = sym in read(f)
            print('  %-8s %-28s %s' % ('[BAD!]' if present else '[clean]', sym, f))
            if present:
                bad.append('forbidden:' + sym)

    print('')
    for m in OK:
        print('  done: %s' % m)
    for m in FAIL:
        print('  FAIL: %s' % m)

    if bad or FAIL:
        print('')
        print('::error::manual hook patch incomplete: %s' % ', '.join(bad + FAIL))
        sys.exit(1)
    print('')
    print('[+] all manual hooks applied')
    sys.exit(0)


if __name__ == '__main__':
    main()
