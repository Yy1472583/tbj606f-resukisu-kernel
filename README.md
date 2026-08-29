# TB-J606F (联想小新 Pad / Lenovo Tab) ReSukiSU 内核云编译工程

机型：Lenovo TB-J606F，Android 12，内核 4.19.157，非 GKI（bengal / SM6115）。  
目标：在 GitHub Actions 上把 ReSukiSU 集我接下来该怎么做成进社区内核源码并编译出可刷的 AnyKernel3 包。  
**全程不碰本地环境，不需要 Linux，点一下 Actions 就出包。**

---

## 0. 前置（你手里应该已经有了）

- [x] Bootloader 已解锁（你早就付过清数据的代价了）
- [x] 桌面有**完整原厂包**（里面能解出 `boot.img` / `boot_a.img` / `boot_b.img`）——这是你的救命备份 + ramdisk 来源
- [x] 桌面已下载 `ReSukiSU_v4.2.0-rc1_35061_arm64.apk`（管理器，内核刷成功后再装）
- [ ] 一个 GitHub 账号

---

## 1. 把这个工程推到你的 GitHub

```bat
:: 在 GitHub 网页新建一个空仓库，比如 tbj606f-resukisu-kernel
cd /d "C:\Users\28171\Desktop\TB-J606F_ReSukiSU编译工程"
git init
git add -A
git commit -m "TB-J606F ReSukiSU build"
git branch -M main
git remote add origin https://github.com/<你的用户名>/tbj606f-resukisu-kernel.git
git push -u origin main
```

## 2. 跑编译

1. 进仓库 → **Actions** → 选 `Build TB-J606F ReSukiSU Kernel` → **Run workflow**
2. 参数默认即可（内核分支 `lineage-19.1`，ReSukiSU `main`）
3. 等 **20~40 分钟**（GitHub 免费 runner 双核）
4. 完成后在 Actions 页面 **Artifacts** 里下载 `AnyKernel3-ReSukiSU-tbj606f.zip`
   - 里面核心就是 `Image.gz-dtb`（新内核）

---

## 3. 安全验证 & 刷入（关键，照顺序来）

> AK3 zip **不能**直接 `fastboot boot`（它没 ramdisk）。正确做法：拿原厂 boot 的 ramdisk 跟新内核拼一个完整 `boot.img` 来试。

### 3.1 备好原厂 boot（ramdisk 来源 + 兜底）

从你桌面的原厂包里解出 `boot_a.img`、`boot_b.img`，放到一个工作目录，例如 `C:\j606\`。

### 3.2 拼测试 boot.img（Windows 下用 magiskboot）

1. 下载 `magiskboot.exe`（来自 Magisk 发布页，单文件）放到 `C:\j606\`
2. 解包原厂 boot_a，换成新内核：

```bat
cd /d C:\j606
magiskboot.exe unpack boot_a.img
:: 生成的 kernel / ramdisk.cpio 等在当前目录
copy /Y "下载的\Image.gz-dtb" kernel
magiskboot.exe repack boot_a.img
:: 产出 new-boot.img
```

1. 临时启动验证（**不写盘**，起不来直接长按电源重启回原系统）：

```bat
fastboot boot new-boot.img
```

能进系统、能装 ReSukiSU APK 并正常授权 → 说明内核 OK。

### 3.3 正式刷入（用 B 槽，A 槽留给原厂兜底）

```bat
fastboot flash boot_b new-boot.img
fastboot set_active b
fastboot reboot
```

- 起不来？`fastboot set_active a` 切回原厂槽，秒回原系统，啥都没丢。
- 起来了？装桌面那个 `ReSukiSU_v4.2.0-rc1_35061_arm64.apk`，打开授权，完事。

### 3.4 兜底恢复

无论啥时候翻车：

```bat
fastboot flash boot_a C:\j606\boot_a.img
fastboot flash boot_b C:\j606\boot_b.img
fastboot set_active a
fastboot reboot
```

---

## 4. 已知风险（先有心理准备）

- 用的是 **LineageOS 19.1 内核源码**跑在 **ZUI Android 12** 上，驱动可能不全（相机/指纹/某些传感器）。先 `fastboot boot` 充分验证再 flash。
- `lineage-19.1` 分支若编译报错（符号/驱动差异），可在 Run workflow 时把 `kernel_branch` 换成 `lineage-18.1` 重试。
- 若 AK3 流程里 `TBJ606_defconfig` 找不到，多半是分支名变了，去看 `arch/arm64/configs/vendor/` 里实际的 defconfig 名改回来。

## 5. 备用参考

- `configs/tbj606f_defconfig` = 你设备**正在运行**的 ZUI 内核完整配置（从 `/proc/config.gz` 提取）。仅作对照/兜底，正常编译用不到它（编译用的是源码自带 `TBJ606_defconfig`）。
- 万一 lineage 源码驱动实在对不上，可改用这份提取配置作底重编——但那是下下策，先试源码自带 defconfig。
