# EXO DTS-HD5.1创建音轨失败：客户端共享堆上限

2026-11-09，默影视使用EXO播放DTS-HD MA5.1，提示音频输出失败。日志为native格式0x0c000000、48k、mask0x3f，应用Config(48000,252,8,2250000)，AudioFlinger请求4194528字节，而空闲MemoryDealer也总共只有1572864字节，返回ENOMEM/-12。格式已认可，失败发生在播放前的共享内存分配，尚未到功放解码。

本机/vendor/build.prop明确写ro.af.client_heap_size_kbyte=1536，原libaudioflinger支持该原生属性。仅改为8192并正常重启，客户端堆上限变8MiB。参考Android12项目也有2048→8192的同类记录；本机原值、控制区大小和文件位置不同，按本机日志修复。

这里不是RAM耗尽：本机总内存约2GiB，当时可用约931MiB。EXO请求2250000编码字节，按幂二队列及224字节控制区需4MiB+224；即使设4MiB也放不下。8MiB为共享堆容量上限，不是每条音轨强制分配8MiB。

## 与前轮两个缓冲区区分

| 层次 | 当前设置 | 本轮是否改动 |
|---|---|---|
| ALSA HBR物理队列 | 131072字节，本机上限 | 不变 |
| AudioTrack编码共享队列最低值 | 128KiB，尊重应用更大请求 | 不变 |
| AudioFlinger每客户端共享堆上限 | 原1536KiB→8192KiB | 唯一改动 |

没有缩小EXO缓存来规避分配，也没有改应用、HAL、封装库、AudioFlinger二进制或框架。前轮飞牛的小缓冲请求未触发这个客户端堆限制，不能据此断言所有播放器的通路已全面验证。

## 构建、部署与回退

原件/目标SHA见manifests/active-files.json；精确字节差异见patches/build.prop.json。artifacts/rootfs/vendor/build.prop为本机精确匹配的完整配置，不可跨固件全文件覆盖。其他自定义文件应只改目标属性行：

```bash
python3 scripts/patch_client_heap.py --input /path/to/original/vendor/build.prop --output build/vendor.build.prop
```

工具只接受单个1536或已修8192目标属性，保留其他字节，只写主机输出，不访问盒子。现有ro属性不能靠普通setprop在线改写，原子写/vendor/build.prop、恢复0644/root:root/SELinux标签和vendor只读后需正常整机重启。重启期CEC临时停用并按原值恢复，不改用户默认。

回退只把8192改回1536后正常重启，会恢复EXO大音轨分配限制。不要为回退这一行刷旧整机vendor镜像或撤销既有直通修复。

## 验证

精确重建、支持属性读取、正常Android重启后8192读回、原六文件SHA保持及ALSA RUNNING均已核对。用户明确反馈“成功点亮DTS-HD 声音正常”。后续日志没有再出现AudioTrack内存分配失败/-12；起播/供数阶段仍可有UNDERRUN，不能把本次结果写成全日志零警告或所有片源、切轨、长期场景通过。没有截图或自动控制播放。原始日志有私有URL，不公开。
