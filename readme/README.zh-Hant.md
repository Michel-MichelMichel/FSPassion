# FS Passion

<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />

[English](../README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Español (Latinoamérica)](README.es-419.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Português (Portugal)](README.pt-PT.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Suomi](README.fi.md) · [Magyar](README.hu.md) · [Norsk bokmål](README.nb.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [简体中文](README.zh-Hans.md) · **繁體中文**

Farming Simulator（FS2011 至 FS25）模組管理器，適用於 Windows 10 和 11。

Farming Simulator 的缺點是只有一個模組資料夾，裡面堆積了大量地圖和有時互不相容的模組。在不同遊戲配置之間切換太過麻煩，讓人懶得嘗試新地圖。

FS Passion 的核心就是以驚人的效率解決這個問題：點幾下即可建立**配置**——也就是模組合集——並一鍵在它們之間切換。你的所有模組都只在原始資料夾（Mods 資料夾）中保留一份。

- **配置**：一張地圖、它的相依項目以及你選擇的模組；所有配置共用的**共通模組**。
- **更新**：遊戲執行的更新（ModHub）會被接收並同步到所有配置；被取代的版本會另行保存，絕不刪除。
- **下載**：自動偵測新模組，並移入對應遊戲版本的模組資料夾。
- **多個磁碟**：最多三個位於不同磁碟上的模組資料夾。
- **配置備份**：匯出和匯入配置與設定，方便重新安裝或換電腦。
- **導覽**：標題列的燈泡用一分鐘介紹介面，搭配動畫範例（版本、配置、清單、多選、拖放、鍵盤快速鍵）。
- **停止使用 FS Passion**：遊戲恢復原始設定，配置資料夾會被移除；你的模組絕不會被更動。
- 雙色**主題**，以及受熱門主題啟發的深色與淺色主題（Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84）。
- **語言**：介面支援 14 種語言（English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska），依 Windows 語言自動選擇，可在設定中變更；也可以加入自己的翻譯。 **即將推出：另外 12 種語言**: Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文.
- **示範**：本應用程式僅供 Farming Simulator 遊戲的擁有者使用。如果你感到好奇，想在沒有遊戲的情況下試用功能，可以在設定中使用示範套件。

> ⚠️ 專案仍在開發中（版本：見 [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) 頁面）。試用前請完整備份你的模組資料夾。此 GitHub 頁面是唯一的官方下載位置。

## 螢幕截圖

<table>
<tr>
<td width="50%"><a href="../assets/screenshots/1-all-mods.webp"><img src="../assets/screenshots/1-all-mods.webp" alt="某個遊戲版本的全部模組、資訊卡片和多選" /></a><br />某個遊戲版本的全部模組、資訊卡片和多選</td>
<td width="50%"><a href="../assets/screenshots/2-setups.webp"><img src="../assets/screenshots/2-setups.webp" alt="配置：一鍵切換（淺色主題，法文介面）" /></a><br />配置：一鍵切換（淺色主題，法文介面）</td>
</tr>
<tr>
<td width="50%"><a href="../assets/screenshots/3-preview.webp"><img src="../assets/screenshots/3-preview.webp" alt="滑鼠停留時的大圖預覽（FS22，Synthwave '84 主題）" /></a><br />滑鼠停留時的大圖預覽（FS22，Synthwave '84 主題）</td>
<td width="50%"><a href="../assets/screenshots/4-themes-languages.webp"><img src="../assets/screenshots/4-themes-languages.webp" alt="主題和語言（波蘭文介面）" /></a><br />主題和語言（波蘭文介面）</td>
</tr>
<tr>
<td width="50%"><a href="../assets/screenshots/5-several-drives.webp"><img src="../assets/screenshots/5-several-drives.webp" alt="位於多個磁碟上的模組資料夾" /></a><br />位於多個磁碟上的模組資料夾</td>
<td width="50%"><a href="../assets/screenshots/6-settings.webp"><img src="../assets/screenshots/6-settings.webp" alt="設定：通知區域、網際網路連線、備份（葡萄牙文介面）" /></a><br />設定：通知區域、網際網路連線、備份（葡萄牙文介面）</td>
</tr>
</table>

## 下載

在 [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) 頁面：

- `FSPassion-X.Y.Z-setup.exe`: 安裝程式：可為目前使用者安裝（不需系統管理員權限），也可為所有使用者安裝；必要時會安裝 Microsoft Edge WebView2（Windows 10）；
- `FSPassion-X.Y.Z-portable.zip`: 可攜版：免安裝；設定與記錄保存在 `FSPassion.exe` 旁的 `data` 資料夾中；
- `SHA256SUMS.txt`: 兩個檔案的總和檢查碼。

檔案尚未簽署：首次啟動時，Windows SmartScreen 可能會顯示警告；請開啟其他資訊，然後選擇仍要執行。 SignPath Foundation 提供的免費簽署計畫在首次發布之後進行。

## 協助改進翻譯

翻譯目前還是第一版：非常歡迎母語使用者提供修正，現有語言和即將推出的語言都可以。不需要任何程式設計知識，只要一個文字編輯器（記事本就可以）。

1. 在本儲存庫中開啟 [`lang`](../lang/) 資料夾，下載你的語言檔（`zh-Hant.json`）。如果還沒有，就下載 `en.json`。
2. 把它放到 FS Passion 安裝的個人語言資料夾中（Settings → Display → Language 中的 **Open the personal languages folder** 按鈕可以開啟它）：
   - 安裝版：`%APPDATA%\FSPassion\lang\`；
   - 可攜版：`FSPassion.exe` 旁邊的 `data\lang\`。
3. 重新命名檔案，例如 `zh-Hant_corrected.json`（檔名不能以 `_` 開頭）。不要修改檔案開頭的 `"code"` 行：這樣你的檔案就會取代內建語言。如果從 `en.json` 開始：在 `"code"` 行寫 `"zh-Hant"`，在 `"name"` 行寫 `"繁體中文"`。
4. 修改 `:` 右側引號中的文字，然後儲存檔案（UTF-8 編碼）。左側的鍵以及大括號中的詞（如 `{count}`）保持不變。
5. 重新啟動 FS Passion，在 Settings → Display → Language 中選擇你的語言：它會標示為「personal」。在介面中檢查你的修正。
6. 在 [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues) 分頁提交修正後的檔案：建立一個 issue，標題例如「Translation: 繁體中文」，並附上檔案（如果 GitHub 不接受 `.json` 副檔名，請壓縮為 ZIP）。

## 回報問題、提出建議

請前往 [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues) 分頁。回報問題時，請附上「Copy diagnostics」（Settings → Help and about → Logs and diagnostics）中的文字。

## 支持本專案

FS Passion 是且將始終是值得信賴、開源且免費的專案。向作者單次捐款只需幾秒鐘，無須註冊帳號：[Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) 或 [信用卡捐款（Stripe）](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00)。

## 網路連線

FS Passion 只連線到 GitHub，用於讀取 DLC 目錄（名稱和圖示，公開儲存庫 `FSPassion-data`），每天最多一次。不會傳送任何個人資料。「Internet connection」設定（Settings → Application）可將其關閉。此外，每次啟動時（之後每天一次）會在 GitHub 上檢查 FS Passion 是否有新版本。「FS Passion updates」設定（Settings → Application）可將其關閉。

## 授權

FS Passion：**GPLv3**（`LICENSE` 檔案），作者 MichelMichel。開發者文件與完整致謝（圖示、字型、主題）：[英文 README](../README.md)。

FS Passion 是獨立專案，與 GIANTS Software 無關。Farming Simulator 是 GIANTS Software 的商標。
