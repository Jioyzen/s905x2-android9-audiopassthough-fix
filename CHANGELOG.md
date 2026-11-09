# 更新记录

## v1.0.1 — 2026-11-09

- 仅新增/vendor/build.prop中客户端堆1536→8192KiB修正，解决默影视EXO DTS-HD5.1创建AudioTrack返回ENOMEM/-12。原六项产物不变。
- 用户确认功放点亮DTS-HD、声音正常；附原生配置工具、精确差异和故障分析。

## v1.0.0 — 2026-11-08

- 首次归档Jiefu Android9实机最终音频直通修复，共六个文件。
- 修复TrueHD Java API、普通DIRECT路由、HD封装、HBR时钟与延迟、软件pause回退、DTS-HD别名和物理队列。
- 新增AudioFlinger 128KiB编码共享队列下限；用户确认TrueHD、DTS-HD MA7.1持续播放正常。
- 保存C/Thumb源码、精确二进制差异、便携主机构建/校验工具、完整FFmpeg对应源码与验证摘要。
- Atmos和真实DTS-ES6.1未作为实测通过；不包含失败JNI试验、内核更换或播放器修改。
