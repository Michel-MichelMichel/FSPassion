# FS Passion

<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />

[English](../README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Español (Latinoamérica)](README.es-419.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Português (Portugal)](README.pt-PT.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Suomi](README.fi.md) · [Magyar](README.hu.md) · [Norsk bokmål](README.nb.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **简体中文** · [繁體中文](README.zh-Hant.md)

Farming Simulator（FS2011 至 FS25）模组管理器，适用于 Windows 10 和 11。

Farming Simulator 的不足在于只有一个模组文件夹，里面堆积了大量地图和有时互不兼容的模组。在不同游戏配置之间切换太过麻烦，让人懒得尝试新地图。

FS Passion 的核心就是以惊人的效率解决这个问题：点几下即可创建**配置**——也就是模组合集——并一键在它们之间切换。你的所有模组都只在原始文件夹（Mods 文件夹）中保留一份。

- **配置**：一张地图、它的依赖项以及你选择的模组；所有配置共享的**公共模组**。
- **更新**：游戏执行的更新（ModHub）会被接收并同步到所有配置；被替换的版本会另行保存，绝不删除。
- **下载**：自动发现新模组，并移入对应游戏版本的模组文件夹。
- **多个硬盘**：最多三个位于不同硬盘上的模组文件夹。
- **配置备份**：导出和导入配置与设置，便于重装或换电脑。
- **导览**：标题栏的灯泡用一分钟介绍界面，配有动画示例（版本、配置、列表、多选、拖放、键盘快捷键）。
- **停止使用 FS Passion**：游戏恢复原始设置，配置文件夹被移除；你的模组绝不会被改动。
- 双色**主题**，以及受流行主题启发的深色和浅色主题（Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84）。
- **语言**：界面支持 14 种语言（English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska），根据 Windows 语言自动选择，可在设置中更改；也可以添加自己的翻译。 **即将推出：另外 12 种语言**: Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文.
- **演示**：本应用仅面向 Farming Simulator 游戏的拥有者。如果你感到好奇，想在没有游戏的情况下试用功能，可以在设置中使用演示包。

> ⚠️ 项目仍在开发中（版本：见 [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) 页面）。试用前请完整备份你的模组文件夹。此 GitHub 页面是唯一的官方下载地址。

## 下载

在 [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) 页面：

- `FSPassion-X.Y.Z-setup.exe`: 安装程序：可为当前用户安装（无需管理员权限），也可为所有用户安装；如有需要会安装 Microsoft Edge WebView2（Windows 10）；
- `FSPassion-X.Y.Z-portable.zip`: 便携版：无需安装；设置和日志保存在 `FSPassion.exe` 旁边的 `data` 文件夹中；
- `SHA256SUMS.txt`: 两个文件的校验和。

文件尚未签名：首次启动时，Windows SmartScreen 可能会显示警告；请打开更多信息，然后选择仍要运行。 SignPath Foundation 提供的免费签名计划在首次发布之后进行。

## 帮助改进翻译

欢迎母语者提出修正。分步指南 (English)：[Help improve the translations](../README.md#help-improve-the-translations)。

## 报告问题、提出建议

请前往 [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues) 标签页。报告问题时，请附上“Copy diagnostics”（Settings → Help and about → Logs and diagnostics）中的文本。

## 支持本项目

FS Passion 是并将始终是一个值得信赖、开源且免费的项目。向作者一次性捐赠只需几秒钟，无需注册账户：[Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) 或 [银行卡捐赠（Stripe）](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00)。

## 网络连接

FS Passion 只连接 GitHub，用于读取 DLC 目录（名称和图标，公开仓库 `FSPassion-data`），每天最多一次。不会发送任何个人数据。“Internet connection”设置（Settings → Application）可将其关闭。此外，每次启动时（之后每天一次）会在 GitHub 上检查 FS Passion 是否有新版本。“FS Passion updates”设置（Settings → Application）可将其关闭。

## 许可证

FS Passion：**GPLv3**（`LICENSE` 文件），作者 MichelMichel。开发者文档和完整致谢（图标、字体、主题）：[英文 README](../README.md)。

FS Passion 是独立项目，与 GIANTS Software 无关。Farming Simulator 是 GIANTS Software 的商标。
