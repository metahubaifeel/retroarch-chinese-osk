> # 🔴 先看这个
>
> **RetroArch 1.22 起原生支持 Android 系统输入法**（`input_android_system_keyboard`，默认开），
> 可以直接用 Gboard / 讯飞 / 百度 / 搜狗打中文 —— **不需要本项目的中文键盘页**。
> 详见 [docs/重要发现-1.22支持系统输入法.md](docs/重要发现-1.22支持系统输入法.md)。
>
> **本项目的适用场景**：RetroArch < 1.22、系统输入法不可用、或想要手柄式点选。
> 系统键盘在时优先用系统键盘，两者不冲突。
>
> ---

# RetroArch 中文键盘（拼音声母索引页）

> **v2 更新（当前）**：字表从 1183 字扩到 **1515 字 / 63 页**（生成器的分页 bug 已修），
> APK 补上了 **assets（9489 项：菜单主题 / 着色器 / 手柄配置 / 数据库）**，
> 现在是 **167.7 MB 的完整版**，和官方包体量一致。
> 见 [docs/编译与实测记录.md](docs/编译与实测记录.md)。


给 RetroArch 的自绘键盘加一套**中文页**，让菜单里的搜索框能直接点出汉字。

不接 Android 输入法，不动 Java 层 —— 纯 C，沿用上游已有的多语言键盘页机制
（韩文/日文页就是这套机制），新增一个「拼音声母索引页 + 63 个字母页」的键盘布局。

---

## 一、为什么 RetroArch 菜单搜不了中文

RetroArch 的菜单搜索框**不是**系统输入框，它是自己画出来的键盘
（`menu_input_dialog` / `input_event_osk_append`）：

```
RetroArch 菜单搜索框
   ↓
自绘键盘（OSK），只认键盘格子上摆的那些字符
   ↓
从不调用 Android 的 InputMethodManager / showSoftInput
   ↓
系统输入法（Gboard / 讯飞）的输出根本进不来
```

对照实验（从设备上抽 APK 验证）：

```bash
unzip base.apk classes*.dex lib/arm64-v8a/libretroarch-activity.so
strings classes*.dex | grep -iE "InputMethod|showSoftInput|InputMethodManager"
#   → 只有 attemptToggleImmersiveMode（状态栏沉浸，不是输入法）
strings lib/arm64-v8a/libretroarch-activity.so | grep -iE "input_method|soft_keyboard"
#   → 无 IME 接口
```

**结论：RetroArch Android 完全没接系统输入法，能输入什么完全由键盘页决定。**

---

## 二、上游已经有的机制（本项目不是从零造）

社区做过同样的事，而且已经合并进 master：

