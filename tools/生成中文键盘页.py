#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从游戏名统计用字 → 生成 RetroArch 中文键盘页的 C 代码

用法:
    python3 生成中文键盘页.py [播放列表目录] [输出文件]

设计:
    每个键盘页 4 行 × 11 列 = 44 格
      第1行: 1..0 + ⇦          (11 格，功能键)
      第2行: 10 个汉字 + ⏎      (11 格)
      第3行: 10 个汉字 + ⇩      (11 格)
      第4行: 10 个汉字 + ⌂      (11 格)
    => 每页放 30 个汉字

    ⚠️ 历史 bug: 旧版每页只塞 29 个却按 40 算页数 → 末尾 332 个字被吞掉。
       改成 30/页 并把 npages 按 30 算，保证一个字都不丢。

输出:
    chinese_osk_pages.h   直接 cp 到 RetroArch 的 input/ 目录
"""

import sys, os, glob, json, collections

try:
    from pypinyin import lazy_pinyin
except ImportError:
    print("❌ 需要 pypinyin:  pip install --break-system-packages pypinyin")
    sys.exit(1)

DEFAULT_IN = os.path.expanduser('~/手机备份/Redmi10X-playlists/加工版')
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '构建产物', 'chinese_osk_pages.h')

CHARS_PER_PAGE = 30      # ⚠️ 必须和 emit_page 里实际塞的字数一致！
COLS = 11


def collect_chars(d):
    counter = collections.Counter()
    files = glob.glob(os.path.join(d, '*.lpl'))
    if not files:
        print(f"❌ {d} 里没有 .lpl 文件")
        sys.exit(1)
    for f in files:
        try:
            txt = open(f, 'rb').read().decode('utf-8', errors='surrogateescape')
            data = json.loads(txt)
        except Exception as e:
            print(f"  ⚠️ 跳过 {os.path.basename(f)}: {e}", file=sys.stderr)
            continue
        for it in data.get('items', []):
            for ch in it.get('label', ''):
                if '\u4e00' <= ch <= '\u9fff':
                    counter[ch] += 1
    return counter


def group_by_initial(counter):
    groups = collections.defaultdict(list)
    for ch, cnt in counter.most_common():
        py = lazy_pinyin(ch)
        if not py or not py[0]:
            continue
        ini = py[0][0].lower()
        if 'a' <= ini <= 'z':
            groups[ini].append((ch, cnt))
    return groups


def emit_page(fh, name, chars):
    """输出一个 4x11 的键盘页 —— 正好 30 个汉字 + 14 个功能键 = 44 格"""
    pool = [c for c, _ in chars]
    pool = (pool + [''] * CHARS_PER_PAGE)[:CHARS_PER_PAGE]
    it = iter(pool)

    row1 = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\u21e6"]   # ⇦
    row2 = [next(it) for _ in range(10)] + ["\u23ce"]                      # ⏎
    row3 = [next(it) for _ in range(10)] + ["\u21e9"]                      # ⇩
    row4 = [next(it) for _ in range(10)] + ["\u2302"]                      # ⌂

    total = len(row1) + len(row2) + len(row3) + len(row4)
    assert total == 44, f"{name} 有 {total} 格，必须是 44"

    fh.write(f"static const char *{name}[] = {{\n")
    for r in (row1, row2, row3, row4):
        vals = ",".join(f'"{c}"' if c else '""' for c in r)
        fh.write(f"    {vals},\n")
    fh.write("};\n\n")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IN
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    counter = collect_chars(src)
    groups = group_by_initial(counter)
    total_chars = sum(len(v) for v in groups.values())

    fh = open(dst, 'w', encoding='utf-8')
    fh.write("/* 自动生成 —— 不要手工改 */\n")
    fh.write("/* 由 生成中文键盘页.py 生成 */\n")
    fh.write(f"/* 语料: {src} */\n")
    fh.write(f"/* 不同汉字 {total_chars} 个，出现 {sum(counter.values())} 次 */\n")
    fh.write("#ifndef CHINESE_OSK_PAGES_H\n#define CHINESE_OSK_PAGES_H\n\n")

    pages = []
    for ini in 'abcdefghijklmnopqrstuvwxyz':
        lst = groups.get(ini, [])
        if not lst:
            continue
        npages = (len(lst) + CHARS_PER_PAGE - 1) // CHARS_PER_PAGE
        fh.write(f"/* {ini}: {len(lst)} 字 → {npages} 页 */\n")
        for p in range(npages):
            chunk = lst[p * CHARS_PER_PAGE:(p + 1) * CHARS_PER_PAGE]
            name = f"chinese_page_{ini}_{p + 1}"
            emit_page(fh, name, chunk)
            pages.append((ini, p + 1, len(chunk)))

    fh.write("/* 声母索引页 */\n")
    fh.write("static const char *chinese_index_grid[] = {\n")
    fh.write('    "1","2","3","4","5","6","7","8","9","0","\u21e6",\n')
    fh.write('    "a","b","c","d","e","f","g","h","i","j","\u23ce",\n')
    fh.write('    "k","l","m","n","o","p","q","r","s","t","\u21e9",\n')
    fh.write('    "u","v","w","x","y","z","\'","_",".","\u2302"};\n\n')

    # ⚠️ 这里不能再输出 osk_chinese_first_page / osk_chinese_page_count：
    #    input/input_driver.c 里已经有一张同名的 enum 表，重名会编译失败。
    #    页数信息对切页逻辑没用（切页靠 enum 顺序 + OSK_TYPE_LAST）。

    fh.write("#endif\n")
    fh.close()

    # ── 自检：字数对得上吗 ──
    written = sum(n for _, _, n in pages)
    print(f"  语料不同汉字: {total_chars}")
    print(f"  写入汉字数:   {written}")
    print(f"  页数:         {len(pages)}")
    if written != total_chars:
        print(f"  ❌ 丢了 {total_chars - written} 个字！", file=sys.stderr)
        sys.exit(2)
    print(f"  ✅ 一个字没丢")
    print(f"  输出: {dst}  ({os.path.getsize(dst)} 字节)")


if __name__ == '__main__':
    main()
