#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把源码里的中文键盘页从旧版（44 页 / 1183 字）升级到新版（63 页 / 1515 字）

同步 4 个地方：
  1. input/chinese_osk_pages.h    ← 直接覆盖成新头文件
  2. input/input_osk.h            ← enum 的 OSK_CHINESE_* 条目
  3. input/input_driver.c         ← osk_chinese_first_page[26] 首指针表
  4. menu/menu_driver.c           ← switch (OSK_CHINESE_* -> memcpy) 的 case

用法:
    python3 升级字表.py [--dry-run]
"""
import os, re, sys, shutil

SRC   = os.path.expanduser('~/retroarch-cn/src/RetroArch')
NEWH  = os.path.expanduser('~/游戏/掌机/红米10X/RetroArch中文输入/构建产物/chinese_osk_pages.h')
DRY   = '--dry-run' in sys.argv

LETTERS = 'abcdefghijklmnopqrstuvwxyz'


def read(p):
    return open(p, encoding='utf-8').read()


def write(p, s):
    if DRY:
        print(f"    [dry-run] 会写 {p} ({len(s)} 字节)")
        return
    shutil.copy2(p, p + '.bak-升级前')
    open(p, 'w', encoding='utf-8').write(s)


def parse_pages(hdr):
    """从新头文件里解析出 {字母: 页数} 和页顺序列表"""
    pages = re.findall(r'static const char \*(chinese_page_([a-z])_(\d+))\[\]', hdr)
    order = [(m[0], m[1], int(m[2])) for m in pages]
    per = {}
    for _, ini, n in order:
        per[ini] = max(per.get(ini, 0), n)
    return order, per


def main():
    hdr = read(NEWH)
    order, per = parse_pages(hdr)
    print(f"  新头文件: {len(order)} 页")
    print(f"  各字母页数: " + ' '.join(f"{k}{per[k]}" for k in sorted(per)))

    # ── 1. input_osk.h 的枚举 ──
    p = os.path.join(SRC, 'input/input_osk.h')
    s = read(p)
    old_enums = re.findall(r'^\s+(OSK_CHINESE_\w+),$', s, re.M)
    lines = ['   OSK_CHINESE_INDEX,']
    for name, ini, n in order:
        lines.append(f"   OSK_CHINESE_{ini.upper()}_{n},")   # ★ 干净命名
    new_block = '\n'.join(lines) + '\n'
    # ⚠️ 不能用非贪婪 .*? —— 会在第一个 OSK_CHINESE_ 就停。
    #    用位置法：从 OSK_CHINESE_INDEX 起，到最后一个 OSK_CHINESE_xxx, 行尾
    try:
        estart = s.index('   OSK_CHINESE_INDEX,')
    except ValueError:
        print("  ❌ 找不到 input_osk.h 的 OSK_CHINESE_INDEX")
        return 1
    epos = [m.start() for m in re.finditer(r'^\s+OSK_CHINESE_\w+,\s*$', s, re.M)
            if m.start() >= estart]
    if not epos:
        print("  ❌ 找不到枚举条目")
        return 1
    eend = s.index('\n', epos[-1]) + 1
    s2 = s[:estart] + new_block + s[eend:]
    print(f"  input_osk.h: {len(old_enums)} → {len(lines)} 条")
    write(p, s2)

    # ── 2. input_driver.c 的首指针表 ──
    p = os.path.join(SRC, 'input/input_driver.c')
    s = read(p)
    entries = []
    for ini in LETTERS:
        entries.append(f"OSK_CHINESE_{ini.upper()}_1" if ini in per else "OSK_TYPE_UNKNOWN")
    tbl = ("static const enum osk_type osk_chinese_first_page[] = {\n"
           + ''.join(f"   {e},{' ' * max(1, 19 - len(e))}"
                     + (f"/* {c} */" if False else '')
                     + ('' if i % 4 != 3 else '')
                     + ('\n' if i % 4 == 3 or i == 25 else '')
                     for i, e in enumerate(entries))
           + "};\n")
    pat = re.compile(r'static const enum osk_type osk_chinese_first_page\[\] = \{.*?\};\n', re.S)
    m = pat.search(s)
    if not m:
        print("  ❌ 找不到 osk_chinese_first_page 表")
        return 1
    s2 = s[:m.start()] + tbl + s[m.end():]
    print(f"  input_driver.c: 首指针表 {len(entries)} 项")
    write(p, s2)

    # ── 3. menu_driver.c 的 switch ──
    p = os.path.join(SRC, 'menu/menu_driver.c')
    s = read(p)
    cases = []
    cases.append("      case OSK_CHINESE_INDEX:\n"
                 "         memcpy(osk_grid,\n"
                 "               chinese_index_grid,\n"
                 "               sizeof(chinese_index_grid));\n"
                 "         break;\n")
    for name, ini, n in order:
        cases.append(f"      case OSK_CHINESE_{ini.upper()}_{n}:\n"
                     f"         memcpy(osk_grid,\n"
                     f"               {name},\n"
                     f"               sizeof({name}));\n"
                     f"         break;\n")
    new_cases = '\n'.join(cases)
    # ⚠️ 不能用非贪婪 .*? —— 会在第一个 break 就停。
    #    改成：定位 INDEX 起点 → 找最后一个 OSK_CHINESE_ case 的块尾
    try:
        start = s.index('      case OSK_CHINESE_INDEX:')
    except ValueError:
        print("  ❌ 找不到 menu_driver.c 的 OSK_CHINESE_INDEX")
        return 1
    positions = [m.start() for m in re.finditer(r'      case OSK_CHINESE_', s)
                 if m.start() >= start]
    if not positions:
        print("  ❌ 找不到 menu_driver.c 的 OSK_CHINESE_ case")
        return 1
    last_start = positions[-1]
    tail_m = re.search(r'      case OSK_CHINESE_\w+:\n(?:.*?\n)*?         break;\n',
                       s[last_start:], re.S)
    if not tail_m:
        print("  ❌ 找不到最后一个 case 的结尾")
        return 1
    end = last_start + tail_m.end()
    old_n = len(re.findall(r'case OSK_CHINESE_', s[start:end]))
    s2 = s[:start] + new_cases + s[end:]
    print(f"  menu_driver.c: switch {old_n} → {len(cases)} 个 case")
    write(p, s2)

    # ── 4. 覆盖头文件 ──
    p = os.path.join(SRC, 'input/chinese_osk_pages.h')
    if DRY:
        print(f"    [dry-run] 会覆盖 {p}")
    else:
        shutil.copy2(p, p + '.bak-升级前')
        shutil.copy2(NEWH, p)
    print(f"  chinese_osk_pages.h: 已覆盖成新头文件")

    print()
    print("  ✅ 升级完成（.bak-升级前 是备份）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
