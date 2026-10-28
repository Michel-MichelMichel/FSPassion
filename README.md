# FS Passion

<img width="1004" alt="FS Passion" src="assets/FS_Passion_logo/Final_grand.png" />

**English** · [Français](readme/README.fr.md) · [Deutsch](readme/README.de.md) · [Español](readme/README.es.md) · [Español (Latinoamérica)](readme/README.es-419.md) · [Italiano](readme/README.it.md) · [Português (Brasil)](readme/README.pt-BR.md) · [Português (Portugal)](readme/README.pt-PT.md) · [Nederlands](readme/README.nl.md) · [Polski](readme/README.pl.md) · [Čeština](readme/README.cs.md) · [Dansk](readme/README.da.md) · [Suomi](readme/README.fi.md) · [Magyar](readme/README.hu.md) · [Norsk bokmål](readme/README.nb.md) · [Română](readme/README.ro.md) · [Русский](readme/README.ru.md) · [Svenska](readme/README.sv.md) · [Türkçe](readme/README.tr.md) · [Українська](readme/README.uk.md) · [Tiếng Việt](readme/README.vi.md) · [Bahasa Indonesia](readme/README.id.md) · [日本語](readme/README.ja.md) · [한국어](readme/README.ko.md) · [简体中文](readme/README.zh-Hans.md) · [繁體中文](readme/README.zh-Hant.md)

Mod manager for Farming Simulator (FS2011 to FS25), for Windows 10 and 11.

The drawback of Farming Simulator is that it offers a single mods folder, where we end up with many maps and mods that are sometimes incompatible with each other. Switching from one game setup to another is so tedious that it holds us back from trying new maps.

The heart of FS Passion is to solve this problem with disarming efficiency: create **setups** — collections of mods — in a few clicks, and switch from one to another in a single click. All your mods stay in a single copy in their original folder, the Mods folder.

