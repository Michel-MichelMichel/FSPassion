# FS Passion

<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />

[English](../README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Español (Latinoamérica)](README.es-419.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Português (Portugal)](README.pt-PT.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Suomi](README.fi.md) · [Magyar](README.hu.md) · [Norsk bokmål](README.nb.md) · [Română](README.ro.md) · **Русский** · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [简体中文](README.zh-Hans.md) · [繁體中文](README.zh-Hant.md)

Менеджер модов для Farming Simulator (от FS2011 до FS25), для Windows 10 и 11.

Недостаток Farming Simulator в том, что у него только одна папка модов, в которой скапливается множество карт и модов, иногда несовместимых друг с другом. Переходить с одной игровой конфигурации на другую так хлопотно, что пропадает желание пробовать новые карты.

Суть FS Passion — решить эту проблему с поразительной эффективностью: создавайте за несколько кликов **сборки** — наборы модов — и переключайтесь между ними одним кликом. Все ваши моды остаются в единственном экземпляре в своей исходной папке, папке Mods.

- **Сборки**: карта, её зависимости и выбранные вами моды; **общие моды**, используемые всеми сборками.
- **Обновления**: обновления, сделанные игрой (ModHub), подхватываются и отслеживаются во всех сборках; заменённая версия откладывается в сторону, а не удаляется.
- **Загрузки**: новые моды обнаруживаются и переносятся в папку модов соответствующей версии игры.
- **Несколько дисков**: до трёх папок модов на разных дисках.
- **Резервная копия настроек**: экспорт и импорт сборок и настроек — для переустановки или другого ПК.
- **Экскурсия**: лампочка в заголовке за минуту знакомит с интерфейсом на анимированных примерах (версии, сборки, списки, множественный выбор, перетаскивание, сочетания клавиш).
- **Прекратить использовать FS Passion**: игра возвращает исходную настройку, папки сборок удаляются; ваши моды никогда не затрагиваются.
- Двухцветные **темы** и темы по мотивам популярных, тёмные и светлые (Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84).
- **Языки**: интерфейс на 14 языках (English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska), выбирается по языку Windows и меняется в настройках; можно добавить собственный перевод. **Скоро: ещё 12 языков**: Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文.
- **Демо**: приложение предназначено только для владельцев игр Farming Simulator. Если вам любопытно и вы хотите опробовать его возможности без игры, в Настройках есть демонстрационный пакет.

> ⚠️ Проект в разработке (версия: см. страницу [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases)). Перед использованием сделайте полную резервную копию папки модов. Эта страница GitHub — единственный официальный источник загрузки.

## Загрузка

На странице [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases):

- `FSPassion-X.Y.Z-setup.exe`: установщик — для текущего пользователя без прав администратора или для всех пользователей; при необходимости устанавливает Microsoft Edge WebView2 (Windows 10);
- `FSPassion-X.Y.Z-portable.zip`: портативная версия без установки; настройки и журналы хранятся в папке `data` рядом с `FSPassion.exe`;
- `SHA256SUMS.txt`: контрольные суммы обоих файлов.

Файлы пока не подписаны: при первом запуске Windows SmartScreen может показать предупреждение; откройте дополнительные сведения и выберите запуск приложения всё равно. Бесплатная подпись от SignPath Foundation запланирована после первого выпуска.

## Помогите улучшить переводы

Исправления от носителей языка приветствуются. Пошаговое руководство (English): [Help improve the translations](../README.md#help-improve-the-translations).

## Сообщить о проблеме, предложить идею

Вкладка [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues). При проблеме приложите текст из «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).

## Поддержать проект

FS Passion был и останется надёжным, открытым и бесплатным проектом. Разовое пожертвование автору занимает несколько секунд, без создания аккаунта: [Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) или [пожертвование картой (Stripe)](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00).

## Подключение к Интернету

FS Passion подключается только к GitHub, чтобы прочитать каталог DLC (названия и значки, публичный репозиторий `FSPassion-data`), не чаще раза в день. Никакие личные данные не отправляются. Настройка «Internet connection» (Settings → Application) отключает это.

## Лицензия

FS Passion: **GPLv3** (файл `LICENSE`), автор MichelMichel. Документация для разработчиков и полный список благодарностей (значки, шрифты, темы): [README на английском](../README.md).

FS Passion — независимый проект, не связанный с GIANTS Software. Farming Simulator — товарный знак GIANTS Software.
