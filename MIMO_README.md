# LecTrans - MiMo 专版

> 全部使用小米 MiMo API，一个 API Key 搞定所有功能

## 🎯 特点

- **统一 API**：ASR + LLM 全部使用 MiMo
- **一个 Key**：只需配置一个 API Key
- **国内优化**：小米服务器，延迟低

## 📦 打包步骤

### 1. 复制项目到 Windows

将 `lectrans_mimo.py` 和 `build_mimo.bat` 复制到 Windows

### 2. 双击运行打包脚本

```
build_mimo.bat
```

### 3. 获取 EXE

```
dist\LecTrans.exe
```

## 🔑 API 获取

1. 访问 https://mimo.xiaomi.com
2. 注册/登录
3. 获取 API Key

## 📱 使用说明

1. 双击 `LecTrans.exe`
2. 点击"设置"
3. 填入 MiMo API Key
4. 点击"测试连接"
5. 点击"开始录音"

## 🤖 MiMo 模型

| 模型 | 用途 | 说明 |
|------|------|------|
| mimo-v2.5-asr | 语音识别 | 韩语转文字 |
| mimo-v2.5-pro | 翻译/总结 | 最强模型 |
| mimo-v2.5 | 翻译/总结 | 标准模型 |

## 📁 文件说明

```
lectrans_mimo.py   # GUI 主程序（MiMo 专用）
build_mimo.bat     # 打包脚本
dist\LecTrans.exe  # 打包后的可执行文件
```

## 💡 优势

相比使用多个 API 的版本：

| 对比项 | 多 API 版本 | MiMo 专版 |
|--------|-------------|-----------|
| API Key 数量 | 2-3 个 | 1 个 |
| 配置复杂度 | 高 | 低 |
| 延迟 | 取决于服务商 | 国内低延迟 |
| 费用 | 多个服务商计费 | 统一计费 |

## ⚠️ 注意

- 需要 Windows 10/11
- 需要 Python 3.9+（打包时）
- 首次运行可能需要几秒启动