- **Setups**: a map, its dependencies and the mods you choose; **common mods** shared by every setup.
- **Updates**: updates made by the game (ModHub) are recovered and followed in every setup; a replaced version is set aside, never deleted.
- **Downloads**: new mods are detected and moved to the mods folder of the matching game version.
- **Several drives**: up to three mods folders, located on different drives.
- **Configuration backup**: export and import setups and settings, for a reinstall or another PC.
- **Guided tour**: the light bulb in the header presents the interface in a minute, with animated examples (versions, setups, lists, multiple selection, drag and drop, keyboard shortcuts).
- **Stop using FS Passion**: the game gets its original setting back and setup folders are removed; your mods are never touched.
- Two-color **themes**, and themes inspired by popular ones in dark and light (Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84).
- **Languages**: interface in 14 languages (English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska), chosen from the Windows language and changeable in the Settings; you can add your own translation. **Coming soon: 12 more languages**: Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文 (see [Help improve the translations](#help-improve-the-translations)).
- **Demo**: the application is meant for owners of Farming Simulator games only. If you are curious and want to try its features without owning a game, a demo pack is available in the Settings.

> ⚠️ Work in progress (version: see the [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) page). Make a full backup of your mods folder before trying it. This GitHub page is the only official download location.

## Download

On the [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) page:

- `FSPassion-X.Y.Z-setup.exe`: installer, for the current user without administrator rights, or for all users; it installs Microsoft Edge WebView2 if needed (Windows 10);
- `FSPassion-X.Y.Z-portable.zip`: portable version, no installation; settings and logs stay in the `data` folder next to `FSPassion.exe`;
- `SHA256SUMS.txt`: checksums of both files.

The files are not signed yet: on first launch, Windows may show “Windows protected your PC” (SmartScreen) → “More info” → “Run anyway”. Free signing by the SignPath Foundation is planned after a first release.

## Help improve the translations

Translations are a first version: corrections from native speakers are very welcome, for the current languages and for the coming ones. No coding knowledge is needed, only a text editor (Notepad is fine).

1. In this repository, open the [`lang`](lang/) folder and download the file of your language (for example `de.json`).
2. Put it in the personal languages folder of your FS Passion installation (the **Open the personal languages folder** button in Settings → Display → Language opens it):
   - installed version: `%APPDATA%\FSPassion\lang\`;
   - portable version: `data\lang\` next to `FSPassion.exe`.
3. Rename it, for example `de_corrected.json` (the name must not start with `_`). Do not change the `"code"` line at the top of the file: your file then replaces the built-in language.
4. Correct the texts between quotes, on the right of the `:` signs, and save the file (UTF-8 encoding). Leave the keys on the left, and the words between braces like `{count}`, unchanged.
5. Restart FS Passion and select your language in Settings → Display → Language: it is marked “personal”. Check your corrections in the interface.
6. Send the corrected file in the [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues) tab: create an issue titled for example “Translation: Deutsch”, and attach the file (zip it if GitHub refuses the `.json` extension).

## Report a problem, suggest an idea

[Issues](https://github.com/Michel-MichelMichel/FSPassion/issues) tab. For a problem, attach the text from “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).

## Support the project

FS Passion is and will remain a trustworthy, open-source and free project. To thank its author, a one-time donation takes a few seconds, without creating an account: [Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) or [card donation (Stripe)](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00).

## Internet connection

FS Passion only connects to GitHub, to read the DLC catalog (names and icons, public `FSPassion-data` repository), at most once a day. No personal data is sent. The “Internet connection” setting (Settings → Application) turns it off. It also checks GitHub for a new version of FS Passion at each launch (then once a day): the “FS Passion updates” setting (Settings → Application) turns it off.

## For developers

### Run from source

Requirement: **Python 3.12, 64-bit** ([python.org](https://www.python.org/downloads/windows/)), installed with “Add python.exe to PATH” checked.

Double-click **`lancer_dev.bat`**. On first launch, it prepares the Python environment and installs the dependencies (about a minute). It then opens the application window.

| Option | Effect |
|---|---|
| `--no-window` | browser only |
| `--no-browser` | window only |
| `--window-mode thin` | window with a very thin native frame |
| `--window-mode script` | resizing computed by the interface |
| `--debug` | developer tools in the window |
| `--uninstall` | opens “Stop using FS Passion” directly (started by the uninstaller) |
| `--uninstall-quiet` | silent uninstall: only restores the game's override line |

Automated tests: `lancer_tests.bat` (pytest and ruff).

### Build the application

Double-click **`fabriquer.bat`** (after a first `lancer_dev.bat`). Result in `build\release\`: the installer, the portable version and `SHA256SUMS.txt`. The installer requires [Inno Setup 6](https://jrsoftware.org/isdl.php); without it, only the portable version is built.

On GitHub, the same build runs on every push (**Actions** tab). A `vX.Y.Z` tag also creates a draft release (**Releases**) with the files.

### Where the files are

| Location | Contents |
|---|---|
| `%APPDATA%\FSPassion\settings.json` | settings, paths per game version |
| `%APPDATA%\FSPassion\lang\` | personal languages (template `_modele_en.json`) |
| `%APPDATA%\FSPassion\backups\` | state saved automatically before each import (last 10) |
| `%LOCALAPPDATA%\FSPassion\logs\fspassion.log` | log (anonymized paths), to attach to a report |
| `%LOCALAPPDATA%\FSPassion\dlc\` | DLC catalog and icons downloaded from GitHub |
| `<mods folder>\..\FSPassion\<version>\parties.json` | setups, common mods (+ 5 backups) |
| `<mods folder>\..\FSPassion\<version>\Parties\` | setup folders: links only |
| `<mods folder>\..\FSPassion\<version>\Old versions\` | replaced versions (never deleted) |
| `<mods folder>\..\FSPassion\<version>\Recovered\` | recovered files (older version…) |

## License and credits

- FS Passion: **GPLv3** (`LICENSE` file), author MichelMichel.
- Interface icons: [Lucide](https://lucide.dev), ISC license (`assets\icons\LICENSE.txt`).
- Font: Iosevka Etoile Compact (custom build), SIL OFL 1.1 license (`assets\fonts\OFL-Iosevka.txt`).
- Guided tour title font: [Caveat](https://github.com/googlefonts/caveat), SIL OFL 1.1 license (`assets\fonts\OFL-Caveat.txt`).
- Chinese, Japanese and Korean font: subsets of [Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic) (itself built from Source Han Sans and Iosevka), renamed “FS Passion CJK” as the license requires, SIL OFL 1.1 license (`assets\fonts\OFL-Sarasa.txt`).
- Dependencies: pywebview (BSD), Pillow (MIT-CMU), psutil (BSD), pystray (LGPL-3.0).
- Themes inspired by the palettes of: Catppuccin ([catppuccin.com](https://catppuccin.com), MIT), Nord ([nordtheme.com](https://www.nordtheme.com), MIT), Solarized ([altercation/solarized](https://github.com/altercation/solarized), MIT), Gruvbox ([morhetz/gruvbox](https://github.com/morhetz/gruvbox), MIT), Tokyo Night ([tokyo-night/tokyo-night-vscode-theme](https://github.com/tokyo-night/tokyo-night-vscode-theme), MIT), Synthwave '84 ([robb0wen/synthwave-vscode](https://github.com/robb0wen/synthwave-vscode), MIT), Dracula Neue Pro ([facelessuser/sublime-dracula-scheme](https://github.com/facelessuser/sublime-dracula-scheme), MIT; Dracula Pro is a theme by Zeno Rocha) and Monokai Pro (a theme by Monokai). Only their colors are used; no file from these themes is included.

FS Passion is an independent project, not affiliated with GIANTS Software. Farming Simulator is a trademark of GIANTS Software. The tests use generated fake mods: no GIANTS content is provided.
