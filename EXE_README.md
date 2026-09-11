# LecTrans Windows EXE 使用说明

## 一、获取 EXE

两种方式任选：

1. **本地打包**：在项目根目录双击 `build.bat`，完成后得到 `dist\LecTrans.exe`
2. **GitHub Actions**：在 Actions 页面手动触发 `CI → build` 任务，下载 `LecTrans-windows` 产物

## 二、EXE 能力范围

| 能力 | 支持情况 |
|------|----------|
| Azure Speech 实时识别 | ✅ 内置 |
| MiMo 实时翻译 / 一键总结 | ✅ 内置 |
| 双栏 UI、历史、录音、导出 Markdown | ✅ 内置 |
| 本地 faster-whisper 离线识别 | ❌ 未打包，请使用源码运行 |

## 三、使用流程

1. 双击 `LecTrans.exe`
2. 首次启动自动弹出「设置」：
   - ASR 引擎选择 **azure**，填写 Azure Speech Key / 区域 / 语言
   - 填写 MiMo API Key（翻译与总结必填）
   - 点击「测试连接」确认，再点击「保存」
3. 点击「● 开始录音」，双栏实时显示韩语原文与中文翻译
4. 点击「■ 停止录音」，录音与会话自动保存到历史记录
5. 「生成总结」得到结构化课堂笔记；「导出」保存 Markdown

## 四、数据目录

| 路径 | 内容 |
|------|------|
| `%USERPROFILE%\.lectrans\config.json` | 配置（密钥优先存 Windows 凭据管理器） |
| `%USERPROFILE%\.lectrans\sessions\` | 会话记录（JSON） |
| `%USERPROFILE%\.lectrans\recordings\` | 课堂录音（MP3，缺 ffmpeg 时 WAV） |
| `%USERPROFILE%\.lectrans\lectrans.log` | 运行日志 |

## 五、常见问题

**Q: 未安装 ffmpeg，录音是什么格式？**
A: 自动保留 WAV，历史记录中的路径指向真实文件，可直接播放。

**Q: 翻译偶尔出现「[翻译失败]」？**
A: 网络异常时会自动重试 2 次；仍失败则显示占位文本并写入日志。

**Q: 麦克风打不开？**
A: 检查 Windows 隐私设置中的麦克风权限，或在控制栏切换音频设备。

**Q: 运行时闪退？**
A: 用命令行运行 exe 或查看 `%USERPROFILE%\.lectrans\lectrans.log` 定位原因。

**Q: 想用离线识别怎么办？**
A: 安装 Python 3.11+，`pip install -r requirements.txt`，运行 `python main.py`，
在设置中选择 local 引擎。
