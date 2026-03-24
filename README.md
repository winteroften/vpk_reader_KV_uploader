# 求生之路2 VPK地图解析与 Cloudflare KV 上传工具 (L4D2 VPK Map Reader & CF KV Uploader)

这是一个基于 `PyQt6` 开发的开源图形界面应用程序。它旨在帮助服务器管理员自动解析《求生之路2》(Left 4 Dead 2) 的 `.vpk` 第三方地图文件或地图压缩包（`.zip`, `.rar`, `.7z`），提取其中的战役名称、章节名称和建图代码，并在允许用户自定义修改名称后，将格式化的数据批量上传到 Cloudflare KV 空间。

## ✨ 功能特性

- **多格式支持与拖拽上传**：支持直接拖拽 `.vpk`、`.zip`、`.rar`、`.7z` 文件到软件窗口，自动在后台安全解压。
- **并发极速解析**：内置多线程并发机制，拖入多个文件时自动并行处理，大幅提升解析速度。
- **多语言适配支持**：可在界面直接选择优先解析语言（简体中文、繁体中文、英语、俄语等），自动适配提取 `resource` 翻译文件，精准映射建图代码。
- **可视化表格修改**：解析完成后生成可视化表格，允许用户在上传前预览和自定义修改每一章节的显示名称。
- **一键云端同步**：基于 Cloudflare Bulk API，一键将修改后的数据批量推送到配置好的 Cloudflare KV 空间中。
- **配置自动记忆**：首次填入的 Cloudflare API 凭证会安全地保存在本地 `config.json`，下次打开免重复输入。

## 🚀 运行与构建

### 方式一：直接运行 (推荐)
如果你只需要使用本工具，可以前往 [Releases](#) 页面下载最新打包好的 `L4D2_VPK_Reader_CN.exe` 文件。
双击即可直接运行，**无需安装任何环境**。

### 方式二：从源码运行与构建
本项目使用 Python 3.8+ 编写，如果你希望从源码运行或自行构建，请按以下步骤操作：

1. **克隆项目到本地**：
```bash
git clone https://github.com/YourUsername/cf_vpk_reader.git
cd cf_vpk_reader
```

2. **安装依赖**：
建议使用虚拟环境，然后运行：
```bash
pip install -r requirements.txt
```
*(注意：解析 `.rar` 格式时，可能需要在系统上安装并配置 `unrar` 环境变量)*

3. **直接运行源码**：
```bash
python main.py
```

4. **构建独立的可执行文件 (.exe)**：
安装 `pyinstaller` 后执行：
```bash
pyinstaller --noconsole --onefile --name L4D2_VPK_Reader_CN main.py
```
构建完成后，程序将生成在 `dist` 目录下。

## 📖 使用说明

1. 启动应用后，在上方输入框填入您的 Cloudflare 认证信息：
   - **Account ID**（您的 Cloudflare 账户 ID）
   - **Namespace ID**（您创建的 KV 命名空间 ID）
   - **API Token**（必须具有该 KV 读写权限的 API 令牌）
2. 点击 **保存配置**，信息将自动保存到本地的 `config.json` 文件中。
3. 将包含 L4D2 战役的 `.vpk` 文件或压缩包（支持多选）拖入中间的虚线框区域内。
4. 程序将并发开始解析。完成后，数据将显示在下方的表格中。
5. 双击右侧的**显示名称**列即可进行自定义修改。
6. 确认无误后，点击底部绿色的 **确认修改并上传** 按钮，等待日志提示上传成功即可。

## 📄 许可证 (License)
本项目基于 [MIT License](LICENSE) 开源，你可以自由地修改和分发。
