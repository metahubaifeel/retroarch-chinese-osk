#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 chinese_osk_pages.h 重新排版成 RetroArch OSK 要求的 4 行 x 11 列 = 44 格。

原始文件有两个数据错误：
  1. 字母页每页 45 个元素 —— 第 4 行有 12 格（9 个汉字 + " " + "," + ⌂）。
     网格选择是 memcpy(osk_grid, page, sizeof(page))，
     osk_grid 是 char*[45]，多出来的一个元素会把结尾的 NULL 顶掉。
  2. 索引页只有 43 个元素 —— 第 4 行少一格。

本脚本按原始顺序保留全部汉字，每页排成：
  第 1 行  10 汉字 + ⇦ (退格)
  第 2 行  10 汉字 + ⏎ (回车)
  第 3 行  10 汉字 + ⇧ (回索引页)
  第 4 行  10 汉字 + ⊕ (下一页)
不足的位置填 ""（空键，点下去无动作）。

功能键只用 ⇦ ⏎ ⇧ ⊕ —— 内置字体（rgui_bitmapfont.c）只覆盖
0x0-0xFF / 0x100-0x24F / 0x3000-0x30FF / 0x4E00-0x9FFF / 0xAC00-0xD7A3，
⌂(U+2302) 落在空洞里，画不出来。
"""

import re
import sys
import collections

SRC = "/home/amd/游戏/掌机/红米10X/RetroArch中文输入/构建产物/chinese_osk_pages.h"
DST = "/home/amd/retroarch-cn/src/RetroArch/input/chinese_osk_pages.h"

BACKSPACE, ENTER, HOME, NEXT = "⇦", "⏎", "⇧", "⊕"
# 原始文件里当模板填充用的字符，不算汉字内容
# （数字是第 1 行的模板格，不是内容；只有索引页才有数字键）
TEMPLATE = set("0123456789")
TEMPLATE |= {"", " ", ",", BACKSPACE, ENTER, HOME, NEXT, "⇩", "⌂"}
CONTENT_PER_PAGE = 40
COLS = 11


def load_letters(path):
    """返回 {首字母: [汉字, ...]}，保持原始（按频率降序）的顺序。"""
    src = open(path, encoding="utf-8").read()
    arrays = re.findall(r"static const char \*(\w+)\[\] = \{(.*?)\};", src, re.S)
    pages = collections.defaultdict(dict)
    for name, body in arrays:
        m = re.match(r"chinese_page_([a-z])_(\d+)$", name)
        if not m:
            continue
        toks = re.findall(r'"((?:[^"\\]|\\.)*)"', body)
        pages[m.group(1)][int(m.group(2))] = toks

    letters = collections.OrderedDict()
    for letter in sorted(pages):
        seq, seen = [], set()
        for _, toks in sorted(pages[letter].items()):
            for t in toks:
                if t in TEMPLATE or t in seen:
                    continue
                seen.add(t)
                seq.append(t)
        letters[letter] = seq
    return letters


def cstr(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def emit_page(name, chars):
    """chars 最多 40 个，输出 44 个元素的数组。"""
    cells = list(chars) + [""] * (CONTENT_PER_PAGE - len(chars))
    rows = [
        cells[0:10] + [BACKSPACE],
        cells[10:20] + [ENTER],
        cells[20:30] + [HOME],
        cells[30:40] + [NEXT],
    ]
    assert len(cells) == CONTENT_PER_PAGE
    for r in rows:
        assert len(r) == COLS, (name, len(r))
    out = ["static const char *%s[] = {" % name]
    for i, r in enumerate(rows):
        end = "};" if i == 3 else ","
        out.append("                          %s%s"
                   % (",".join(cstr(c) for c in r), end))
    return "\n".join(out)


def emit_index():
    rows = [
        [str((i + 1) % 10) for i in range(10)] + [BACKSPACE],
        list("abcdefghij") + [ENTER],
        list("klmnopqrst") + [HOME],
        list("uvwxyz") + ["'", "_", ".", " "] + [NEXT],
    ]
    for r in rows:
        assert len(r) == COLS, len(r)
    out = ["static const char *chinese_index_grid[] = {"]
    for i, r in enumerate(rows):
        end = "};" if i == 3 else ","
        out.append("                          %s%s"
                   % (",".join(cstr(c) for c in r), end))
    return "\n".join(out)


def main():
    letters = load_letters(SRC)
    total_chars = sum(len(v) for v in letters.values())

    pages = collections.OrderedDict()   # (letter, page_no) -> chars
    for letter, seq in letters.items():
        for i in range(0, len(seq), CONTENT_PER_PAGE):
            pages[(letter, i // CONTENT_PER_PAGE + 1)] = seq[i:i + CONTENT_PER_PAGE]

    body = ["/* 自动生成 —— 不要手工改（生成脚本：构建产物/gen_chinese_osk_pages.py） */",
            "/* 来源: /home/amd/手机备份/Redmi10X-playlists/加工版 */",
            "#ifndef CHINESE_OSK_PAGES_H",
            "#define CHINESE_OSK_PAGES_H",
            "",
            "/* %d 个汉字，%d 页，每页 40 字 + 4 个功能键 = 44 格 */"
            % (total_chars, len(pages)),
            ""]
    for letter, seq in letters.items():
        body.append("/* %s: %d 字 -> %d 页 */"
                    % (letter, len(seq),
                       -(-len(seq) // CONTENT_PER_PAGE)))
    body.append("")

    for (letter, no), chars in pages.items():
        body.append(emit_page("chinese_page_%s_%d" % (letter, no), chars))
        body.append("")

    body.append("/* 声母索引页 */")
    body.append(emit_index())
    body.append("")
    body.append("#endif")
    body.append("")

    open(DST, "w", encoding="utf-8").write("\n".join(body))
    print("wrote %s" % DST)
    print("汉字 %d 个，字母页 %d 页 + 索引页 1 页 = %d 个枚举值"
          % (total_chars, len(pages), len(pages) + 1))
    print()
    print("=== input_osk.h 枚举 ===")
    print("   OSK_CHINESE_INDEX,")
    for (letter, no), _ in pages.items():
        print("   OSK_CHINESE_%s_%d," % (letter.upper(), no))
    print()
    print("=== input_driver.c 首字母 -> 页码表 ===")
    first = {}
    for (letter, no) in pages:
        first.setdefault(letter, "OSK_CHINESE_%s_%d" % (letter.upper(), no))
    names = []
    for i in range(26):
        c = chr(ord("a") + i)
        names.append(first.get(c, "OSK_TYPE_UNKNOWN"))
    for i in range(0, 26, 4):
        print("      " + ", ".join(names[i:i + 4]) + ",")
    print()
    print("=== menu/menu_driver.c 网格 switch ===")
    print("      case OSK_CHINESE_INDEX:")
    print("         memcpy(osk_grid, chinese_index_grid,")
    print("               sizeof(chinese_index_grid));")
    print("         break;")
    for (letter, no), _ in pages.items():
        n = "chinese_page_%s_%d" % (letter, no)
        print("      case OSK_CHINESE_%s_%d:" % (letter.upper(), no))
        print("         memcpy(osk_grid, %s, sizeof(%s));" % (n, n))
        print("         break;")


if __name__ == "__main__":
    sys.exit(main())
