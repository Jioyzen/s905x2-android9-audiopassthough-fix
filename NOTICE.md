# 来源、许可与归档范围

本仓库包含本项目适配代码、AOSP兼容封装代码、FFmpeg及厂商原始二进制的局部修补产物，不能统一视为全部由本项目原创或重新许可。

| 内容 | 来源及许可说明 |
|---|---|
| HAL/框架/AudioFlinger产物 | 用户Jiefu设备SN5BBAO / PI.4333的原件与本项目局部补丁；原厂/AOSP部分权利归相应权利人 |
| 本机HAL辅助代码、缓冲补丁、主机构建与重建工具、文档 | 本项目适配工作；新增原创部分采用MIT，见LICENSE |
| src/spdif/ | Jioyzen/s905x2-android12-audio-fix，固定提交de6a1a0a98feb8e9e3181eddc80c87218251a3a4；保留文件中的AOSP Apache2.0等声明 |
| third_party/ffmpeg-armv7、完整源码包 | FFmpeg n8.1.3，commit1041abdc962f4cc4f394aa8de9dc5236c0c3b9e7；配置为LGPL2.1 or later，GPL/NONFREE/VERSION3禁用 |
| third_party/link-stubs/libc++.so | 从参考项目保留的平台链接依赖，仅用于链接；不部署到盒子 |

参考项目：https://github.com/Jioyzen/s905x2-android12-audio-fix 。FFmpeg上游：https://ffmpeg.org/ 。AOSP上游：https://android.googlesource.com/ 。

FFmpeg完整对应源包、生成配置、冻结静态库和本项目适配源码一并提供，可重编静态依赖并重新链接libdroidaudiospdif.so。许可文本见third_party/licenses/。源包与冻结依赖哈希见manifests/dependencies.json；归档使用的精确二进制并不代表本轮从零重编FFmpeg。

原厂二进制不会因为附带MIT文档而被重新许可。仓库只归档音频相关的七文件，不含整机固件、data、原始播放日志、局域网连接信息或影片片段。
