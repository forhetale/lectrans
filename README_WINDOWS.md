# LecTrans - Windows 版本说明

## ⚠️ 重要说明

由于当前服务器环境是 **Linux**，无法直接生成 Windows `.exe` 文件。

Windows exe 必须在 **Windows 系统** 上打包生成。

---

## 🚀 最快打包方法（3 步）

### 1. 将项目复制到 Windows

将 `/root/lectrans/` 整个文件夹复制到 Windows 电脑

### 2. 双击运行打包脚本

```
build_windows.bat
```

### 3. 获取 exe

打包完成后，`dist\LecTrans.exe` 就是可执行文件

---

## 📦 打包后的功能

✅ **完整图形化界面**（tkinter 原生窗口）

✅ **所有配置项可视化**：
- API Key 配置（Groq、小米 MiMo、DeepSeek、OpenAI）
- 模型选择
- 字体大小调节
- 连接测试

✅ **所有功能可视化**：
- 开始/停止录音
- 实时翻译显示（韩语 + 中文）
- 一键生成总结
- 保存/导出笔记

---

## 📁 项目文件说明

```
lectrans/
├── gui_app.py          # GUI 主程序（完整图形化）
├── build_windows.bat   # Windows 打包脚本
├── BUILD_GUIDE.md      # 详细打包指南
├── requirements.txt    # Python 依赖
├── core/               # 核心模块
├── prompts/            # Prompt 模板
└── docs/               # 设计文档
```

---

## 🔧 手动打包命令

如果打包脚本不工作，手动执行：

```cmd
cd lectrans
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name LecTrans gui_app.py
```

---

## 💡 替代方案

如果不想自己打包，可以：

1. **使用 Python 直接运行**：
   ```cmd
   pip install -r requirements.txt
   python gui_app.py
   ```

2. **使用 Streamlit Web 版**：
   ```cmd
   pip install -r requirements.txt
   streamlit run ui/app.py
   ```

---

## 📞 技术支持

打包问题参考：`BUILD_GUIDE.md`
