# Jiefu Android 9 音频直通修复

为 Jiefu（Jeff2021 / SN5BBAO、PI.4333）S905X2-BU 盒子修复 HDMI 音频源码直通。本仓库保存**当前实机有效的七个文件、补丁源码、精确二进制差异、构建方法及验证记录**，用于维护与复现。

截至 2026-11-08，用户手测确认 DD、DD+、DTS 正常，TrueHD 与 DTS-HD MA 7.1 在最终缓冲修复后持续播放正常；2026-11-09补充8MiB客户端堆后，默影视EXO DTS-HD5.1用户复测通过，未再复现原连续断音。尚不代表所有片源、暂停/跳转/切轨及最终版本冷启动均已全面验收。

**修改全部位于盒子 Android 系统层，没有修改飞牛 APK、播放器逻辑、缓存设置或数据库。** 没有更换内核、DTB、bootloader，也不包含 HDR、CEC 或 Wi-Fi 修改。

- [下载修复包](https://github.com/Jioyzen/jiefu-android9-audio-fix/releases)
- [修复原理与具体修改](docs/修复原理与修改方法.md)
- [构建与精确重建](docs/构建与重建.md)
- [EXO大音轨共享堆修复](docs/EXO大音轨共享堆修复.md)
- [部署与回退](docs/部署与回退.md)
- [验证范围与失败经验](docs/验证与排障经验.md)
- [来源与许可](NOTICE.md)

## 适用环境

| 项目 | 当前设备 |
|---|---|
| SoC | Amlogic S905X2-BU |
| 产品 / 固件 | SN5BBAO / PI.4333 |
| Android | 9，API 28 |
| Linux | 4.9.113，ARM64 |
| Android 用户空间 / HAL | **ARM32、armeabi-v7a，补丁代码为 Thumb** |
| 输出 | 盒子 HDMI → 功放 → 电视 |

64 位内核不代表音频库也是 64 位。本仓库的地址、结构体布局、C++ ABI 和框架预编译文件绑定这套固件；**以清单中的原件 SHA-256 为准，不能仅凭 S905X2 / Android 9 名称判断可用。**

## 到底改了哪些文件

以下是最终有效的**全部七个音频文件**，镜像目录在 `artifacts/rootfs/`，完整原件/产物 SHA-256 见 [active-files.json](manifests/active-files.json)。

| 盒子上的路径 | 修改方式 | 解决的问题 |
|---|---|---|
| `/vendor/lib/hw/audio.primary.amlogic.so` | 原厂 HAL 精确二进制补丁，加入本机 ARM32 C/汇编辅助代码 | HD 能力查询、TrueHD/DTS-HD 格式保留、HBR 时钟与缓冲、时间戳/延迟、pause/resume、DTS-HD 被标成 DTS 的识别 |
| `/vendor/lib/libdroidaudiospdif.so` | 基于 AOSP 兼容接口和参考项目源码重新链接 | TrueHD 的 IEC 61937/MAT 封装、完整 DTS-HD 封装、普通 AC3/EAC3/DTS 边界处理及降日志 |
| `/vendor/etc/audio_policy_configuration.xml` | 添加普通 DIRECT 动态压缩输出及 HDMI 路由 | 播放器不使用 HW_AV_SYNC 时也能申请压缩音轨 |
| `/system/framework/arm/boot-framework.oat` | 原预编译文件中四处 switch 表，各改一个字节 | 本机 Android 9 Java API 接受 TrueHD encoding 14 |
| `/system/framework/boot-framework.vdex` | 对应四处表同步，各改一个字节 | 保持 DEX / AOT 行为一致；两文件实际总改动 **8 字节** |
| `/vendor/build.prop` | 原生属性 `ro.af.client_heap_size_kbyte=1536→8192` | 解决EXO DTS-HD大音轨申请4MiB共享队列时客户端堆仅1.5MiB导致的ENOMEM |
| `/system/lib/libaudioflinger.so` | 原 `createTrack_l` 入口定向补丁，新增 96 字节可执行代码 | 为普通 DTS/DTS-HD/TrueHD streaming 音轨设置 **128 KiB 编码字节**共享队列下限，解决持续供数不足 |

原 `framework.jar`、其他 boot 预编译文件、`services.jar`、`libandroid_runtime.so` 都不是本次最终音频载荷。`/system/framework/arm/boot-framework.vdex` 原有软链接应保留。

## 修复后的数据路径

```text
播放器输出原始压缩音频
  → Android AudioTrack / AudioFormat（允许 TrueHD）
  → AudioPolicy 普通 DIRECT → AudioFlinger（HD 编码共享队列下限 128 KiB）
  → 本机 Amlogic HAL（EDID、格式、时钟、时间戳与硬件队列修正）
  → IEC 61937 封装（TrueHD 使用 MAT；DTS-HD 保留 EXSS）
  → ALSA / AUGE / HDMI
  → 功放解码
```

直通路径不把音轨解码成 PCM 后重编码。HBR 使用 PCM 形态的 ALSA 载波并不代表音频已被下混，真实压缩内容仍在载波中。

## 目前能力与边界

| 格式 | 当前结论 |
|---|---|
| AC3 / DD、EAC3 / DD+ | 用户确认正常 |
| DTS | 用户确认功放点亮 DTS、有声 |
| TrueHD | 原先不可选/无声/画速快；现用户确认持续播放正常、未再断续 |
| DTS-HD MA 5.1（默影视EXO） | 客户端堆修复后用户确认功放点亮DTS-HD、有声正常 |
| DTS-HD MA 7.1 | 功放点亮 DTS-HD MA，最终用户复测正常 |
| DTS-ES 6.1 | 代码、掩码与实际 AudioTrack 创建通过；真实 DTS-ES 片源听感未验证 |
| DD+ Atmos / TrueHD Atmos | 当前封装代码保留完整编码帧，元数据应随码流保留；功放不支持 Atmos，**没有接收端实测证明** |

Atmos 不需要把对象信息单独注入 HDMI。前提是播放器交出完整原始码流；普通 DD+/TrueHD 路径保留扩展不等于所有应用单独声明 `E_AC3_JOC` 时的能力协商都已验证。7.1 声道掩码不等于 Atmos 对象数量限制。

## 仓库内容

```text
artifacts/rootfs/     七个实机有效产物（按设备路径组织）
artifacts/SHA256SUMS  产物校验和
src/hal/             本机 HAL C 与 Thumb 源码
src/spdif/           AOSP 兼容封装接口、扫描器、FFmpeg HD 适配器
src/flinger/         AudioFlinger 共享缓冲补丁
patches/             六个原文件到最终文件的精确差异（含原/目标 SHA）
scripts/             主机构建、精确重建、校验和发布打包；不自动连接盒子
probes/              音轨容量及封装探针源码
verification/        脱敏后的 ABI、机器码、封装和音轨容量验证结果
third_party/         冻结 FFmpeg 静态库、完整对应源码及许可
manifests/           有效文件及依赖来源/哈希
```

迁移后的主机构建已重新执行，HAL、封装库、框架表补丁、AudioFlinger均与实机产物SHA完全一致，policy也已精确重建。HAL/DTS检测器机器码测试与AudioFlinger 240种ABI/缓冲用例通过，见[复建结果](verification/repository-rebuild.json)。

一键检查归档完整性（Python 3.12+，不访问盒子）：

```bash
python3 scripts/verify_artifacts.py
(cd artifacts && sha256sum -c SHA256SUMS)
```

FFmpeg 对应完整源码和冻结依赖随仓库提供。HAL 基于原厂二进制定向修补，**不是开源重写整个厂商 HAL**。参考 Android 12 项目的经验和封装源码，但没有照搬 Android 12 的 HAL 地址或框架。
