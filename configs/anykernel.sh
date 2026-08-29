# AnyKernel3 - TB-J606F / bengal / ReSukiSU
# 由构建流程 cp 进 ak3/ 目录，勿手动改这里

properties() { '
kernel.string=TB-J606F ReSukiSU Kernel
do.devicecheck=0
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=bengal
device.name2=TB-J606F
device.name3=J606F
device.name4=m11_prc_wifi
supported.versions=12
supported.patchlevels=
'; }

block=/dev/block/bootdevice/by-name/boot;
is_slot_device=1;
ramdisk_compression=auto;

. tools/ak3-core.sh;

set_perm_recursive 0 0 755 644 $ramdisk/*;
set_perm_recursive 0 0 750 750 $ramdisk/init* $ramdisk/sbin;

dump_boot;
write_kernel Image.gz-dtb;
patch_dtbo;
end_install;