| PR | 状态 | 内容 |
|---|---|---|
| [#14654](https://github.com/libretro/RetroArch/pull/14654) | closed（未合并） | "Extended ime and korean osk" 初版 |
| [#14676](https://github.com/libretro/RetroArch/pull/14676) | ✅ **已合并 2022-11-29**，+369 / −86，6 个文件 | "Extended IME and Korean OSK - rebased PR" |

PR #14676 引入的正是本项目依赖的三样东西：

1. **`HAVE_LANGEXTRA` 编译开关下的多语言键盘页**（`input/input_osk_utf8_pages.h`）
2. **日文平假名/片假名页**（`hiragana_page1/2`、`katakana_page1/2`）
3. **韩文谚文页**（`korean_page1_grid`）+ Windows 端 imm32 系统输入法

Android 构建里 `HAVE_LANGEXTRA` 是**无条件打开**的，不用改 configure：

```make
# pkg/android/phoenix-common/jni/Android.mk:122
-DHAVE_LANGEXTRA \
```

### 那为什么中文一直没人做

因为字符量不是一个量级：

| 语言 | 字符数 | 塞进 44 格键盘 |
|---|---|---|
| 韩文 | 24 个基本字母（组合成音节）| ✅ 一页 |
| 日文假名 | 46 平 + 46 片 | ✅ 两页 |
| **中文** | 常用 3,500 / 全部 20,000+ | ❌ 不可能 |

韩文/日文一个人几天就能写完；中文要么几百页，要么接系统输入法。
**所以中文页是「没人愿意啃」，不是「做不到」—— 本项目补的就是这一块。**

---

## 三、键盘长什么样

复用现有 4 行 × 11 列 = **44 格**的网格。第 0 页是拼音声母索引页：

```
┌─────────────────────────────────────────────┐
│ 1  2  3  4  5  6  7  8  9  0  ⇦             │
│ a  b  c  d  e  f  g  h  i  j  ⏎             │
│ k  l  m  n  o  p  q  r  s  t  ⇧             │
│ u  v  w  x  y  z  '  _  .     ⊕             │
└─────────────────────────────────────────────┘
        ↓ 点某个声母（例：l）
┌─────────────────────────────────────────────┐
│ 洛 龙 绿 蓝 雷 灵 拉 旅 落 浪  ⇦             │   ← 40 字/页，按语料出现频率降序
│ 兰 烈 鹿 冷 莲 流 猎 林 立 罗  ⏎             │
│ 陆 岚 狼 亮 丽 蕾 链 黎 莉 梁  ⇧             │   ← ⇧ = 回声母索引页
│ 路 卢 炉 鲁 露 屡 吕 律 滤 略  ⊕             │   ← ⊕ = 本字母的下一页
└─────────────────────────────────────────────┘
```

- **索引页上按 `⇧`** → 退出中文键盘，回到原来的拉丁键盘（否则进了中文区只能一路翻页出来）
- **字母页上按 `⇧`** → 回索引页
- 点汉字 → 直接追加到搜索框。**中文比韩文简单：韩文要 3 个字母组合成 1 个音节，
  汉字本身就是完整字符，append 即可，不需要组字状态机。**

### 实际搜一个游戏的流程

```
搜「绿宝石」
  点 l → 跳 l 第 1 页 → 点「绿」   → 搜索框：绿
  点 ⇧ → 回索引页
  点 b → 点「宝」                  → 搜索框：绿宝
  点 ⇧ → 点 s → 点「石」            → 搜索框：绿宝石  ✅
```

字不在第 1 页就点 `⊕` 翻下一页（b/c/d…z 多的有 3 页）。

---

## 四、当前完成度（请按实读）

| 项 | 状态 |
|---|---|
| 改动代码 | ✅ 完成，5 个文件 +311 行（另 1 个打包文件） |
| 本地编译验证 | ✅ `input_driver.o` / `menu_driver.o` 零报错零警告（`-Wall -Wextra`）|
| 数据完整性 | ✅ 45 个页数组 × **每个恰好 44 格**；枚举 45 个 ↔ 数据 45 页 ↔ menu switch 45 个 case，三方一致 |
| **Android APK 编译** | ✅ `BUILD SUCCESSFUL in 3m 21s`，7.1 MB |
| 汉字进没进二进制 | ✅ 从 APK 里抽出 `libretroarch-activity.so` 逐字比对：**1187 个字符串一个不丢**（1183 汉字 + 4 个功能键）|
| **真机实测** | ❌ **没做成** —— 见下 |

### 真机测试为什么没做

APK 编出来了，但装不进手机，卡在 MIUI 的开关上：

```
$ adb install -r RetroArch-CN-aarch64-v8a-release.apk
Failure [INSTALL_FAILED_USER_RESTRICTED: Install canceled by user]

# 换四条路（--user 0 / push+pm install / -i com.android.vending）都是同一个错
# 手机上连确认弹窗都不弹 —— MIUI 是静默拒绝
# 顺带：adb 模拟点击也被禁
$ adb shell input keyevent KEYCODE_BACK
java.lang.SecurityException: Injecting to another application requires INJECT_EVENTS permission
```

两个都是同一个开关管的：**设置 → 更多设置 → 开发者选项 → 「USB调试（安全设置）」**。
开关没打开，所以：

> **这套键盘「能编译、数据正确、进了二进制」，但「点上去好不好用、翻页顺不顺手」
> 没有任何真机验证。** 谁先装上，欢迎反馈。

### APK 还缺 assets（不影响键盘，影响外观）

编出来只有 7.1 MB，官方 APK 是 150 MB 上下。差的不是编译失误：
`pkg/android/phoenix/assets/` 在仓库 `.gitignore` 里，官方打包时是从 5 个外部仓库
（retroarch-assets、common-shaders、common-overlays、joypad-autoconfig、libretro-database）
灌进去的，那个打包脚本不在源码仓库里。

**实际影响**：新包名 = 全新数据目录，装上是个「空壳」—— 没有 xmb/ozone/glui 主题、
着色器、手柄自动配置、缩略图库。程序能启动、中文键盘能用、游戏能跑（rgui 菜单是代码画的），
但菜单会缺图标主题。补法：装完在 Settings → Directory 里把 Assets 指向已有的 assets 目录。

---

## 五、怎么编译

### 依赖版本（实测通过的一套，照抄即可）

| 组件 | 版本 |
|---|---|
| JDK | 17（`jdk-17.0.19+10`）|
| Gradle | 9.3.1 |
| Android Gradle Plugin | 9.1.0 |
| compileSdk / targetSdk | 36 |
| build-tools | 36.0.0 |
| NDK | 29.0.14206865 |
| ABI | arm64-v8a |

源码树要的 Gradle/AGP/SDK 版本比机器上默认的高，用 `sdkmanager` 补齐缺的组件。

### 步骤

```bash
# 1) 拿源码，检出本项目对应的基线
git clone https://github.com/libretro/RetroArch.git
cd RetroArch
git checkout 6400e21b86deb37c5062d7e98614267ee05da593   # 本 patch 的基线

# 2) 打补丁
git apply /path/to/patch/0001-chinese-osk.patch
git apply /path/to/patch/0002-android-package-rename.patch   # 可选：改包名并存

# 3) 编译
export JAVA_HOME=/path/to/jdk-17
export ANDROID_HOME=/path/to/android-sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

cd pkg/android/phoenix
./gradlew assembleAarch64Release

# 产物
# pkg/android/phoenix/build/outputs/apk/aarch64/release/phoenix-aarch64-release.apk
```

> ⚠️ 上游文档/旧教程里写的 `assembleNormalUniversalRelease` 在这个版本**不存在**。
> `build.gradle` 的 `variant` 维度下只有 normal / aarch64 / ra32 / playStoreNormal /
> playStorePlus / quest。arm64 手机要的是 **`assembleAarch64Release`**。

`HAVE_LANGEXTRA` 不用管，Android 端无条件定义（见上文 Android.mk:122）。

### patch 0002 是什么（可选）

只改 `pkg/android/phoenix/build.gradle` 一个文件的 aarch64 flavor：

| 项 | 原来 | 改成 |
|---|---|---|
| `applicationIdSuffix` | `.aarch64` | `.aarch64.cn` |
| `abiFilters` | `arm64-v8a, x86_64` | `arm64-v8a` |
| `app_name` | `RetroArch (AArch64)` | `RetroArch 中文版` |

**目的：换包名，和官方版并存**（装成两个独立 App，互不碰数据）。
这是本地的打包选择，不是功能必需 —— 想直接覆盖官方版就别打这个 patch。

---

## 六、仓库内容

```
patch/
  0001-chinese-osk.patch               功能改动：5 文件 +311 行（含新增数据头文件）
  0002-android-package-rename.patch    可选：改包名并存
src/
  chinese_osk_pages.h                  生成好的键盘数据（1183 汉字 / 44 页 + 索引页）
tools/
  生成中文键盘页.py                      语料(.lpl 游戏名) → 统计用字 → 出 C 代码
  gen_chinese_osk_pages.py             重排成严格 44 格 + 打印要粘的枚举/switch 片段
data/
  chinese_osk_pages.corpus-1515.h      修好生成器后重跑的完整字表（1515 字，尚未重编）
  chinese_osk_pages.orig-45elem-BROKEN.h  最早的坏数据（留档，见下）
docs/
  研究报告.md                           问题定位、方案对比（含「接系统输入法」方案）
  改动方案.md                           改动设计、枚举/切页逻辑、构建步骤
```

### 改动清单（0001）

| 文件 | 改了什么 |
|---|---|
| `input/chinese_osk_pages.h` | **新增**。45 个 44 格页数组（1 索引页 + 44 字母页）|
| `input/input_osk.h` | 枚举加 45 个 `OSK_CHINESE_*`。**一页一个枚举值**（不是一字母一个）|
| `input/input_osk_utf8_pages.h` | 末尾 `#include "chinese_osk_pages.h"`（只在 `HAVE_LANGEXTRA` 里被包含）|
| `input/input_driver.c` | 加 `osk_chinese_first_page[26]` 表 + `input_event_osk_append()` 两个分支 |
| `menu/menu_driver.c` | `input_event_osk_iterate()` 的网格 switch 加 45 个 `case`（形状与原有 case 完全一致）|

### 两个设计决定（踩过的坑）

**1. 枚举必须「一页一个值」，不能「一字母一个值」。**

`osk_type` 这个枚举不只是名字 —— **它就是「当前第几页」本身**：

```c
*osk_idx + 1                          /* ⊕ 键翻下一页 */
menu_st->osk_idx < OSK_TYPE_LAST - 1  /* 菜单 R/L 翻页 */
switch (osk_idx) { case ...: memcpy(该页的图) }
```

23 个字母一共占 44 页（b 两页、l 三页、z 三页…），26 个名字装不下 44 页。
按现有架构（上游 `OSK_HIRAGANA_PAGE1`/`PAGE2` 就是这个写法）改成 **一页一个值**，
好处是 `⊕` 键和菜单 R/L 键**自动**能翻完所有中文页，不用额外状态变量。

**2. 「回索引」键不能用 `⌂`。**

`⌂` 是 U+2302，内置字体 `rgui_bitmapfont.c` 覆盖 `0x0–0xFF`、`0x100–0x24F`、
`0x3000–0x30FF`、`0x4E00–0x9FFF`、`0xAC00–0xD7A3` —— U+2302 正好掉在
`0x24F–0x3000` 的空洞里，画不出来。现有键盘页的 `⇦ ⏎ ⇧ ⇩ ⊕` 能用，是因为
rgui 把这 5 个当**矢量图形**画（`rgui_blit_symbol`），绕开了字体。
所以改用 `⇧`（上箭头 = 往上一层，语义也顺）。

---

## 七、自己重新生成字表

`src/chinese_osk_pages.h` 是**生成**出来的，别手工改。两个字表来源：

### 用你**自己**的游戏列表生成（推荐）

`tools/生成中文键盘页.py` 从 RetroArch 播放列表里统计游戏名用字，
用 `pypinyin` 取拼音首字母，按出现频率降序排 —— **只收你库里真实出现的字**，
所以字表小、常用字在前、翻页少。

```bash
pip install pypinyin

# 用法: python3 生成中文键盘页.py [播放列表目录] [输出文件]
python3 tools/生成中文键盘页.py ~/playlists/  /tmp/chinese_osk_pages.h
```

播放列表目录里放 `.lpl`（RetroArch 播放列表是 JSON，脚本读每个 item 的 `label`）。

### 再重排成严格 44 格

```bash
# tools/gen_chinese_osk_pages.py 里是写死的本地路径，按你的路径改一下：
sed -e 's#^SRC = .*#SRC = "/tmp/chinese_osk_pages.h"#' \
    -e 's#^DST = .*#DST = "./chinese_osk_pages.h"#' \
    tools/gen_chinese_osk_pages.py > /tmp/reflow.py
python3 /tmp/reflow.py
```

它会：

1. 把每页重排成 `10 字 + 功能键` × 4 行 = **恰好 44 格**（不足补 `""` 空键）
2. 打印**要粘进 `input_osk.h` 的枚举**和**要粘进 `menu_driver.c` 的 switch 片段**
3. 自检字数（有断言，少一个字就报错）

然后重编 APK 即可。

### 关于字表规模：`data/` 里两份文件的来历

这是本项目一个**已知缺口**，如实记录：

| 文件 | 汉字数 | 说明 |
|---|---|---|
| `data/chinese_osk_pages.orig-45elem-BROKEN.h` | 1183 | 最早的生成器输出。**坏数据**：字母页 45 格、索引页 43 格 |
| `src/chinese_osk_pages.h`（= patch 里那份）| **1183** | 把上面那份重排成 44 格。**这份进了 APK** |
| `data/chinese_osk_pages.corpus-1515.h` | **1515** | 修好生成器后重跑的结果，**尚未重排进源码树、尚未重编** |

坏在哪：最早的生成器**每页只塞 29 个字，却按 40 字算页数**，
于是末尾 **332 个字从来没被写进文件**（语料里实际有 1515 个不同汉字）。
后果不只是「少 332 个字」：

- 每页 45 格 → `memcpy(osk_grid, page, sizeof(page))` 会把 `osk_grid[45]` 的结尾顶掉
- 索引页 43 格 → 第 44 格不会被覆盖，**留着上一页的残留字符**（一个假键，点下去还会翻页）

修好后的生成器（`tools/生成中文键盘页.py`，就是仓库里这份）改成 30 字/页并把页数
按 30 算，带**自检断言**：写入字数 ≠ 语料字数就直接 `exit 2`，不再静默吞字。

**想用完整的 1515 字**：按第七节跑一遍两个脚本 → 把打印出来的枚举/switch 粘回去 → 重编。
（本项目没做，因为改完要重编重测，而真机测试还没打通。）

---

## 八、上游合并的可能性

这套改动**照现有架构写**（`HAVE_LANGEXTRA` + `osk_type` 一页一值 + 网格 switch），
形状和已合并的韩文 PR #14676 一致，理论上可以提 PR。但提之前建议先解决：

1. **真机验证**（现在完全没测过）
2. `menu_driver.c` 里 45 个 `case` 是机械重复 —— 上游可能更想要
   数据驱动的表（指针数组）而不是 45 个 case，值得先问 maintainer
3. 字表版权/来源要干净（本项目是从个人游戏库统计的，见第七节，可复现）

---

## 九、参考

| 链接 | 内容 |
|---|---|
| [PR #14676](https://github.com/libretro/RetroArch/pull/14676) | ✅ 已合并的韩文 OSK PR（**主要参考**）|
| [PR #14654](https://github.com/libretro/RetroArch/pull/14654) | 初版（有完整讨论）|
| `input/input_osk_utf8_pages.h` | 上游键盘页定义 |
| `input/input_osk.h` | 上游 OSK 枚举 |
| `input/input_driver.c` | `input_event_osk_append` 实现 |
| [Android 编译指南](https://docs.libretro.com/development/retroarch/compilation/android/) | 官方文档 |

---

## 十、许可

改动本身是 RetroArch 的衍生作品，**GPLv3**（见 `COPYING`），与上游一致。

## 基线

patch 针对上游 commit `6400e21b86deb37c5062d7e98614267ee05da593`（2026-10-08）生成，
已验证可 `git apply` 干净应用。上游更新后如冲突，照第三节的设计改即可。
