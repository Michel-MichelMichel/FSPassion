"""Traductions du README : readme/README.<langue>.md.

    python tools/readme_translations.py

Le README principal (README.md) est en anglais ; le français (readme/README.fr.md)
est rédigé à la main. Ce script écrit les autres langues à partir d'un même
modèle : modifier un texte ici, puis relancer le script, garde toutes les
traductions identiques dans leur structure. Les noms des boutons et menus
de l'application sont repris du fichier lang/<langue>.json quand l'interface
existe dans cette langue, sinon ils restent en anglais. Le point « Langues »
compte et nomme les fichiers de lang/ : il suit les traductions ajoutées.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "readme"

REPO = "https://github.com/Michel-MichelMichel/FSPassion"
RELEASES = f"{REPO}/releases"
ISSUES = f"{REPO}/issues"
BMAC = "https://buymeacoffee.com/michel.michelmichel"
STRIPE = "https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00"
THEMES = "Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84"

# Noms des langues, dans l'ordre de la ligne de liens du README anglais.
NAMES = {
    "fr": "Français", "de": "Deutsch", "es": "Español", "es-419": "Español (Latinoamérica)",
    "it": "Italiano", "pt-BR": "Português (Brasil)", "pt-PT": "Português (Portugal)",
    "nl": "Nederlands", "pl": "Polski", "cs": "Čeština", "da": "Dansk", "fi": "Suomi",
    "hu": "Magyar", "nb": "Norsk bokmål", "ro": "Română", "ru": "Русский", "sv": "Svenska",
    "tr": "Türkçe", "uk": "Українська", "vi": "Tiếng Việt", "id": "Bahasa Indonesia",
    "ja": "日本語", "ko": "한국어", "zh-Hans": "简体中文", "zh-Hant": "繁體中文",
}

# Clés : sub, p1, p2, f (9 points), warn, h_dl, dl_intro, dl_setup, dl_port,
# dl_sums, dl_sign, sign (point SignPath), soon (titre « à venir » du point
# Langues), h_help (titre de la section d'aide, texte dans HELP), h_rep, rep, h_sup, sup, h_net, net,
# h_lic, lic, disc. Liens : {releases}, {issues}, {bmac}, {stripe} ; {themes} :
# noms des thèmes ; {nsoon}, {soonlist} : langues à venir.
T: dict[str, dict] = {}

# Langues de readme/ sans interface dans lang/ (point « à venir »), dans l'ordre
# du README anglais. main() vérifie qu'elles correspondent à lang/.
SOON = ["hu", "ro", "ru", "uk", "tr", "vi", "id", "es-419", "ja", "ko", "zh-Hans", "zh-Hant"]

T["de"] = dict(
    sub="Mod-Manager für Farming Simulator (FS2011 bis FS25), für Windows 10 und 11.",
    p1="Der Nachteil von Farming Simulator: Es gibt nur einen einzigen Mod-Ordner, in dem sich viele Maps und Mods ansammeln, die manchmal nicht miteinander kompatibel sind. Der Wechsel von einer Spielkonfiguration zur anderen ist so mühsam, dass man neue Maps lieber gar nicht erst ausprobiert.",
    p2="Das Herz von FS Passion löst dieses Problem verblüffend einfach: Erstelle mit wenigen Klicks **Setups** – Sammlungen von Mods – und wechsle mit einem einzigen Klick zwischen ihnen. Alle deine Mods bleiben nur einmal in ihrem ursprünglichen Ordner, dem Mods-Ordner.",
    f=[
        "**Setups**: eine Map, ihre Abhängigkeiten und die Mods deiner Wahl; **gemeinsame Mods**, die alle Setups teilen.",
        "**Updates**: Updates, die das Spiel durchführt (ModHub), werden übernommen und in allen Setups nachgeführt; eine ersetzte Version wird beiseitegelegt, nie gelöscht.",
        "**Downloads**: Neue Mods werden erkannt und in den Mod-Ordner der passenden Spielversion verschoben.",
        "**Mehrere Laufwerke**: bis zu drei Mod-Ordner auf verschiedenen Laufwerken.",
        "**Sicherung der Konfiguration**: Export und Import von Setups und Einstellungen, für eine Neuinstallation oder einen anderen PC.",
        "**Geführte Tour**: Die Glühbirne in der Kopfzeile stellt die Oberfläche in einer Minute vor, mit animierten Beispielen (Versionen, Setups, Listen, Mehrfachauswahl, Drag & Drop, Tastenkürzel).",
        "**FS Passion nicht mehr verwenden**: Das Spiel erhält seine ursprüngliche Einstellung zurück, die Setup-Ordner werden entfernt; deine Mods werden nie angerührt.",
        "Zweifarbige **Designs** und Designs nach beliebten Vorbildern, hell und dunkel ({themes}).",
        "**Demo**: Die Anwendung richtet sich ausschließlich an Besitzer der Farming-Simulator-Spiele. Wer neugierig ist und die Funktionen ohne Spiel ausprobieren möchte, findet in den Einstellungen ein Demo-Paket.",
    ],
    warn="⚠️ Projekt in Entwicklung (Version: siehe Seite [Releases]({releases})). Lege vor dem Ausprobieren eine vollständige Sicherung deines Mod-Ordners an. Diese GitHub-Seite ist die einzige offizielle Download-Quelle.",
    h_dl="Download",
    dl_intro="Auf der Seite [Releases]({releases}):",
    dl_setup="Installationsprogramm, für den aktuellen Benutzer ohne Administratorrechte oder für alle Benutzer; installiert bei Bedarf Microsoft Edge WebView2 (Windows 10);",
    dl_port="portable Version, ohne Installation; Einstellungen und Protokolle bleiben im Ordner `data` neben `FSPassion.exe`;",
    dl_sums="Prüfsummen der beiden Dateien.",
    dl_sign="Die Dateien sind noch nicht signiert: Beim ersten Start kann Windows SmartScreen eine Warnung anzeigen; öffne die weiteren Informationen und wähle, die App trotzdem auszuführen.",
    sign="Eine kostenlose Signatur durch die SignPath Foundation ist nach einer ersten Veröffentlichung geplant.",
    soon="Demnächst: {nsoon} weitere Sprachen",
    h_help="Übersetzungen verbessern",
    h_rep="Problem melden, Idee vorschlagen",
    rep="Reiter [Issues]({issues}). Füge bei einem Problem den Text von „Copy diagnostics“ hinzu (Settings → Help and about → Logs and diagnostics).",
    h_sup="Das Projekt unterstützen",
    sup="FS Passion ist und bleibt ein vertrauenswürdiges, quelloffenes und kostenloses Projekt. Eine einmalige Spende an den Autor dauert nur wenige Sekunden, ohne Konto: [Buy Me a Coffee]({bmac}) oder [Spende per Karte (Stripe)]({stripe}).",
    h_net="Internetverbindung",
    net="FS Passion verbindet sich nur mit GitHub, um den DLC-Katalog zu lesen (Namen und Symbole, öffentliches Repository `FSPassion-data`), höchstens einmal pro Tag. Es werden keine persönlichen Daten gesendet. Die Einstellung „Internet connection“ (Settings → Application) schaltet das ab. Außerdem sucht es bei jedem Start (danach einmal täglich) auf GitHub nach einer neuen Version von FS Passion: Die Einstellung „FS Passion updates“ (Settings → Application) schaltet das ab.",
    h_lic="Lizenz",
    lic="FS Passion: **GPLv3** (Datei `LICENSE`), Autor MichelMichel. Entwicklerdokumentation und alle Nachweise (Symbole, Schriften, Designs): [englisches README](../README.md).",
    disc="FS Passion ist ein unabhängiges Projekt, nicht mit GIANTS Software verbunden. Farming Simulator ist eine Marke von GIANTS Software.",
)

_ES_COMMON = dict(
    sub="Gestor de mods para Farming Simulator (FS2011 a FS25), para Windows 10 y 11.",
    h_dl="Descarga",
    dl_intro="En la página [Releases]({releases}):",
    dl_sums="sumas de verificación de ambos archivos.",
    h_rep="Informar de un problema, proponer una idea",
    h_net="Conexión a Internet",
    h_lic="Licencia",
    disc="FS Passion es un proyecto independiente, sin relación con GIANTS Software. Farming Simulator es una marca de GIANTS Software.",
)

T["es"] = dict(
    _ES_COMMON,
    p1="El inconveniente de Farming Simulator es que solo ofrece una carpeta de mods, en la que acabamos con muchos mapas y mods a veces incompatibles entre sí. Pasar de una configuración de partida a otra es tan engorroso que quita las ganas de probar mapas nuevos.",
    p2="El corazón de FS Passion resuelve este problema con una eficacia sorprendente: crea en pocos clics **partidas**, que son colecciones de mods, y pasa de una a otra con un solo clic. Todos tus mods se quedan en un único ejemplar en su carpeta de origen, la carpeta Mods.",
    f=[
        "**Partidas**: un mapa, sus dependencias y los mods que elijas; **mods comunes** compartidos por todas las partidas.",
        "**Actualizaciones**: las que hace el juego (ModHub) se recuperan y se siguen en todas las partidas; una versión sustituida se aparta, nunca se borra.",
        "**Descargas**: los mods nuevos se detectan y se colocan en la carpeta de mods de la versión del juego correspondiente.",
        "**Varios discos**: hasta tres carpetas de mods en discos distintos.",
        "**Copia de la configuración**: exportación e importación de partidas y ajustes, para una reinstalación u otro PC.",
        "**Visita guiada**: la bombilla de la cabecera presenta la interfaz en un minuto, con ejemplos animados (versiones, partidas, listas, selección múltiple, arrastrar y soltar, atajos de teclado).",
        "**Dejar de usar FS Passion**: el juego recupera su ajuste original y se eliminan las carpetas de partidas; tus mods nunca se tocan.",
        "**Temas** bicolores y temas inspirados en temas populares, oscuros y claros ({themes}).",
        "**Demo**: la aplicación está pensada solo para quienes tienen los juegos Farming Simulator. Si sientes curiosidad y quieres probar sus funciones sin tener el juego, hay un paquete de demostración en los Ajustes.",
    ],
    warn="⚠️ Proyecto en desarrollo (versión: ver la página [Releases]({releases})). Haz una copia de seguridad completa de tu carpeta de mods antes de probarlo. Esta página de GitHub es el único enlace oficial de descarga.",
    dl_setup="instalador, para el usuario actual sin permisos de administrador o para todos los usuarios; instala Microsoft Edge WebView2 si hace falta (Windows 10);",
    dl_port="versión portátil, sin instalación; ajustes y registros en la carpeta `data`, junto a `FSPassion.exe`;",
    dl_sign="Los archivos aún no están firmados: en el primer inicio, Windows SmartScreen puede mostrar un aviso; abre la información adicional y elige ejecutar la aplicación de todos modos.",
    sign="La firma gratuita de SignPath Foundation está prevista después de una primera versión.",
    soon="Próximamente: {nsoon} idiomas más",
    h_help="Mejorar las traducciones",
    rep="Pestaña [Issues]({issues}). Para un problema, adjunta el texto de «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Apoyar el proyecto",
    sup="FS Passion es y seguirá siendo un proyecto de confianza, de código abierto y gratuito. Para dar las gracias a su autor, una donación puntual se hace en segundos, sin crear cuenta: [Buy Me a Coffee]({bmac}) o [donación con tarjeta (Stripe)]({stripe}).",
    net="FS Passion solo se conecta a GitHub para leer el catálogo de DLC (nombres e iconos, repositorio público `FSPassion-data`), como mucho una vez al día. No se envía ningún dato personal. El ajuste «Internet connection» (Settings → Application) lo desactiva. También busca en GitHub una nueva versión de FS Passion en cada inicio (luego una vez al día): el ajuste «FS Passion updates» (Settings → Application) lo desactiva.",
    lic="FS Passion: **GPLv3** (archivo `LICENSE`), autor MichelMichel. Documentación para desarrolladores y créditos completos (iconos, fuentes, temas): [README en inglés](../README.md).",
)

T["es-419"] = dict(
    _ES_COMMON,
    p1="La desventaja de Farming Simulator es que solo ofrece una carpeta de mods, donde terminamos con muchos mapas y mods que a veces no son compatibles entre sí. Cambiar de una configuración de partida a otra es tan complicado que quita las ganas de probar mapas nuevos.",
    p2="El corazón de FS Passion resuelve este problema con una eficacia sorprendente: crea en pocos clics **partidas**, que son colecciones de mods, y cambia de una a otra con un solo clic. Todos tus mods se quedan en una sola copia en su carpeta original, la carpeta Mods.",
    f=[
        "**Partidas**: un mapa, sus dependencias y los mods que elijas; **mods comunes** compartidos por todas las partidas.",
        "**Actualizaciones**: las que hace el juego (ModHub) se recuperan y se siguen en todas las partidas; una versión reemplazada se guarda aparte, nunca se borra.",
        "**Descargas**: los mods nuevos se detectan y se mueven a la carpeta de mods de la versión del juego correspondiente.",
        "**Varios discos**: hasta tres carpetas de mods en discos diferentes.",
        "**Respaldo de la configuración**: exportación e importación de partidas y ajustes, para una reinstalación u otra PC.",
        "**Recorrido guiado**: el foco del encabezado presenta la interfaz en un minuto, con ejemplos animados (versiones, partidas, listas, selección múltiple, arrastrar y soltar, atajos de teclado).",
        "**Dejar de usar FS Passion**: el juego recupera su configuración original y se eliminan las carpetas de partidas; tus mods nunca se tocan.",
        "**Temas** bicolores y temas inspirados en temas populares, oscuros y claros ({themes}).",
        "**Demo**: la aplicación está pensada solo para quienes tienen los juegos Farming Simulator. Si te da curiosidad y quieres probar sus funciones sin tener el juego, hay un paquete de demostración en la Configuración.",
    ],
    warn="⚠️ Proyecto en desarrollo (versión: consulta la página [Releases]({releases})). Haz un respaldo completo de tu carpeta de mods antes de probarlo. Esta página de GitHub es el único enlace oficial de descarga.",
    dl_setup="instalador, para el usuario actual sin permisos de administrador o para todos los usuarios; instala Microsoft Edge WebView2 si hace falta (Windows 10);",
    dl_port="versión portable, sin instalación; la configuración y los registros quedan en la carpeta `data`, junto a `FSPassion.exe`;",
    dl_sign="Los archivos todavía no están firmados: al abrir la app por primera vez, Windows SmartScreen puede mostrar una advertencia; abre la información adicional y elige ejecutarla de todas formas.",
    sign="La firma gratuita de SignPath Foundation está prevista después de una primera versión.",
    soon="Próximamente: {nsoon} idiomas más",
    h_help="Mejorar las traducciones",
    rep="Pestaña [Issues]({issues}). Si es un problema, adjunta el texto de “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Apoyar el proyecto",
    sup="FS Passion es y seguirá siendo un proyecto confiable, de código abierto y gratuito. Para agradecerle a su autor, una donación única toma unos segundos, sin crear cuenta: [Buy Me a Coffee]({bmac}) o [donación con tarjeta (Stripe)]({stripe}).",
    net="FS Passion solo se conecta a GitHub para leer el catálogo de DLC (nombres e íconos, repositorio público `FSPassion-data`), como máximo una vez al día. No se envía ningún dato personal. La opción “Internet connection” (Settings → Application) lo desactiva. También busca en GitHub una nueva versión de FS Passion en cada inicio (luego una vez al día): la opción “FS Passion updates” (Settings → Application) lo desactiva.",
    lic="FS Passion: **GPLv3** (archivo `LICENSE`), autor MichelMichel. Documentación para desarrolladores y créditos completos (íconos, fuentes, temas): [README en inglés](../README.md).",
)

T["it"] = dict(
    sub="Gestore di mod per Farming Simulator (da FS2011 a FS25), per Windows 10 e 11.",
    p1="Il limite di Farming Simulator è che offre una sola cartella delle mod, in cui ci ritroviamo con tante mappe e mod a volte incompatibili tra loro. Passare da una configurazione di partita all'altra è così scomodo che toglie la voglia di provare nuove mappe.",
    p2="Il cuore di FS Passion risolve questo problema con un'efficacia sorprendente: crea in pochi clic delle **partite**, cioè raccolte di mod, e passa dall'una all'altra con un solo clic. Tutte le tue mod restano in un'unica copia nella loro cartella d'origine, la cartella Mods.",
    f=[
        "**Partite**: una mappa, le sue dipendenze e le mod che scegli; **mod comuni** condivise da tutte le partite.",
        "**Aggiornamenti**: quelli fatti dal gioco (ModHub) vengono recuperati e seguiti in tutte le partite; una versione sostituita viene messa da parte, mai cancellata.",
        "**Download**: le nuove mod vengono individuate e spostate nella cartella delle mod della versione del gioco corrispondente.",
        "**Più dischi**: fino a tre cartelle delle mod su dischi diversi.",
        "**Backup della configurazione**: esportazione e importazione di partite e impostazioni, per una reinstallazione o un altro PC.",
        "**Visita guidata**: la lampadina nell'intestazione presenta l'interfaccia in un minuto, con esempi animati (versioni, partite, liste, selezione multipla, trascinamento, scorciatoie da tastiera).",
        "**Non usare più FS Passion**: il gioco ritrova la sua impostazione originale e le cartelle delle partite vengono rimosse; le tue mod non vengono mai toccate.",
        "**Temi** bicolori e temi ispirati a temi popolari, scuri e chiari ({themes}).",
        "**Demo**: l'applicazione è pensata solo per chi possiede i giochi Farming Simulator. Se sei curioso e vuoi provarne le funzioni senza avere il gioco, nelle Impostazioni trovi un pacchetto dimostrativo.",
    ],
    warn="⚠️ Progetto in sviluppo (versione: vedi la pagina [Releases]({releases})). Fai un backup completo della tua cartella delle mod prima di provarlo. Questa pagina GitHub è l'unico link ufficiale per il download.",
    h_dl="Download",
    dl_intro="Nella pagina [Releases]({releases}):",
    dl_setup="programma di installazione, per l'utente corrente senza diritti di amministratore o per tutti gli utenti; installa Microsoft Edge WebView2 se necessario (Windows 10);",
    dl_port="versione portatile, senza installazione; impostazioni e log restano nella cartella `data` accanto a `FSPassion.exe`;",
    dl_sums="impronte di controllo dei due file.",
    dl_sign="I file non sono ancora firmati: al primo avvio, Windows SmartScreen può mostrare un avviso; apri le informazioni aggiuntive e scegli di eseguire comunque l'app.",
    sign="La firma gratuita di SignPath Foundation è prevista dopo una prima versione.",
    soon="In arrivo: altre {nsoon} lingue",
    h_help="Migliorare le traduzioni",
    h_rep="Segnalare un problema, proporre un'idea",
    rep="Scheda [Issues]({issues}). Per un problema, allega il testo di «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Sostenere il progetto",
    sup="FS Passion è e resterà un progetto affidabile, open source e gratuito. Per ringraziare il suo autore, una donazione una tantum richiede pochi secondi, senza creare un account: [Buy Me a Coffee]({bmac}) o [donazione con carta (Stripe)]({stripe}).",
    h_net="Connessione a Internet",
    net="FS Passion si collega solo a GitHub, per leggere il catalogo dei DLC (nomi e icone, repository pubblico `FSPassion-data`), al massimo una volta al giorno. Nessun dato personale viene inviato. L'impostazione «Internet connection» (Settings → Application) la disattiva. Cerca inoltre su GitHub una nuova versione di FS Passion a ogni avvio (poi una volta al giorno): l'impostazione «FS Passion updates» (Settings → Application) la disattiva.",
    h_lic="Licenza",
    lic="FS Passion: **GPLv3** (file `LICENSE`), autore MichelMichel. Documentazione per sviluppatori e crediti completi (icone, caratteri, temi): [README in inglese](../README.md).",
    disc="FS Passion è un progetto indipendente, non affiliato a GIANTS Software. Farming Simulator è un marchio di GIANTS Software.",
)

T["pt-BR"] = dict(
    sub="Gerenciador de mods para Farming Simulator (FS2011 a FS25), para Windows 10 e 11.",
    p1="A desvantagem do Farming Simulator é que ele oferece uma única pasta de mods, onde acabamos com muitos mapas e mods às vezes incompatíveis entre si. Trocar de uma configuração de partida para outra é tão trabalhoso que desanima de testar mapas novos.",
    p2="O coração do FS Passion resolve esse problema com uma eficiência surpreendente: crie em poucos cliques **partidas**, que são coleções de mods, e passe de uma para outra com um único clique. Todos os seus mods ficam em uma só cópia na pasta original, a pasta Mods.",
    f=[
        "**Partidas**: um mapa, suas dependências e os mods que você escolher; **mods comuns** compartilhados por todas as partidas.",
        "**Atualizações**: as feitas pelo jogo (ModHub) são recuperadas e acompanhadas em todas as partidas; uma versão substituída é guardada à parte, nunca apagada.",
        "**Downloads**: os mods novos são detectados e movidos para a pasta de mods da versão do jogo correspondente.",
        "**Vários discos**: até três pastas de mods em discos diferentes.",
        "**Backup da configuração**: exportação e importação de partidas e configurações, para uma reinstalação ou outro PC.",
        "**Tour guiado**: a lâmpada do cabeçalho apresenta a interface em um minuto, com exemplos animados (versões, partidas, listas, seleção múltipla, arrastar e soltar, atalhos de teclado).",
        "**Parar de usar o FS Passion**: o jogo volta à configuração original e as pastas de partidas são removidas; seus mods nunca são tocados.",
        "**Temas** bicolores e temas inspirados em temas populares, escuros e claros ({themes}).",
        "**Demo**: o aplicativo é destinado apenas a quem tem os jogos Farming Simulator. Se você está curioso e quer testar os recursos sem ter o jogo, há um pacote de demonstração nas Configurações.",
    ],
    warn="⚠️ Projeto em desenvolvimento (versão: veja a página [Releases]({releases})). Faça um backup completo da sua pasta de mods antes de experimentar. Esta página do GitHub é o único link oficial de download.",
    h_dl="Download",
    dl_intro="Na página [Releases]({releases}):",
    dl_setup="instalador, para o usuário atual sem direitos de administrador ou para todos os usuários; instala o Microsoft Edge WebView2 se necessário (Windows 10);",
    dl_port="versão portátil, sem instalação; configurações e logs ficam na pasta `data`, ao lado de `FSPassion.exe`;",
    dl_sums="somas de verificação dos dois arquivos.",
    dl_sign="Os arquivos ainda não são assinados: na primeira execução, o Windows SmartScreen pode exibir um aviso; abra as informações adicionais e escolha executar o aplicativo mesmo assim.",
    sign="A assinatura gratuita da SignPath Foundation está prevista após uma primeira versão.",
    soon="Em breve: mais {nsoon} idiomas",
    h_help="Ajude a melhorar as traduções",
    h_rep="Relatar um problema, sugerir uma ideia",
    rep="Aba [Issues]({issues}). Para um problema, anexe o texto de “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Apoiar o projeto",
    sup="O FS Passion é e continuará sendo um projeto confiável, de código aberto e gratuito. Para agradecer ao autor, uma doação única leva poucos segundos, sem criar conta: [Buy Me a Coffee]({bmac}) ou [doação com cartão (Stripe)]({stripe}).",
    h_net="Conexão com a Internet",
    net="O FS Passion só se conecta ao GitHub, para ler o catálogo de DLCs (nomes e ícones, repositório público `FSPassion-data`), no máximo uma vez por dia. Nenhum dado pessoal é enviado. A opção “Internet connection” (Settings → Application) desativa isso. Ele também procura no GitHub uma nova versão do FS Passion a cada inicialização (depois uma vez por dia): a opção “FS Passion updates” (Settings → Application) desativa isso.",
    h_lic="Licença",
    lic="FS Passion: **GPLv3** (arquivo `LICENSE`), autor MichelMichel. Documentação para desenvolvedores e créditos completos (ícones, fontes, temas): [README em inglês](../README.md).",
    disc="O FS Passion é um projeto independente, sem afiliação com a GIANTS Software. Farming Simulator é uma marca da GIANTS Software.",
)

T["pt-PT"] = dict(
    sub="Gestor de mods para Farming Simulator (FS2011 a FS25), para Windows 10 e 11.",
    p1="O inconveniente do Farming Simulator é oferecer uma única pasta de mods, onde acabamos com muitos mapas e mods por vezes incompatíveis entre si. Mudar de uma configuração de jogo para outra é tão trabalhoso que tira a vontade de experimentar mapas novos.",
    p2="O coração do FS Passion resolve este problema com uma eficácia surpreendente: crie em poucos cliques **partidas**, que são coleções de mods, e passe de uma para outra com um único clique. Todos os seus mods ficam num único exemplar na pasta de origem, a pasta Mods.",
    f=[
        "**Partidas**: um mapa, as suas dependências e os mods à sua escolha; **mods comuns** partilhados por todas as partidas.",
        "**Atualizações**: as feitas pelo jogo (ModHub) são recuperadas e acompanhadas em todas as partidas; uma versão substituída é posta de parte, nunca apagada.",
        "**Transferências**: os mods novos são detetados e arrumados na pasta de mods da versão do jogo correspondente.",
        "**Vários discos**: até três pastas de mods em discos diferentes.",
        "**Cópia de segurança da configuração**: exportação e importação de partidas e definições, para uma reinstalação ou outro PC.",
        "**Visita guiada**: a lâmpada do cabeçalho apresenta a interface num minuto, com exemplos animados (versões, partidas, listas, seleção múltipla, arrastar e largar, atalhos de teclado).",
        "**Deixar de usar o FS Passion**: o jogo recupera a definição original e as pastas de partidas são removidas; os seus mods nunca são tocados.",
        "**Temas** bicolores e temas inspirados em temas populares, escuros e claros ({themes}).",
        "**Demo**: a aplicação destina-se apenas a quem possui os jogos Farming Simulator. Se tem curiosidade e quer experimentar as funcionalidades sem ter o jogo, encontra um pacote de demonstração nas Definições.",
    ],
    warn="⚠️ Projeto em desenvolvimento (versão: ver a página [Releases]({releases})). Faça uma cópia de segurança completa da sua pasta de mods antes de experimentar. Esta página do GitHub é a única ligação oficial de transferência.",
    h_dl="Transferência",
    dl_intro="Na página [Releases]({releases}):",
    dl_setup="instalador, para o utilizador atual sem direitos de administrador ou para todos os utilizadores; instala o Microsoft Edge WebView2 se necessário (Windows 10);",
    dl_port="versão portátil, sem instalação; definições e registos ficam na pasta `data`, junto de `FSPassion.exe`;",
    dl_sums="somas de verificação dos dois ficheiros.",
    dl_sign="Os ficheiros ainda não estão assinados: na primeira execução, o Windows SmartScreen pode mostrar um aviso; abra as informações adicionais e escolha executar a aplicação mesmo assim.",
    sign="A assinatura gratuita da SignPath Foundation está prevista após uma primeira versão.",
    soon="Em breve: mais {nsoon} idiomas",
    h_help="Ajude a melhorar as traduções",
    h_rep="Comunicar um problema, propor uma ideia",
    rep="Separador [Issues]({issues}). Para um problema, junte o texto de «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Apoiar o projeto",
    sup="O FS Passion é e continuará a ser um projeto de confiança, de código aberto e gratuito. Para agradecer ao autor, um donativo pontual faz-se em segundos, sem criar conta: [Buy Me a Coffee]({bmac}) ou [donativo por cartão (Stripe)]({stripe}).",
    h_net="Ligação à Internet",
    net="O FS Passion só se liga ao GitHub, para ler o catálogo de DLC (nomes e ícones, repositório público `FSPassion-data`), no máximo uma vez por dia. Nenhum dado pessoal é enviado. A definição «Internet connection» (Settings → Application) desativa-a. Também procura no GitHub uma nova versão do FS Passion em cada arranque (depois uma vez por dia): a definição «FS Passion updates» (Settings → Application) desativa-a.",
    h_lic="Licença",
    lic="FS Passion: **GPLv3** (ficheiro `LICENSE`), autor MichelMichel. Documentação para programadores e créditos completos (ícones, tipos de letra, temas): [README em inglês](../README.md).",
    disc="O FS Passion é um projeto independente, sem ligação à GIANTS Software. Farming Simulator é uma marca da GIANTS Software.",
)

T["nl"] = dict(
    sub="Modbeheerder voor Farming Simulator (FS2011 tot FS25), voor Windows 10 en 11.",
    p1="Het nadeel van Farming Simulator is dat het maar één modmap heeft, waarin we eindigen met veel maps en mods die soms niet met elkaar samengaan. Wisselen tussen spelconfiguraties is zo omslachtig dat het je ervan weerhoudt nieuwe maps te proberen.",
    p2="Het hart van FS Passion lost dit probleem verrassend efficiënt op: maak in een paar klikken **setups** – verzamelingen van mods – en wissel ertussen met één klik. Al je mods blijven in één exemplaar in hun oorspronkelijke map, de map Mods.",
    f=[
        "**Setups**: een map, de afhankelijkheden ervan en de mods van je keuze; **gedeelde mods** voor alle setups.",
        "**Updates**: updates die het spel uitvoert (ModHub) worden opgehaald en in alle setups gevolgd; een vervangen versie wordt apart gezet, nooit gewist.",
        "**Downloads**: nieuwe mods worden herkend en in de modmap van de juiste spelversie gezet.",
        "**Meerdere schijven**: tot drie modmappen op verschillende schijven.",
        "**Back-up van de configuratie**: export en import van setups en instellingen, voor een herinstallatie of een andere pc.",
        "**Rondleiding**: het lampje in de koptekst toont de interface in één minuut, met geanimeerde voorbeelden (versies, setups, lijsten, meervoudige selectie, slepen en neerzetten, sneltoetsen).",
        "**FS Passion niet meer gebruiken**: het spel krijgt zijn oorspronkelijke instelling terug en de setupmappen worden verwijderd; je mods worden nooit aangeraakt.",
        "Tweekleurige **thema's**, en thema's geïnspireerd op populaire thema's, donker en licht ({themes}).",
        "**Demo**: de applicatie is alleen bedoeld voor bezitters van de Farming Simulator-games. Ben je nieuwsgierig en wil je de functies uitproberen zonder het spel, dan staat er een demopakket in de Instellingen.",
    ],
    warn="⚠️ Project in ontwikkeling (versie: zie de pagina [Releases]({releases})). Maak een volledige back-up van je modmap voordat je het probeert. Deze GitHub-pagina is de enige officiële downloadlocatie.",
    h_dl="Downloaden",
    dl_intro="Op de pagina [Releases]({releases}):",
    dl_setup="installatieprogramma, voor de huidige gebruiker zonder beheerdersrechten of voor alle gebruikers; installeert zo nodig Microsoft Edge WebView2 (Windows 10);",
    dl_port="draagbare versie, zonder installatie; instellingen en logboeken blijven in de map `data` naast `FSPassion.exe`;",
    dl_sums="controlesommen van beide bestanden.",
    dl_sign="De bestanden zijn nog niet ondertekend: bij de eerste start kan Windows SmartScreen een waarschuwing tonen; open de aanvullende informatie en kies ervoor de app toch uit te voeren.",
    sign="Gratis ondertekening door de SignPath Foundation is gepland na een eerste release.",
    soon="Binnenkort: nog {nsoon} talen",
    h_help="Help de vertalingen verbeteren",
    h_rep="Een probleem melden, een idee voorstellen",
    rep="Tabblad [Issues]({issues}). Voeg bij een probleem de tekst van “Copy diagnostics” toe (Settings → Help and about → Logs and diagnostics).",
    h_sup="Het project steunen",
    sup="FS Passion is en blijft een betrouwbaar, opensource en gratis project. Een eenmalige donatie aan de auteur duurt maar een paar seconden, zonder account: [Buy Me a Coffee]({bmac}) of [donatie per kaart (Stripe)]({stripe}).",
    h_net="Internetverbinding",
    net="FS Passion maakt alleen verbinding met GitHub, om de DLC-catalogus te lezen (namen en pictogrammen, openbare repository `FSPassion-data`), hooguit één keer per dag. Er worden geen persoonlijke gegevens verzonden. De instelling “Internet connection” (Settings → Application) schakelt dit uit. Daarnaast zoekt het bij elke start (daarna één keer per dag) op GitHub naar een nieuwe versie van FS Passion: de instelling “FS Passion updates” (Settings → Application) schakelt dit uit.",
    h_lic="Licentie",
    lic="FS Passion: **GPLv3** (bestand `LICENSE`), auteur MichelMichel. Documentatie voor ontwikkelaars en alle vermeldingen (pictogrammen, lettertypen, thema's): [Engelse README](../README.md).",
    disc="FS Passion is een onafhankelijk project, niet verbonden aan GIANTS Software. Farming Simulator is een handelsmerk van GIANTS Software.",
)

T["pl"] = dict(
    sub="Menedżer modów do Farming Simulator (od FS2011 do FS25), dla Windows 10 i 11.",
    p1="Wadą Farming Simulator jest to, że oferuje tylko jeden folder modów, w którym gromadzi się wiele map i modów, czasem niezgodnych ze sobą. Przechodzenie z jednej konfiguracji gry do drugiej jest tak uciążliwe, że zniechęca do wypróbowywania nowych map.",
    p2="Sercem FS Passion jest rozwiązanie tego problemu z zaskakującą skutecznością: w kilka kliknięć tworzysz **zestawy**, czyli kolekcje modów, i przełączasz się między nimi jednym kliknięciem. Wszystkie twoje mody zostają w jednym egzemplarzu w swoim pierwotnym folderze, folderze Mods.",
    f=[
        "**Zestawy**: mapa, jej zależności i wybrane przez ciebie mody; **wspólne mody** dzielone przez wszystkie zestawy.",
        "**Aktualizacje**: te wykonane przez grę (ModHub) są przejmowane i śledzone we wszystkich zestawach; zastąpiona wersja jest odkładana na bok, nigdy usuwana.",
        "**Pobrane pliki**: nowe mody są wykrywane i przenoszone do folderu modów odpowiedniej wersji gry.",
        "**Kilka dysków**: do trzech folderów modów na różnych dyskach.",
        "**Kopia zapasowa konfiguracji**: eksport i import zestawów oraz ustawień, na potrzeby ponownej instalacji lub innego komputera.",
        "**Przewodnik**: żarówka w nagłówku przedstawia interfejs w minutę, z animowanymi przykładami (wersje, zestawy, listy, zaznaczanie wielu, przeciąganie i upuszczanie, skróty klawiszowe).",
        "**Przestań używać FS Passion**: gra odzyskuje oryginalne ustawienie, a foldery zestawów są usuwane; twoje mody nigdy nie są ruszane.",
        "Dwukolorowe **motywy** oraz motywy inspirowane popularnymi, ciemne i jasne ({themes}).",
        "**Demo**: aplikacja jest przeznaczona wyłącznie dla posiadaczy gier Farming Simulator. Jeśli jesteś ciekawy i chcesz wypróbować jej funkcje bez gry, w Ustawieniach znajdziesz pakiet demonstracyjny.",
    ],
    warn="⚠️ Projekt w trakcie rozwoju (wersja: zobacz stronę [Releases]({releases})). Przed wypróbowaniem zrób pełną kopię zapasową folderu modów. Ta strona GitHub jest jedynym oficjalnym źródłem pobierania.",
    h_dl="Pobieranie",
    dl_intro="Na stronie [Releases]({releases}):",
    dl_setup="instalator, dla bieżącego użytkownika bez uprawnień administratora lub dla wszystkich użytkowników; w razie potrzeby instaluje Microsoft Edge WebView2 (Windows 10);",
    dl_port="wersja przenośna, bez instalacji; ustawienia i dzienniki zostają w folderze `data` obok `FSPassion.exe`;",
    dl_sums="sumy kontrolne obu plików.",
    dl_sign="Pliki nie są jeszcze podpisane: przy pierwszym uruchomieniu Windows SmartScreen może wyświetlić ostrzeżenie; otwórz dodatkowe informacje i wybierz uruchomienie aplikacji mimo to.",
    sign="Bezpłatne podpisywanie przez SignPath Foundation jest planowane po pierwszej wersji.",
    soon="Wkrótce: {nsoon} kolejnych języków",
    h_help="Pomóż ulepszyć tłumaczenia",
    h_rep="Zgłoś problem, zaproponuj pomysł",
    rep="Zakładka [Issues]({issues}). Przy problemie dołącz tekst z „Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Wesprzyj projekt",
    sup="FS Passion jest i pozostanie projektem godnym zaufania, otwartym i darmowym. Jednorazowa darowizna dla autora zajmuje kilka sekund, bez zakładania konta: [Buy Me a Coffee]({bmac}) lub [darowizna kartą (Stripe)]({stripe}).",
    h_net="Połączenie z internetem",
    net="FS Passion łączy się tylko z GitHubem, aby odczytać katalog DLC (nazwy i ikony, publiczne repozytorium `FSPassion-data`), najwyżej raz dziennie. Żadne dane osobowe nie są wysyłane. Ustawienie „Internet connection” (Settings → Application) to wyłącza. Przy każdym uruchomieniu (potem raz dziennie) sprawdza też na GitHubie, czy jest nowa wersja FS Passion: ustawienie „FS Passion updates” (Settings → Application) to wyłącza.",
    h_lic="Licencja",
    lic="FS Passion: **GPLv3** (plik `LICENSE`), autor MichelMichel. Dokumentacja dla programistów i pełne podziękowania (ikony, czcionki, motywy): [README po angielsku](../README.md).",
    disc="FS Passion jest niezależnym projektem, niezwiązanym z GIANTS Software. Farming Simulator jest znakiem towarowym GIANTS Software.",
)

T["cs"] = dict(
    sub="Správce modů pro Farming Simulator (FS2011 až FS25), pro Windows 10 a 11.",
    p1="Nevýhodou Farming Simulatoru je, že nabízí jedinou složku modů, ve které se nám hromadí spousta map a modů, které spolu někdy nejsou kompatibilní. Přecházet z jedné herní konfigurace do druhé je tak pracné, že to odrazuje od zkoušení nových map.",
    p2="Srdcem FS Passion je vyřešit tento problém s překvapivou účinností: vytvořte během pár kliknutí **sestavy**, tedy kolekce modů, a přepínejte mezi nimi jediným kliknutím. Všechny vaše mody zůstanou v jediné kopii ve své původní složce, složce Mods.",
    f=[
        "**Sestavy**: mapa, její závislosti a mody podle vašeho výběru; **společné mody** sdílené všemi sestavami.",
        "**Aktualizace**: ty, které provede hra (ModHub), se převezmou a sledují ve všech sestavách; nahrazená verze se odloží stranou, nikdy se nesmaže.",
        "**Stažené soubory**: nové mody se rozpoznají a přesunou do složky modů odpovídající verze hry.",
        "**Více disků**: až tři složky modů na různých discích.",
        "**Záloha konfigurace**: export a import sestav a nastavení, pro přeinstalaci nebo jiný počítač.",
        "**Prohlídka**: žárovka v záhlaví představí rozhraní za minutu, s animovanými příklady (verze, sestavy, seznamy, vícenásobný výběr, přetažení, klávesové zkratky).",
        "**Přestat používat FS Passion**: hra získá zpět své původní nastavení a složky sestav se odstraní; vašich modů se nic nedotkne.",
        "Dvoubarevné **motivy** a motivy inspirované populárními motivy, tmavé i světlé ({themes}).",
        "**Demo**: aplikace je určena výhradně majitelům her Farming Simulator. Pokud jste zvědaví a chcete si funkce vyzkoušet bez hry, v Nastavení najdete demonstrační balíček.",
    ],
    warn="⚠️ Projekt ve vývoji (verze: viz stránka [Releases]({releases})). Před vyzkoušením si udělejte úplnou zálohu složky modů. Tato stránka GitHub je jediným oficiálním místem ke stažení.",
    h_dl="Stažení",
    dl_intro="Na stránce [Releases]({releases}):",
    dl_setup="instalátor, pro aktuálního uživatele bez oprávnění správce nebo pro všechny uživatele; v případě potřeby nainstaluje Microsoft Edge WebView2 (Windows 10);",
    dl_port="přenosná verze, bez instalace; nastavení a protokoly zůstávají ve složce `data` vedle `FSPassion.exe`;",
    dl_sums="kontrolní součty obou souborů.",
    dl_sign="Soubory zatím nejsou podepsané: při prvním spuštění může Windows SmartScreen zobrazit varování; otevřete další informace a zvolte, že aplikaci přesto chcete spustit.",
    sign="Bezplatné podepisování od SignPath Foundation je plánováno po první verzi.",
    soon="Brzy: dalších {nsoon} jazyků",
    h_help="Pomozte zlepšit překlady",
    h_rep="Nahlásit problém, navrhnout nápad",
    rep="Karta [Issues]({issues}). U problému přiložte text z „Copy diagnostics“ (Settings → Help and about → Logs and diagnostics).",
    h_sup="Podpořit projekt",
    sup="FS Passion je a zůstane důvěryhodným, otevřeným a bezplatným projektem. Jednorázový dar autorovi zabere pár sekund, bez zakládání účtu: [Buy Me a Coffee]({bmac}) nebo [dar kartou (Stripe)]({stripe}).",
    h_net="Připojení k internetu",
    net="FS Passion se připojuje pouze ke GitHubu, aby načetl katalog DLC (názvy a ikony, veřejný repozitář `FSPassion-data`), nejvýše jednou denně. Neodesílají se žádné osobní údaje. Nastavení „Internet connection“ (Settings → Application) to vypne. Při každém spuštění (pak jednou denně) také hledá na GitHubu novou verzi FS Passion: nastavení „FS Passion updates“ (Settings → Application) to vypne.",
    h_lic="Licence",
    lic="FS Passion: **GPLv3** (soubor `LICENSE`), autor MichelMichel. Dokumentace pro vývojáře a úplné poděkování (ikony, písma, motivy): [anglické README](../README.md).",
    disc="FS Passion je nezávislý projekt, který není spojen se společností GIANTS Software. Farming Simulator je ochranná známka společnosti GIANTS Software.",
)

T["da"] = dict(
    sub="Mod-håndtering til Farming Simulator (FS2011 til FS25), til Windows 10 og 11.",
    p1="Ulempen ved Farming Simulator er, at det kun har én mod-mappe, hvor vi ender med mange maps og mods, der nogle gange ikke passer sammen. Det er så besværligt at skifte fra én spilopsætning til en anden, at man holder sig fra at prøve nye maps.",
    p2="Hjertet i FS Passion løser dette problem forbløffende effektivt: Opret med få klik **opsætninger** – samlinger af mods – og skift mellem dem med ét klik. Alle dine mods forbliver i ét eksemplar i deres oprindelige mappe, mappen Mods.",
    f=[
        "**Opsætninger**: et map, dets afhængigheder og de mods, du vælger; **fælles mods**, som alle opsætninger deler.",
        "**Opdateringer**: dem, spillet laver (ModHub), hentes og følges i alle opsætninger; en erstattet version lægges til side, aldrig slettet.",
        "**Downloads**: nye mods registreres og flyttes til mod-mappen for den tilsvarende spilversion.",
        "**Flere drev**: op til tre mod-mapper på forskellige drev.",
        "**Sikkerhedskopi af konfigurationen**: eksport og import af opsætninger og indstillinger, til en geninstallation eller en anden pc.",
        "**Guidet tur**: pæren i overskriften viser grænsefladen på et minut med animerede eksempler (versioner, opsætninger, lister, multivalg, træk og slip, tastaturgenveje).",
        "**Stop med at bruge FS Passion**: spillet får sin oprindelige indstilling tilbage, og opsætningsmapperne fjernes; dine mods røres aldrig.",
        "Tofarvede **temaer** og temaer inspireret af populære temaer, mørke og lyse ({themes}).",
        "**Demo**: Programmet er kun beregnet til ejere af Farming Simulator-spillene. Er du nysgerrig og vil prøve funktionerne uden at eje spillet, finder du en demopakke i Indstillinger.",
    ],
    warn="⚠️ Projekt under udvikling (version: se siden [Releases]({releases})). Tag en fuld sikkerhedskopi af din mod-mappe, før du prøver det. Denne GitHub-side er det eneste officielle downloadsted.",
    h_dl="Download",
    dl_intro="På siden [Releases]({releases}):",
    dl_setup="installationsprogram, til den aktuelle bruger uden administratorrettigheder eller til alle brugere; installerer Microsoft Edge WebView2 om nødvendigt (Windows 10);",
    dl_port="bærbar version uden installation; indstillinger og logfiler bliver i mappen `data` ved siden af `FSPassion.exe`;",
    dl_sums="kontrolsummer for begge filer.",
    dl_sign="Filerne er endnu ikke signerede: Ved første start kan Windows SmartScreen vise en advarsel; åbn de yderligere oplysninger, og vælg at køre programmet alligevel.",
    sign="Gratis signering af SignPath Foundation er planlagt efter en første udgivelse.",
    soon="Kommer snart: {nsoon} flere sprog",
    h_help="Hjælp med at forbedre oversættelserne",
    h_rep="Rapportér et problem, foreslå en idé",
    rep="Fanen [Issues]({issues}). Ved et problem skal du vedhæfte teksten fra “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Støt projektet",
    sup="FS Passion er og forbliver et pålideligt, open source og gratis projekt. En enkelt donation til forfatteren tager få sekunder, uden at oprette en konto: [Buy Me a Coffee]({bmac}) eller [donation med kort (Stripe)]({stripe}).",
    h_net="Internetforbindelse",
    net="FS Passion forbinder kun til GitHub for at læse DLC-kataloget (navne og ikoner, offentligt repository `FSPassion-data`), højst én gang om dagen. Ingen personlige data sendes. Indstillingen “Internet connection” (Settings → Application) slår det fra. Ved hver start (derefter én gang om dagen) søger det også på GitHub efter en ny version af FS Passion: indstillingen “FS Passion updates” (Settings → Application) slår det fra.",
    h_lic="Licens",
    lic="FS Passion: **GPLv3** (filen `LICENSE`), forfatter MichelMichel. Dokumentation for udviklere og alle krediteringer (ikoner, skrifttyper, temaer): [engelsk README](../README.md).",
    disc="FS Passion er et uafhængigt projekt, ikke tilknyttet GIANTS Software. Farming Simulator er et varemærke tilhørende GIANTS Software.",
)

T["fi"] = dict(
    sub="Modienhallinta Farming Simulatoriin (FS2011–FS25), Windows 10:lle ja 11:lle.",
    p1="Farming Simulatorin heikkous on, että siinä on vain yksi modikansio, johon kertyy paljon karttoja ja modeja, jotka eivät aina sovi yhteen. Siirtyminen pelikokoonpanosta toiseen on niin työlästä, että uusien karttojen kokeileminen jää helposti tekemättä.",
    p2="FS Passionin ydin ratkaisee tämän ongelman hämmästyttävän tehokkaasti: luo muutamalla napsautuksella **kokoonpanoja** eli modikokoelmia ja vaihda niiden välillä yhdellä napsautuksella. Kaikki modisi pysyvät yhtenä kappaleena alkuperäisessä kansiossaan, Mods-kansiossa.",
    f=[
        "**Kokoonpanot**: kartta, sen riippuvuudet ja valitsemasi modit; **yhteiset modit**, jotka kaikki kokoonpanot jakavat.",
        "**Päivitykset**: pelin tekemät päivitykset (ModHub) otetaan talteen ja niitä seurataan kaikissa kokoonpanoissa; korvattu versio siirretään sivuun, ei koskaan poisteta.",
        "**Lataukset**: uudet modit tunnistetaan ja siirretään oikean peliversion modikansioon.",
        "**Useita levyjä**: enintään kolme modikansiota eri levyillä.",
        "**Asetusten varmuuskopio**: kokoonpanojen ja asetusten vienti ja tuonti uudelleenasennusta tai toista tietokonetta varten.",
        "**Esittelykierros**: otsikkopalkin hehkulamppu esittelee käyttöliittymän minuutissa animoiduin esimerkein (versiot, kokoonpanot, luettelot, monivalinta, vedä ja pudota, pikanäppäimet).",
        "**Lopeta FS Passionin käyttö**: peli saa alkuperäisen asetuksensa takaisin ja kokoonpanokansiot poistetaan; modeihisi ei kosketa.",
        "Kaksiväriset **teemat** sekä suosittujen teemojen innoittamat teemat, tummat ja vaaleat ({themes}).",
        "**Demo**: sovellus on tarkoitettu vain Farming Simulator -pelien omistajille. Jos olet utelias ja haluat kokeilla ominaisuuksia ilman peliä, asetuksista löytyy esittelypaketti.",
    ],
    warn="⚠️ Projekti on kehitysvaiheessa (versio: katso sivu [Releases]({releases})). Tee täydellinen varmuuskopio modikansiostasi ennen kokeilua. Tämä GitHub-sivu on ainoa virallinen latauspaikka.",
    h_dl="Lataus",
    dl_intro="Sivulla [Releases]({releases}):",
    dl_setup="asennusohjelma nykyiselle käyttäjälle ilman järjestelmänvalvojan oikeuksia tai kaikille käyttäjille; asentaa tarvittaessa Microsoft Edge WebView2:n (Windows 10);",
    dl_port="siirrettävä versio ilman asennusta; asetukset ja lokit pysyvät kansiossa `data` tiedoston `FSPassion.exe` vieressä;",
    dl_sums="molempien tiedostojen tarkistussummat.",
    dl_sign="Tiedostoja ei ole vielä allekirjoitettu: ensimmäisellä käynnistyskerralla Windows SmartScreen voi näyttää varoituksen; avaa lisätiedot ja valitse sovelluksen suorittaminen silti.",
    sign="SignPath Foundationin ilmainen allekirjoitus on suunniteltu ensimmäisen julkaisun jälkeen.",
    soon="Tulossa pian: {nsoon} kieltä lisää",
    h_help="Auta parantamaan käännöksiä",
    h_rep="Ilmoita ongelmasta, ehdota ideaa",
    rep="Välilehti [Issues]({issues}). Liitä ongelmailmoitukseen teksti kohdasta ”Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Tue projektia",
    sup="FS Passion on ja pysyy luotettavana, avoimen lähdekoodin ja maksuttomana projektina. Kertalahjoitus tekijälle vie muutaman sekunnin ilman tilin luomista: [Buy Me a Coffee]({bmac}) tai [lahjoitus kortilla (Stripe)]({stripe}).",
    h_net="Internet-yhteys",
    net="FS Passion muodostaa yhteyden vain GitHubiin lukeakseen DLC-luettelon (nimet ja kuvakkeet, julkinen `FSPassion-data`-repositorio), enintään kerran päivässä. Henkilötietoja ei lähetetä. Asetus ”Internet connection” (Settings → Application) poistaa sen käytöstä. Lisäksi se etsii GitHubista FS Passionin uutta versiota joka käynnistyksellä (sen jälkeen kerran päivässä): asetus ”FS Passion updates” (Settings → Application) poistaa sen käytöstä.",
    h_lic="Lisenssi",
    lic="FS Passion: **GPLv3** (tiedosto `LICENSE`), tekijä MichelMichel. Kehittäjien dokumentaatio ja täydet tekijätiedot (kuvakkeet, fontit, teemat): [englanninkielinen README](../README.md).",
    disc="FS Passion on itsenäinen projekti, joka ei liity GIANTS Softwareen. Farming Simulator on GIANTS Softwaren tavaramerkki.",
)

T["hu"] = dict(
    sub="Modkezelő a Farming Simulatorhoz (FS2011-től FS25-ig), Windows 10 és 11 rendszerre.",
    p1="A Farming Simulator hátránya, hogy csak egyetlen modmappát kínál, amelyben rengeteg térkép és mod gyűlik össze, amelyek néha nem férnek meg egymással. Az egyik játékkonfigurációról a másikra váltani olyan körülményes, hogy elveszi a kedvet az új térképek kipróbálásától.",
    p2="Az FS Passion lényege, hogy ezt a problémát meglepő hatékonysággal oldja meg: néhány kattintással **összeállításokat** – modgyűjteményeket – hozhatsz létre, és egyetlen kattintással válthatsz közöttük. Minden modod egyetlen példányban marad az eredeti mappájában, a Mods mappában.",
    f=[
        "**Összeállítások**: egy térkép, a függőségei és az általad választott modok; **közös modok**, amelyeken minden összeállítás osztozik.",
        "**Frissítések**: a játék által végzett frissítéseket (ModHub) átveszi és minden összeállításban követi; a lecserélt verziót félreteszi, sosem törli.",
        "**Letöltések**: az új modokat felismeri, és a megfelelő játékverzió modmappájába helyezi.",
        "**Több meghajtó**: legfeljebb három modmappa különböző meghajtókon.",
        "**A beállítások mentése**: összeállítások és beállítások exportálása és importálása újratelepítéshez vagy másik géphez.",
        "**Bemutató**: a fejléc villanykörtéje egy perc alatt bemutatja a felületet, animált példákkal (verziók, összeállítások, listák, többes kijelölés, húzás és ejtés, billentyűparancsok).",
        "**Az FS Passion használatának befejezése**: a játék visszakapja eredeti beállítását, az összeállítások mappái törlődnek; a modjaidhoz sosem nyúl.",
        "Kétszínű **témák**, valamint népszerű témák ihlette témák sötét és világos változatban ({themes}).",
        "**Demó**: az alkalmazás kizárólag a Farming Simulator játékok tulajdonosainak készült. Ha kíváncsi vagy, és játék nélkül szeretnéd kipróbálni a funkciókat, a Beállításokban találsz egy bemutatócsomagot.",
    ],
    warn="⚠️ Fejlesztés alatt álló projekt (verzió: lásd a [Releases]({releases}) oldalt). Kipróbálás előtt készíts teljes biztonsági mentést a modmappádról. Ez a GitHub-oldal az egyetlen hivatalos letöltési hely.",
    h_dl="Letöltés",
    dl_intro="A [Releases]({releases}) oldalon:",
    dl_setup="telepítő, az aktuális felhasználónak rendszergazdai jogok nélkül vagy minden felhasználónak; szükség esetén telepíti a Microsoft Edge WebView2-t (Windows 10);",
    dl_port="hordozható verzió, telepítés nélkül; a beállítások és naplók a `FSPassion.exe` melletti `data` mappában maradnak;",
    dl_sums="a két fájl ellenőrzőösszegei.",
    dl_sign="A fájlok még nincsenek aláírva: első indításkor a Windows SmartScreen figyelmeztetést jeleníthet meg; nyisd meg a további információkat, és válaszd az alkalmazás futtatását mindenképp.",
    sign="Az SignPath Foundation ingyenes aláírása az első kiadás után van tervben.",
    soon="Hamarosan: még {nsoon} nyelv",
    h_help="Segíts a fordítások javításában",
    h_rep="Hiba bejelentése, ötlet javaslása",
    rep="[Issues]({issues}) fül. Hiba esetén csatold a „Copy diagnostics” szövegét (Settings → Help and about → Logs and diagnostics).",
    h_sup="A projekt támogatása",
    sup="Az FS Passion megbízható, nyílt forráskódú és ingyenes projekt, és az is marad. Egyszeri adomány a szerzőnek néhány másodperc, fiók létrehozása nélkül: [Buy Me a Coffee]({bmac}) vagy [adomány kártyával (Stripe)]({stripe}).",
    h_net="Internetkapcsolat",
    net="Az FS Passion csak a GitHubhoz csatlakozik, hogy beolvassa a DLC-katalógust (nevek és ikonok, nyilvános `FSPassion-data` tároló), legfeljebb naponta egyszer. Személyes adatot nem küld. Az „Internet connection” beállítás (Settings → Application) kikapcsolja. Emellett minden indításkor (utána naponta egyszer) megnézi a GitHubon, van-e új FS Passion-verzió: az „FS Passion updates” beállítás (Settings → Application) kikapcsolja.",
    h_lic="Licenc",
    lic="FS Passion: **GPLv3** (`LICENSE` fájl), szerző: MichelMichel. Fejlesztői dokumentáció és teljes köszönetnyilvánítás (ikonok, betűtípusok, témák): [angol nyelvű README](../README.md).",
    disc="Az FS Passion független projekt, nem áll kapcsolatban a GIANTS Software-rel. A Farming Simulator a GIANTS Software védjegye.",
)

T["nb"] = dict(
    sub="Modbehandler for Farming Simulator (FS2011 til FS25), for Windows 10 og 11.",
    p1="Ulempen med Farming Simulator er at det bare har én modmappe, der vi ender opp med mange kart og modder som noen ganger ikke passer sammen. Å bytte fra ett spilloppsett til et annet er så tungvint at det holder oss tilbake fra å prøve nye kart.",
    p2="Hjertet i FS Passion løser dette problemet forbløffende effektivt: Lag **oppsett** – samlinger av modder – med noen få klikk, og bytt mellom dem med ett klikk. Alle moddene dine blir liggende i ett eksemplar i den opprinnelige mappen, Mods-mappen.",
    f=[
        "**Oppsett**: et kart, avhengighetene og moddene du velger; **felles modder** som deles av alle oppsett.",
        "**Oppdateringer**: de som spillet gjør (ModHub), hentes inn og følges i alle oppsett; en erstattet versjon legges til side, aldri slettet.",
        "**Nedlastinger**: nye modder oppdages og flyttes til modmappen for riktig spillversjon.",
        "**Flere disker**: opptil tre modmapper på forskjellige disker.",
        "**Sikkerhetskopi av konfigurasjonen**: eksport og import av oppsett og innstillinger, for en ny installasjon eller en annen PC.",
        "**Omvisning**: lyspæren i toppfeltet viser grensesnittet på ett minutt, med animerte eksempler (versjoner, oppsett, lister, flervalg, dra og slipp, hurtigtaster).",
        "**Slutt å bruke FS Passion**: spillet får tilbake den opprinnelige innstillingen, og oppsettmappene fjernes; moddene dine blir aldri rørt.",
        "Tofargede **temaer**, og temaer inspirert av populære temaer, mørke og lyse ({themes}).",
        "**Demo**: Programmet er bare ment for dem som eier Farming Simulator-spillene. Er du nysgjerrig og vil prøve funksjonene uten spillet, finner du en demopakke i Innstillinger.",
    ],
    warn="⚠️ Prosjekt under utvikling (versjon: se siden [Releases]({releases})). Ta en full sikkerhetskopi av modmappen før du prøver det. Denne GitHub-siden er det eneste offisielle nedlastingsstedet.",
    h_dl="Nedlasting",
    dl_intro="På siden [Releases]({releases}):",
    dl_setup="installasjonsprogram, for gjeldende bruker uten administratorrettigheter eller for alle brukere; installerer Microsoft Edge WebView2 ved behov (Windows 10);",
    dl_port="bærbar versjon uten installasjon; innstillinger og logger blir liggende i mappen `data` ved siden av `FSPassion.exe`;",
    dl_sums="kontrollsummer for begge filene.",
    dl_sign="Filene er ikke signert ennå: Ved første oppstart kan Windows SmartScreen vise en advarsel; åpne tilleggsinformasjonen og velg å kjøre programmet likevel.",
    sign="Gratis signering fra SignPath Foundation er planlagt etter en første utgivelse.",
    soon="Kommer snart: {nsoon} flere språk",
    h_help="Hjelp til med å forbedre oversettelsene",
    h_rep="Meld fra om et problem, foreslå en idé",
    rep="Fanen [Issues]({issues}). Ved et problem legger du ved teksten fra «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Støtt prosjektet",
    sup="FS Passion er og forblir et pålitelig, åpen kildekode- og gratis prosjekt. En enkeltdonasjon til forfatteren tar noen sekunder, uten å opprette konto: [Buy Me a Coffee]({bmac}) eller [donasjon med kort (Stripe)]({stripe}).",
    h_net="Internettilkobling",
    net="FS Passion kobler seg bare til GitHub for å lese DLC-katalogen (navn og ikoner, offentlig repository `FSPassion-data`), høyst én gang om dagen. Ingen personopplysninger sendes. Innstillingen «Internet connection» (Settings → Application) slår det av. Ved hver oppstart (deretter én gang om dagen) ser det også etter en ny versjon av FS Passion på GitHub: innstillingen «FS Passion updates» (Settings → Application) slår det av.",
    h_lic="Lisens",
    lic="FS Passion: **GPLv3** (filen `LICENSE`), forfatter MichelMichel. Dokumentasjon for utviklere og alle krediteringer (ikoner, skrifter, temaer): [engelsk README](../README.md).",
    disc="FS Passion er et uavhengig prosjekt uten tilknytning til GIANTS Software. Farming Simulator er et varemerke for GIANTS Software.",
)

T["ro"] = dict(
    sub="Manager de moduri pentru Farming Simulator (FS2011 până la FS25), pentru Windows 10 și 11.",
    p1="Dezavantajul Farming Simulator este că oferă un singur folder de moduri, în care ajungem să avem multe hărți și moduri uneori incompatibile între ele. Trecerea de la o configurație de joc la alta este atât de anevoioasă încât descurajează încercarea unor hărți noi.",
    p2="Inima FS Passion rezolvă această problemă cu o eficiență surprinzătoare: creează din câteva clicuri **configurații**, adică colecții de moduri, și treci de la una la alta cu un singur clic. Toate modurile tale rămân într-un singur exemplar în folderul lor de origine, folderul Mods.",
    f=[
        "**Configurații**: o hartă, dependențele ei și modurile alese de tine; **moduri comune**, folosite de toate configurațiile.",
        "**Actualizări**: cele făcute de joc (ModHub) sunt preluate și urmărite în toate configurațiile; o versiune înlocuită este pusă deoparte, niciodată ștearsă.",
        "**Descărcări**: modurile noi sunt detectate și mutate în folderul de moduri al versiunii de joc corespunzătoare.",
        "**Mai multe discuri**: până la trei foldere de moduri pe discuri diferite.",
        "**Copie de siguranță a configurării**: export și import al configurațiilor și setărilor, pentru o reinstalare sau alt PC.",
        "**Tur ghidat**: becul din antet prezintă interfața într-un minut, cu exemple animate (versiuni, configurații, liste, selecție multiplă, glisare și plasare, comenzi rapide).",
        "**Nu mai folosi FS Passion**: jocul își recapătă setarea originală, iar folderele configurațiilor sunt eliminate; modurile tale nu sunt atinse niciodată.",
        "**Teme** bicolore și teme inspirate de teme populare, întunecate și luminoase ({themes}).",
        "**Demo**: aplicația se adresează exclusiv celor care dețin jocurile Farming Simulator. Dacă ești curios și vrei să-i încerci funcțiile fără să ai jocul, în Setări găsești un pachet demonstrativ.",
    ],
    warn="⚠️ Proiect în dezvoltare (versiune: vezi pagina [Releases]({releases})). Fă o copie de siguranță completă a folderului de moduri înainte de a-l încerca. Această pagină GitHub este singura sursă oficială de descărcare.",
    h_dl="Descărcare",
    dl_intro="Pe pagina [Releases]({releases}):",
    dl_setup="program de instalare, pentru utilizatorul curent fără drepturi de administrator sau pentru toți utilizatorii; instalează Microsoft Edge WebView2 dacă e nevoie (Windows 10);",
    dl_port="versiune portabilă, fără instalare; setările și jurnalele rămân în folderul `data` de lângă `FSPassion.exe`;",
    dl_sums="sumele de control ale celor două fișiere.",
    dl_sign="Fișierele nu sunt încă semnate: la prima pornire, Windows SmartScreen poate afișa un avertisment; deschide informațiile suplimentare și alege să rulezi totuși aplicația.",
    sign="Semnarea gratuită de către SignPath Foundation este planificată după o primă lansare.",
    soon="În curând: încă {nsoon} limbi",
    h_help="Ajută la îmbunătățirea traducerilor",
    h_rep="Raportează o problemă, propune o idee",
    rep="Fila [Issues]({issues}). Pentru o problemă, atașează textul din „Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Susține proiectul",
    sup="FS Passion este și va rămâne un proiect de încredere, open source și gratuit. O donație unică pentru autor durează câteva secunde, fără cont: [Buy Me a Coffee]({bmac}) sau [donație cu cardul (Stripe)]({stripe}).",
    h_net="Conexiunea la internet",
    net="FS Passion se conectează doar la GitHub, pentru a citi catalogul DLC (nume și pictograme, depozitul public `FSPassion-data`), cel mult o dată pe zi. Nu se trimit date personale. Setarea „Internet connection” (Settings → Application) o dezactivează. De asemenea, la fiecare pornire (apoi o dată pe zi) caută pe GitHub o versiune nouă de FS Passion: setarea „FS Passion updates” (Settings → Application) o dezactivează.",
    h_lic="Licență",
    lic="FS Passion: **GPLv3** (fișierul `LICENSE`), autor MichelMichel. Documentație pentru dezvoltatori și mențiuni complete (pictograme, fonturi, teme): [README în engleză](../README.md).",
    disc="FS Passion este un proiect independent, neafiliat cu GIANTS Software. Farming Simulator este o marcă a GIANTS Software.",
)

T["ru"] = dict(
    sub="Менеджер модов для Farming Simulator (от FS2011 до FS25), для Windows 10 и 11.",
    p1="Недостаток Farming Simulator в том, что у него только одна папка модов, в которой скапливается множество карт и модов, иногда несовместимых друг с другом. Переходить с одной игровой конфигурации на другую так хлопотно, что пропадает желание пробовать новые карты.",
    p2="Суть FS Passion — решить эту проблему с поразительной эффективностью: создавайте за несколько кликов **сборки** — наборы модов — и переключайтесь между ними одним кликом. Все ваши моды остаются в единственном экземпляре в своей исходной папке, папке Mods.",
    f=[
        "**Сборки**: карта, её зависимости и выбранные вами моды; **общие моды**, используемые всеми сборками.",
        "**Обновления**: обновления, сделанные игрой (ModHub), подхватываются и отслеживаются во всех сборках; заменённая версия откладывается в сторону, а не удаляется.",
        "**Загрузки**: новые моды обнаруживаются и переносятся в папку модов соответствующей версии игры.",
        "**Несколько дисков**: до трёх папок модов на разных дисках.",
        "**Резервная копия настроек**: экспорт и импорт сборок и настроек — для переустановки или другого ПК.",
        "**Экскурсия**: лампочка в заголовке за минуту знакомит с интерфейсом на анимированных примерах (версии, сборки, списки, множественный выбор, перетаскивание, сочетания клавиш).",
        "**Прекратить использовать FS Passion**: игра возвращает исходную настройку, папки сборок удаляются; ваши моды никогда не затрагиваются.",
        "Двухцветные **темы** и темы по мотивам популярных, тёмные и светлые ({themes}).",
        "**Демо**: приложение предназначено только для владельцев игр Farming Simulator. Если вам любопытно и вы хотите опробовать его возможности без игры, в Настройках есть демонстрационный пакет.",
    ],
    warn="⚠️ Проект в разработке (версия: см. страницу [Releases]({releases})). Перед использованием сделайте полную резервную копию папки модов. Эта страница GitHub — единственный официальный источник загрузки.",
    h_dl="Загрузка",
    dl_intro="На странице [Releases]({releases}):",
    dl_setup="установщик — для текущего пользователя без прав администратора или для всех пользователей; при необходимости устанавливает Microsoft Edge WebView2 (Windows 10);",
    dl_port="портативная версия без установки; настройки и журналы хранятся в папке `data` рядом с `FSPassion.exe`;",
    dl_sums="контрольные суммы обоих файлов.",
    dl_sign="Файлы пока не подписаны: при первом запуске Windows SmartScreen может показать предупреждение; откройте дополнительные сведения и выберите запуск приложения всё равно.",
    sign="Бесплатная подпись от SignPath Foundation запланирована после первого выпуска.",
    soon="Скоро: ещё {nsoon} языков",
    h_help="Помогите улучшить переводы",
    h_rep="Сообщить о проблеме, предложить идею",
    rep="Вкладка [Issues]({issues}). При проблеме приложите текст из «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Поддержать проект",
    sup="FS Passion был и останется надёжным, открытым и бесплатным проектом. Разовое пожертвование автору занимает несколько секунд, без создания аккаунта: [Buy Me a Coffee]({bmac}) или [пожертвование картой (Stripe)]({stripe}).",
    h_net="Подключение к Интернету",
    net="FS Passion подключается только к GitHub, чтобы прочитать каталог DLC (названия и значки, публичный репозиторий `FSPassion-data`), не чаще раза в день. Никакие личные данные не отправляются. Настройка «Internet connection» (Settings → Application) отключает это. Кроме того, при каждом запуске (затем раз в день) он проверяет на GitHub, вышла ли новая версия FS Passion: настройка «FS Passion updates» (Settings → Application) отключает это.",
    h_lic="Лицензия",
    lic="FS Passion: **GPLv3** (файл `LICENSE`), автор MichelMichel. Документация для разработчиков и полный список благодарностей (значки, шрифты, темы): [README на английском](../README.md).",
    disc="FS Passion — независимый проект, не связанный с GIANTS Software. Farming Simulator — товарный знак GIANTS Software.",
)

T["sv"] = dict(
    sub="Modhanterare för Farming Simulator (FS2011 till FS25), för Windows 10 och 11.",
    p1="Nackdelen med Farming Simulator är att det bara har en enda modmapp, där vi hamnar med många kartor och moddar som ibland inte fungerar ihop. Att byta från en spelkonfiguration till en annan är så krångligt att det håller oss tillbaka från att testa nya kartor.",
    p2="Kärnan i FS Passion löser problemet med häpnadsväckande effektivitet: skapa **uppsättningar** – samlingar av moddar – med några klick, och växla mellan dem med ett enda klick. Alla dina moddar ligger kvar i ett enda exemplar i sin ursprungliga mapp, mappen Mods.",
    f=[
        "**Uppsättningar**: en karta, dess beroenden och de moddar du väljer; **gemensamma moddar** som alla uppsättningar delar.",
        "**Uppdateringar**: de som spelet gör (ModHub) tas om hand och följs i alla uppsättningar; en ersatt version läggs åt sidan, raderas aldrig.",
        "**Nedladdningar**: nya moddar upptäcks och flyttas till modmappen för rätt spelversion.",
        "**Flera enheter**: upp till tre modmappar på olika enheter.",
        "**Säkerhetskopia av konfigurationen**: export och import av uppsättningar och inställningar, för en ominstallation eller en annan dator.",
        "**Guidad tur**: glödlampan i sidhuvudet visar gränssnittet på en minut, med animerade exempel (versioner, uppsättningar, listor, flerval, dra och släpp, kortkommandon).",
        "**Sluta använda FS Passion**: spelet får tillbaka sin ursprungliga inställning och uppsättningsmapparna tas bort; dina moddar rörs aldrig.",
        "Tvåfärgade **teman** och teman inspirerade av populära teman, mörka och ljusa ({themes}).",
        "**Demo**: programmet är endast avsett för dig som äger Farming Simulator-spelen. Är du nyfiken och vill testa funktionerna utan att äga spelet finns ett demopaket i Inställningar.",
    ],
    warn="⚠️ Projekt under utveckling (version: se sidan [Releases]({releases})). Gör en fullständig säkerhetskopia av din modmapp innan du provar. Den här GitHub-sidan är den enda officiella nedladdningsplatsen.",
    h_dl="Nedladdning",
    dl_intro="På sidan [Releases]({releases}):",
    dl_setup="installationsprogram, för den aktuella användaren utan administratörsbehörighet eller för alla användare; installerar Microsoft Edge WebView2 vid behov (Windows 10);",
    dl_port="portabel version utan installation; inställningar och loggar ligger i mappen `data` bredvid `FSPassion.exe`;",
    dl_sums="kontrollsummor för båda filerna.",
    dl_sign="Filerna är inte signerade ännu: vid första starten kan Windows SmartScreen visa en varning; öppna den ytterligare informationen och välj att köra appen ändå.",
    sign="Gratis signering av SignPath Foundation är planerad efter en första version.",
    soon="Kommer snart: {nsoon} fler språk",
    h_help="Hjälp till att förbättra översättningarna",
    h_rep="Rapportera ett problem, föreslå en idé",
    rep="Fliken [Issues]({issues}). Vid ett problem bifogar du texten från ”Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Stöd projektet",
    sup="FS Passion är och förblir ett pålitligt, öppet och gratis projekt. En engångsdonation till upphovspersonen tar några sekunder, utan konto: [Buy Me a Coffee]({bmac}) eller [donation med kort (Stripe)]({stripe}).",
    h_net="Internetanslutning",
    net="FS Passion ansluter bara till GitHub för att läsa DLC-katalogen (namn och ikoner, offentligt arkiv `FSPassion-data`), högst en gång per dag. Inga personuppgifter skickas. Inställningen ”Internet connection” (Settings → Application) stänger av det. Vid varje start (sedan en gång per dag) söker det också på GitHub efter en ny version av FS Passion: inställningen ”FS Passion updates” (Settings → Application) stänger av det.",
    h_lic="Licens",
    lic="FS Passion: **GPLv3** (filen `LICENSE`), upphovsperson MichelMichel. Dokumentation för utvecklare och alla erkännanden (ikoner, typsnitt, teman): [engelsk README](../README.md).",
    disc="FS Passion är ett oberoende projekt utan koppling till GIANTS Software. Farming Simulator är ett varumärke som tillhör GIANTS Software.",
)

T["tr"] = dict(
    sub="Farming Simulator (FS2011'den FS25'e) için mod yöneticisi, Windows 10 ve 11 için.",
    p1="Farming Simulator'ın dezavantajı, tek bir mod klasörü sunmasıdır; bu klasörde birçok harita ve bazen birbiriyle uyumsuz modlar birikir. Bir oyun yapılandırmasından diğerine geçmek o kadar zahmetlidir ki yeni haritaları denemekten vazgeçeriz.",
    p2="FS Passion'ın özü bu sorunu şaşırtıcı bir verimlilikle çözmektir: birkaç tıklamayla mod koleksiyonları olan **kurulumlar** oluşturun ve tek tıklamayla aralarında geçiş yapın. Tüm modlarınız, özgün klasörleri olan Mods klasöründe tek bir kopya olarak kalır.",
    f=[
        "**Kurulumlar**: bir harita, bağımlılıkları ve seçtiğiniz modlar; tüm kurulumların paylaştığı **ortak modlar**.",
        "**Güncellemeler**: oyunun yaptığı güncellemeler (ModHub) alınır ve tüm kurulumlarda izlenir; değiştirilen sürüm kenara ayrılır, asla silinmez.",
        "**İndirmeler**: yeni modlar algılanır ve ilgili oyun sürümünün mod klasörüne taşınır.",
        "**Birden çok sürücü**: farklı sürücülerde en fazla üç mod klasörü.",
        "**Yapılandırma yedeği**: yeniden kurulum veya başka bir bilgisayar için kurulumları ve ayarları dışa ve içe aktarma.",
        "**Rehberli tur**: başlıktaki ampul, arayüzü bir dakikada canlandırılmış örneklerle tanıtır (sürümler, kurulumlar, listeler, çoklu seçim, sürükle-bırak, klavye kısayolları).",
        "**FS Passion'ı kullanmayı bırak**: oyun özgün ayarına geri döner, kurulum klasörleri kaldırılır; modlarınıza asla dokunulmaz.",
        "İki renkli **temalar** ve popüler temalardan esinlenen koyu ve açık temalar ({themes}).",
        "**Demo**: uygulama yalnızca Farming Simulator oyunlarına sahip olanlar içindir. Merak ediyorsanız ve özellikleri oyuna sahip olmadan denemek istiyorsanız, Ayarlar'da bir tanıtım paketi bulunur.",
    ],
    warn="⚠️ Geliştirme aşamasında bir proje (sürüm: [Releases]({releases}) sayfasına bakın). Denemeden önce mod klasörünüzün tam bir yedeğini alın. Bu GitHub sayfası tek resmî indirme kaynağıdır.",
    h_dl="İndirme",
    dl_intro="[Releases]({releases}) sayfasında:",
    dl_setup="yükleyici; geçerli kullanıcı için yönetici hakları olmadan veya tüm kullanıcılar için; gerekirse Microsoft Edge WebView2'yi yükler (Windows 10);",
    dl_port="taşınabilir sürüm, kurulum gerektirmez; ayarlar ve günlükler `FSPassion.exe` yanındaki `data` klasöründe kalır;",
    dl_sums="iki dosyanın sağlama toplamları.",
    dl_sign="Dosyalar henüz imzalı değildir: ilk açılışta Windows SmartScreen bir uyarı gösterebilir; ek bilgileri açın ve uygulamayı yine de çalıştırmayı seçin.",
    sign="SignPath Foundation tarafından ücretsiz imzalama, ilk sürümden sonra planlanmaktadır.",
    soon="Yakında: {nsoon} dil daha",
    h_help="Çevirilerin geliştirilmesine yardım edin",
    h_rep="Sorun bildirin, fikir önerin",
    rep="[Issues]({issues}) sekmesi. Bir sorun için “Copy diagnostics” metnini ekleyin (Settings → Help and about → Logs and diagnostics).",
    h_sup="Projeyi destekleyin",
    sup="FS Passion güvenilir, açık kaynaklı ve ücretsiz bir projedir ve öyle kalacaktır. Yazara tek seferlik bağış birkaç saniye sürer, hesap gerekmez: [Buy Me a Coffee]({bmac}) veya [kartla bağış (Stripe)]({stripe}).",
    h_net="İnternet bağlantısı",
    net="FS Passion yalnızca DLC kataloğunu (adlar ve simgeler, herkese açık `FSPassion-data` deposu) okumak için GitHub'a bağlanır, günde en fazla bir kez. Hiçbir kişisel veri gönderilmez. “Internet connection” ayarı (Settings → Application) bunu kapatır. Ayrıca her açılışta (sonra günde bir kez) GitHub'da FS Passion'ın yeni bir sürümünü arar: “FS Passion updates” ayarı (Settings → Application) bunu kapatır.",
    h_lic="Lisans",
    lic="FS Passion: **GPLv3** (`LICENSE` dosyası), yazar MichelMichel. Geliştirici belgeleri ve tüm atıflar (simgeler, yazı tipleri, temalar): [İngilizce README](../README.md).",
    disc="FS Passion, GIANTS Software ile bağlantısı olmayan bağımsız bir projedir. Farming Simulator, GIANTS Software'in ticari markasıdır.",
)

T["uk"] = dict(
    sub="Менеджер модів для Farming Simulator (від FS2011 до FS25), для Windows 10 і 11.",
    p1="Недолік Farming Simulator у тому, що він має лише одну теку модів, де накопичується багато мап і модів, іноді несумісних між собою. Переходити з однієї ігрової конфігурації на іншу настільки клопітно, що зникає бажання пробувати нові мапи.",
    p2="Серце FS Passion — розв'язати цю проблему з дивовижною ефективністю: створюйте за кілька кліків **збірки** — набори модів — і перемикайтеся між ними одним кліком. Усі ваші моди залишаються в одному примірнику у своїй початковій теці, теці Mods.",
    f=[
        "**Збірки**: мапа, її залежності та вибрані вами моди; **спільні моди** для всіх збірок.",
        "**Оновлення**: оновлення, зроблені грою (ModHub), підхоплюються й відстежуються в усіх збірках; замінена версія відкладається, а не видаляється.",
        "**Завантаження**: нові моди виявляються й переносяться до теки модів відповідної версії гри.",
        "**Кілька дисків**: до трьох тек модів на різних дисках.",
        "**Резервна копія налаштувань**: експорт та імпорт збірок і налаштувань — для перевстановлення або іншого ПК.",
        "**Екскурсія**: лампочка в заголовку за хвилину знайомить з інтерфейсом на анімованих прикладах (версії, збірки, списки, множинний вибір, перетягування, сполучення клавіш).",
        "**Припинити користуватися FS Passion**: гра повертає початкове налаштування, теки збірок видаляються; ваших модів ніхто не торкається.",
        "Двоколірні **теми** й теми за мотивами популярних, темні та світлі ({themes}).",
        "**Демо**: застосунок призначений лише для власників ігор Farming Simulator. Якщо вам цікаво і ви хочете спробувати його можливості без гри, у Налаштуваннях є демонстраційний пакет.",
    ],
    warn="⚠️ Проєкт у розробці (версія: див. сторінку [Releases]({releases})). Перш ніж пробувати, зробіть повну резервну копію теки модів. Ця сторінка GitHub — єдине офіційне джерело завантаження.",
    h_dl="Завантаження",
    dl_intro="На сторінці [Releases]({releases}):",
    dl_setup="інсталятор — для поточного користувача без прав адміністратора або для всіх користувачів; за потреби встановлює Microsoft Edge WebView2 (Windows 10);",
    dl_port="портативна версія без встановлення; налаштування й журнали зберігаються в теці `data` поруч із `FSPassion.exe`;",
    dl_sums="контрольні суми обох файлів.",
    dl_sign="Файли поки не підписані: під час першого запуску Windows SmartScreen може показати попередження; відкрийте додаткові відомості й виберіть запуск застосунку попри все.",
    sign="Безкоштовне підписування від SignPath Foundation заплановано після першого випуску.",
    soon="Незабаром: ще {nsoon} мов",
    h_help="Допоможіть покращити переклади",
    h_rep="Повідомити про проблему, запропонувати ідею",
    rep="Вкладка [Issues]({issues}). Якщо є проблема, додайте текст із «Copy diagnostics» (Settings → Help and about → Logs and diagnostics).",
    h_sup="Підтримати проєкт",
    sup="FS Passion є і залишиться надійним, відкритим і безкоштовним проєктом. Разовий внесок авторові займає кілька секунд, без створення облікового запису: [Buy Me a Coffee]({bmac}) або [внесок карткою (Stripe)]({stripe}).",
    h_net="Підключення до Інтернету",
    net="FS Passion підключається лише до GitHub, щоб прочитати каталог DLC (назви й значки, публічний репозиторій `FSPassion-data`), не частіше одного разу на день. Жодні особисті дані не надсилаються. Налаштування «Internet connection» (Settings → Application) вимикає це. Крім того, під час кожного запуску (потім раз на день) він перевіряє на GitHub, чи вийшла нова версія FS Passion: налаштування «FS Passion updates» (Settings → Application) вимикає це.",
    h_lic="Ліцензія",
    lic="FS Passion: **GPLv3** (файл `LICENSE`), автор MichelMichel. Документація для розробників і повний перелік подяк (значки, шрифти, теми): [README англійською](../README.md).",
    disc="FS Passion — незалежний проєкт, не пов'язаний із GIANTS Software. Farming Simulator — торговельна марка GIANTS Software.",
)

T["vi"] = dict(
    sub="Trình quản lý mod cho Farming Simulator (FS2011 đến FS25), dành cho Windows 10 và 11.",
    p1="Nhược điểm của Farming Simulator là chỉ có một thư mục mod duy nhất, nơi chúng ta tích tụ rất nhiều bản đồ và mod đôi khi không tương thích với nhau. Việc chuyển từ cấu hình chơi này sang cấu hình khác phiền phức đến mức khiến ta ngại thử bản đồ mới.",
    p2="Cốt lõi của FS Passion là giải quyết vấn đề này với hiệu quả đáng kinh ngạc: tạo **bộ cấu hình** – tập hợp các mod – chỉ với vài cú nhấp, và chuyển đổi giữa chúng bằng một cú nhấp. Tất cả mod của bạn chỉ giữ một bản duy nhất trong thư mục gốc, thư mục Mods.",
    f=[
        "**Bộ cấu hình**: một bản đồ, các phụ thuộc của nó và các mod bạn chọn; **mod chung** dùng cho mọi bộ cấu hình.",
        "**Cập nhật**: các bản cập nhật do trò chơi thực hiện (ModHub) được tiếp nhận và theo dõi trong mọi bộ cấu hình; phiên bản bị thay thế được để riêng, không bao giờ bị xóa.",
        "**Tải xuống**: mod mới được phát hiện và chuyển vào thư mục mod của phiên bản trò chơi tương ứng.",
        "**Nhiều ổ đĩa**: tối đa ba thư mục mod trên các ổ đĩa khác nhau.",
        "**Sao lưu cấu hình**: xuất và nhập bộ cấu hình và cài đặt, khi cài lại hoặc sang máy tính khác.",
        "**Hướng dẫn tham quan**: bóng đèn ở tiêu đề giới thiệu giao diện trong một phút với ví dụ hoạt hình (phiên bản, bộ cấu hình, danh sách, chọn nhiều, kéo và thả, phím tắt).",
        "**Ngừng dùng FS Passion**: trò chơi trở lại cài đặt ban đầu, các thư mục bộ cấu hình bị gỡ bỏ; mod của bạn không bao giờ bị động đến.",
        "**Giao diện** hai màu và các giao diện lấy cảm hứng từ những chủ đề phổ biến, tối và sáng ({themes}).",
        "**Bản demo**: ứng dụng chỉ dành cho người sở hữu các trò chơi Farming Simulator. Nếu bạn tò mò và muốn thử tính năng mà không có trò chơi, có một gói trình diễn trong phần Cài đặt.",
    ],
    warn="⚠️ Dự án đang phát triển (phiên bản: xem trang [Releases]({releases})). Hãy sao lưu đầy đủ thư mục mod trước khi dùng thử. Trang GitHub này là nguồn tải xuống chính thức duy nhất.",
    h_dl="Tải xuống",
    dl_intro="Trên trang [Releases]({releases}):",
    dl_setup="trình cài đặt, cho người dùng hiện tại mà không cần quyền quản trị hoặc cho mọi người dùng; cài Microsoft Edge WebView2 nếu cần (Windows 10);",
    dl_port="phiên bản di động, không cần cài đặt; cài đặt và nhật ký nằm trong thư mục `data` cạnh `FSPassion.exe`;",
    dl_sums="mã kiểm tra của hai tệp.",
    dl_sign="Các tệp chưa được ký số: ở lần mở đầu tiên, Windows SmartScreen có thể hiện cảnh báo; hãy mở thông tin bổ sung và chọn vẫn chạy ứng dụng.",
    sign="Việc ký số miễn phí của SignPath Foundation được dự kiến sau bản phát hành đầu tiên.",
    soon="Sắp có: thêm {nsoon} ngôn ngữ",
    h_help="Giúp cải thiện bản dịch",
    h_rep="Báo lỗi, đề xuất ý tưởng",
    rep="Thẻ [Issues]({issues}). Khi gặp lỗi, hãy đính kèm nội dung của “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Ủng hộ dự án",
    sup="FS Passion là và sẽ luôn là một dự án đáng tin cậy, mã nguồn mở và miễn phí. Một lần ủng hộ tác giả chỉ mất vài giây, không cần tạo tài khoản: [Buy Me a Coffee]({bmac}) hoặc [ủng hộ bằng thẻ (Stripe)]({stripe}).",
    h_net="Kết nối Internet",
    net="FS Passion chỉ kết nối với GitHub để đọc danh mục DLC (tên và biểu tượng, kho công khai `FSPassion-data`), tối đa một lần mỗi ngày. Không có dữ liệu cá nhân nào được gửi đi. Cài đặt “Internet connection” (Settings → Application) sẽ tắt tính năng này. Ngoài ra, mỗi lần khởi động (sau đó mỗi ngày một lần), ứng dụng kiểm tra trên GitHub xem có phiên bản FS Passion mới không: cài đặt “FS Passion updates” (Settings → Application) sẽ tắt tính năng này.",
    h_lic="Giấy phép",
    lic="FS Passion: **GPLv3** (tệp `LICENSE`), tác giả MichelMichel. Tài liệu cho nhà phát triển và đầy đủ ghi công (biểu tượng, phông chữ, giao diện): [README tiếng Anh](../README.md).",
    disc="FS Passion là một dự án độc lập, không liên kết với GIANTS Software. Farming Simulator là nhãn hiệu của GIANTS Software.",
)

T["id"] = dict(
    sub="Pengelola mod untuk Farming Simulator (FS2011 hingga FS25), untuk Windows 10 dan 11.",
    p1="Kekurangan Farming Simulator adalah hanya menyediakan satu folder mod, tempat kita akhirnya menumpuk banyak peta dan mod yang kadang tidak cocok satu sama lain. Berpindah dari satu konfigurasi permainan ke konfigurasi lain begitu merepotkan sehingga kita enggan mencoba peta baru.",
    p2="Inti dari FS Passion adalah menyelesaikan masalah ini dengan efisiensi yang mengejutkan: buat **konfigurasi** — kumpulan mod — dalam beberapa klik, lalu beralih di antaranya dengan satu klik. Semua mod Anda tetap satu salinan di folder aslinya, folder Mods.",
    f=[
        "**Konfigurasi**: sebuah peta, dependensinya, dan mod pilihan Anda; **mod bersama** yang dipakai semua konfigurasi.",
        "**Pembaruan**: pembaruan yang dilakukan game (ModHub) diambil dan diikuti di semua konfigurasi; versi yang diganti disisihkan, tidak pernah dihapus.",
        "**Unduhan**: mod baru dikenali dan dipindahkan ke folder mod versi game yang sesuai.",
        "**Beberapa drive**: hingga tiga folder mod di drive yang berbeda.",
        "**Cadangan konfigurasi**: ekspor dan impor konfigurasi serta pengaturan, untuk instal ulang atau PC lain.",
        "**Tur terpandu**: bola lampu di header memperkenalkan antarmuka dalam satu menit, dengan contoh beranimasi (versi, konfigurasi, daftar, pilihan ganda, seret dan lepas, pintasan keyboard).",
        "**Berhenti memakai FS Passion**: game mendapatkan kembali pengaturan aslinya dan folder konfigurasi dihapus; mod Anda tidak pernah disentuh.",
        "**Tema** dua warna dan tema yang terinspirasi tema populer, gelap dan terang ({themes}).",
        "**Demo**: aplikasi ini hanya ditujukan bagi pemilik game Farming Simulator. Jika Anda penasaran dan ingin mencoba fiturnya tanpa memiliki game, tersedia paket demo di Pengaturan.",
    ],
    warn="⚠️ Proyek masih dalam pengembangan (versi: lihat halaman [Releases]({releases})). Buat cadangan lengkap folder mod Anda sebelum mencobanya. Halaman GitHub ini adalah satu-satunya sumber unduhan resmi.",
    h_dl="Unduh",
    dl_intro="Di halaman [Releases]({releases}):",
    dl_setup="penginstal, untuk pengguna saat ini tanpa hak administrator atau untuk semua pengguna; menginstal Microsoft Edge WebView2 bila perlu (Windows 10);",
    dl_port="versi portabel, tanpa instalasi; pengaturan dan log tetap di folder `data` di samping `FSPassion.exe`;",
    dl_sums="checksum kedua file.",
    dl_sign="File belum ditandatangani: saat pertama dijalankan, Windows SmartScreen mungkin menampilkan peringatan; buka informasi tambahan, lalu pilih untuk tetap menjalankan aplikasi.",
    sign="Penandatanganan gratis oleh SignPath Foundation direncanakan setelah rilis pertama.",
    soon="Segera hadir: {nsoon} bahasa lagi",
    h_help="Bantu meningkatkan terjemahan",
    h_rep="Laporkan masalah, usulkan ide",
    rep="Tab [Issues]({issues}). Untuk masalah, lampirkan teks dari “Copy diagnostics” (Settings → Help and about → Logs and diagnostics).",
    h_sup="Dukung proyek ini",
    sup="FS Passion adalah dan akan tetap menjadi proyek yang tepercaya, sumber terbuka, dan gratis. Donasi sekali untuk pembuatnya hanya butuh beberapa detik, tanpa membuat akun: [Buy Me a Coffee]({bmac}) atau [donasi dengan kartu (Stripe)]({stripe}).",
    h_net="Koneksi internet",
    net="FS Passion hanya terhubung ke GitHub untuk membaca katalog DLC (nama dan ikon, repositori publik `FSPassion-data`), paling banyak sekali sehari. Tidak ada data pribadi yang dikirim. Pengaturan “Internet connection” (Settings → Application) mematikannya. Selain itu, setiap kali dijalankan (lalu sekali sehari), FS Passion memeriksa versi baru di GitHub: pengaturan “FS Passion updates” (Settings → Application) mematikannya.",
    h_lic="Lisensi",
    lic="FS Passion: **GPLv3** (file `LICENSE`), pembuat MichelMichel. Dokumentasi pengembang dan kredit lengkap (ikon, font, tema): [README bahasa Inggris](../README.md).",
    disc="FS Passion adalah proyek independen, tidak berafiliasi dengan GIANTS Software. Farming Simulator adalah merek dagang GIANTS Software.",
)

T["ja"] = dict(
    sub="Farming Simulator（FS2011〜FS25）用の MOD マネージャー。Windows 10・11 対応。",
    p1="Farming Simulator の弱点は、MOD フォルダーが 1 つしかないことです。そこには多くのマップや、ときには互いに相性の悪い MOD がたまっていきます。ゲーム構成を切り替えるのが面倒なため、新しいマップを試す気になれません。",
    p2="FS Passion の中心は、この問題を驚くほど効率よく解決することです。数クリックで MOD の集まりである **構成** を作り、ワンクリックで切り替えられます。すべての MOD は元のフォルダー（Mods フォルダー）に 1 つだけ置かれたままです。",
    f=[
        "**構成**：マップ、その依存 MOD、選んだ MOD。すべての構成で共有する **共通 MOD**。",
        "**アップデート**：ゲームが行った更新（ModHub）を取り込み、すべての構成に反映します。置き換えられたバージョンは削除せず、別に保管します。",
        "**ダウンロード**：新しい MOD を検出し、対応するゲームバージョンの MOD フォルダーに移動します。",
        "**複数ドライブ**：異なるドライブ上の MOD フォルダーを最大 3 つまで。",
        "**設定のバックアップ**：構成と設定のエクスポート・インポート。再インストールや別の PC に。",
        "**ガイドツアー**：ヘッダーの電球が、アニメーション付きの例（バージョン、構成、リスト、複数選択、ドラッグ＆ドロップ、キーボードショートカット）で 1 分で画面を紹介します。",
        "**FS Passion の使用をやめる**：ゲームは元の設定に戻り、構成フォルダーは削除されます。MOD 自体には一切手を触れません。",
        "2 色の **テーマ** と、人気テーマに着想を得たダーク・ライトのテーマ（{themes}）。",
        "**デモ**：このアプリは Farming Simulator シリーズの所有者向けです。ゲームを持っていなくても機能を試したい方のために、設定にデモパックがあります。",
    ],
    warn="⚠️ 開発中のプロジェクトです（バージョン：[Releases]({releases}) ページを参照）。試す前に MOD フォルダーを完全にバックアップしてください。公式のダウンロード先はこの GitHub ページだけです。",
    h_dl="ダウンロード",
    dl_intro="[Releases]({releases}) ページから：",
    dl_setup="インストーラー。管理者権限なしで現在のユーザーに、またはすべてのユーザーにインストールできます。必要に応じて Microsoft Edge WebView2 をインストールします（Windows 10）。",
    dl_port="ポータブル版。インストール不要で、設定とログは `FSPassion.exe` の隣の `data` フォルダーに保存されます。",
    dl_sums="2 つのファイルのチェックサム。",
    dl_sign="ファイルにはまだ署名がありません。初回起動時に Windows SmartScreen が警告を表示することがあります。詳細情報を開き、そのまま実行を選んでください。",
    sign="SignPath Foundation による無償の署名は、最初のリリースの後に予定されています。",
    soon="近日対応: さらに {nsoon} 言語",
    h_help="翻訳の改善にご協力ください",
    h_rep="問題の報告・アイデアの提案",
    rep="[Issues]({issues}) タブへ。問題の報告には「Copy diagnostics」（Settings → Help and about → Logs and diagnostics）のテキストを添付してください。",
    h_sup="プロジェクトを支援する",
    sup="FS Passion は信頼できる、オープンソースで無料のプロジェクトであり、これからもそうあり続けます。作者への単発の寄付は、アカウント作成なしで数秒で済みます：[Buy Me a Coffee]({bmac}) または [カードでの寄付（Stripe）]({stripe})。",
    h_net="インターネット接続",
    net="FS Passion が接続するのは GitHub だけで、DLC カタログ（名前とアイコン、公開リポジトリ `FSPassion-data`）を 1 日に最大 1 回読み込みます。個人データは送信されません。「Internet connection」設定（Settings → Application）でオフにできます。また、起動するたびに（その後は 1 日 1 回）GitHub で FS Passion の新しいバージョンを確認します。「FS Passion updates」設定（Settings → Application）でオフにできます。",
    h_lic="ライセンス",
    lic="FS Passion：**GPLv3**（`LICENSE` ファイル）、作者 MichelMichel。開発者向けドキュメントとすべてのクレジット（アイコン、フォント、テーマ）：[英語版 README](../README.md)。",
    disc="FS Passion は GIANTS Software とは関係のない独立したプロジェクトです。Farming Simulator は GIANTS Software の商標です。",
)

T["ko"] = dict(
    sub="Farming Simulator(FS2011~FS25)용 모드 관리자, Windows 10 및 11용.",
    p1="Farming Simulator의 단점은 모드 폴더가 하나뿐이라는 것입니다. 그 안에 수많은 맵과 때로는 서로 호환되지 않는 모드가 쌓입니다. 게임 구성을 바꾸는 일이 너무 번거로워 새로운 맵을 시도하기가 망설여집니다.",
    p2="FS Passion의 핵심은 이 문제를 놀라울 만큼 효율적으로 해결하는 것입니다. 몇 번의 클릭으로 모드 모음인 **구성**을 만들고, 한 번의 클릭으로 서로 전환하세요. 모든 모드는 원래 폴더인 Mods 폴더에 하나씩만 남습니다.",
    f=[
        "**구성**: 맵, 그 의존성, 그리고 원하는 모드; 모든 구성이 함께 쓰는 **공통 모드**.",
        "**업데이트**: 게임이 수행한 업데이트(ModHub)를 가져와 모든 구성에 반영합니다. 교체된 버전은 지우지 않고 따로 보관합니다.",
        "**다운로드**: 새 모드를 감지하여 해당 게임 버전의 모드 폴더로 옮깁니다.",
        "**여러 드라이브**: 서로 다른 드라이브에 최대 세 개의 모드 폴더.",
        "**설정 백업**: 재설치나 다른 PC를 위해 구성과 설정을 내보내고 가져옵니다.",
        "**가이드 투어**: 헤더의 전구가 애니메이션 예시(버전, 구성, 목록, 다중 선택, 끌어서 놓기, 단축키)로 1분 만에 인터페이스를 소개합니다.",
        "**FS Passion 사용 중지**: 게임이 원래 설정으로 돌아가고 구성 폴더가 제거됩니다. 모드는 절대 건드리지 않습니다.",
        "2색 **테마**와 인기 테마에서 영감을 받은 다크·라이트 테마({themes}).",
        "**데모**: 이 앱은 Farming Simulator 게임 소유자만을 위한 것입니다. 게임 없이 기능을 체험해 보고 싶다면 설정에서 데모 팩을 이용할 수 있습니다.",
    ],
    warn="⚠️ 개발 중인 프로젝트입니다(버전: [Releases]({releases}) 페이지 참고). 사용해 보기 전에 모드 폴더를 완전히 백업하세요. 공식 다운로드 위치는 이 GitHub 페이지뿐입니다.",
    h_dl="다운로드",
    dl_intro="[Releases]({releases}) 페이지에서:",
    dl_setup="설치 프로그램 — 관리자 권한 없이 현재 사용자용으로, 또는 모든 사용자용으로 설치합니다. 필요하면 Microsoft Edge WebView2를 설치합니다(Windows 10).",
    dl_port="포터블 버전 — 설치가 필요 없으며, 설정과 로그는 `FSPassion.exe` 옆의 `data` 폴더에 저장됩니다.",
    dl_sums="두 파일의 체크섬.",
    dl_sign="파일은 아직 서명되지 않았습니다. 처음 실행할 때 Windows SmartScreen이 경고를 표시할 수 있습니다. 추가 정보를 열고 그래도 실행을 선택하세요.",
    sign="SignPath Foundation의 무료 서명은 첫 번째 릴리스 이후에 예정되어 있습니다.",
    soon="곧 추가: {nsoon}개 언어 더",
    h_help="번역 개선에 도움 주기",
    h_rep="문제 신고, 아이디어 제안",
    rep="[Issues]({issues}) 탭. 문제를 신고할 때는 “Copy diagnostics”(Settings → Help and about → Logs and diagnostics)의 텍스트를 첨부해 주세요.",
    h_sup="프로젝트 후원",
    sup="FS Passion은 신뢰할 수 있는 무료 오픈 소스 프로젝트이며 앞으로도 그럴 것입니다. 계정을 만들지 않고도 몇 초 만에 작성자에게 일회성 후원을 할 수 있습니다: [Buy Me a Coffee]({bmac}) 또는 [카드 후원(Stripe)]({stripe}).",
    h_net="인터넷 연결",
    net="FS Passion은 DLC 카탈로그(이름과 아이콘, 공개 저장소 `FSPassion-data`)를 읽기 위해 GitHub에만 하루 최대 한 번 연결합니다. 개인 데이터는 전송되지 않습니다. “Internet connection” 설정(Settings → Application)으로 끌 수 있습니다. 또한 실행할 때마다(이후 하루 한 번) GitHub에서 FS Passion의 새 버전을 확인합니다. “FS Passion updates” 설정(Settings → Application)으로 끌 수 있습니다.",
    h_lic="라이선스",
    lic="FS Passion: **GPLv3**(`LICENSE` 파일), 작성자 MichelMichel. 개발자 문서와 전체 크레딧(아이콘, 글꼴, 테마): [영어 README](../README.md).",
    disc="FS Passion은 GIANTS Software와 무관한 독립 프로젝트입니다. Farming Simulator는 GIANTS Software의 상표입니다.",
)

T["zh-Hans"] = dict(
    sub="Farming Simulator（FS2011 至 FS25）模组管理器，适用于 Windows 10 和 11。",
    p1="Farming Simulator 的不足在于只有一个模组文件夹，里面堆积了大量地图和有时互不兼容的模组。在不同游戏配置之间切换太过麻烦，让人懒得尝试新地图。",
    p2="FS Passion 的核心就是以惊人的效率解决这个问题：点几下即可创建**配置**——也就是模组合集——并一键在它们之间切换。你的所有模组都只在原始文件夹（Mods 文件夹）中保留一份。",
    f=[
        "**配置**：一张地图、它的依赖项以及你选择的模组；所有配置共享的**公共模组**。",
        "**更新**：游戏执行的更新（ModHub）会被接收并同步到所有配置；被替换的版本会另行保存，绝不删除。",
        "**下载**：自动发现新模组，并移入对应游戏版本的模组文件夹。",
        "**多个硬盘**：最多三个位于不同硬盘上的模组文件夹。",
        "**配置备份**：导出和导入配置与设置，便于重装或换电脑。",
        "**导览**：标题栏的灯泡用一分钟介绍界面，配有动画示例（版本、配置、列表、多选、拖放、键盘快捷键）。",
        "**停止使用 FS Passion**：游戏恢复原始设置，配置文件夹被移除；你的模组绝不会被改动。",
        "双色**主题**，以及受流行主题启发的深色和浅色主题（{themes}）。",
        "**演示**：本应用仅面向 Farming Simulator 游戏的拥有者。如果你感到好奇，想在没有游戏的情况下试用功能，可以在设置中使用演示包。",
    ],
    warn="⚠️ 项目仍在开发中（版本：见 [Releases]({releases}) 页面）。试用前请完整备份你的模组文件夹。此 GitHub 页面是唯一的官方下载地址。",
    h_dl="下载",
    dl_intro="在 [Releases]({releases}) 页面：",
    dl_setup="安装程序：可为当前用户安装（无需管理员权限），也可为所有用户安装；如有需要会安装 Microsoft Edge WebView2（Windows 10）；",
    dl_port="便携版：无需安装；设置和日志保存在 `FSPassion.exe` 旁边的 `data` 文件夹中；",
    dl_sums="两个文件的校验和。",
    dl_sign="文件尚未签名：首次启动时，Windows SmartScreen 可能会显示警告；请打开更多信息，然后选择仍要运行。",
    sign="SignPath Foundation 提供的免费签名计划在首次发布之后进行。",
    soon="即将推出：另外 {nsoon} 种语言",
    h_help="帮助改进翻译",
    h_rep="报告问题、提出建议",
    rep="请前往 [Issues]({issues}) 标签页。报告问题时，请附上“Copy diagnostics”（Settings → Help and about → Logs and diagnostics）中的文本。",
    h_sup="支持本项目",
    sup="FS Passion 是并将始终是一个值得信赖、开源且免费的项目。向作者一次性捐赠只需几秒钟，无需注册账户：[Buy Me a Coffee]({bmac}) 或 [银行卡捐赠（Stripe）]({stripe})。",
    h_net="网络连接",
    net="FS Passion 只连接 GitHub，用于读取 DLC 目录（名称和图标，公开仓库 `FSPassion-data`），每天最多一次。不会发送任何个人数据。“Internet connection”设置（Settings → Application）可将其关闭。此外，每次启动时（之后每天一次）会在 GitHub 上检查 FS Passion 是否有新版本。“FS Passion updates”设置（Settings → Application）可将其关闭。",
    h_lic="许可证",
    lic="FS Passion：**GPLv3**（`LICENSE` 文件），作者 MichelMichel。开发者文档和完整致谢（图标、字体、主题）：[英文 README](../README.md)。",
    disc="FS Passion 是独立项目，与 GIANTS Software 无关。Farming Simulator 是 GIANTS Software 的商标。",
)

T["zh-Hant"] = dict(
    sub="Farming Simulator（FS2011 至 FS25）模組管理器，適用於 Windows 10 和 11。",
    p1="Farming Simulator 的缺點是只有一個模組資料夾，裡面堆積了大量地圖和有時互不相容的模組。在不同遊戲配置之間切換太過麻煩，讓人懶得嘗試新地圖。",
    p2="FS Passion 的核心就是以驚人的效率解決這個問題：點幾下即可建立**配置**——也就是模組合集——並一鍵在它們之間切換。你的所有模組都只在原始資料夾（Mods 資料夾）中保留一份。",
    f=[
        "**配置**：一張地圖、它的相依項目以及你選擇的模組；所有配置共用的**共通模組**。",
        "**更新**：遊戲執行的更新（ModHub）會被接收並同步到所有配置；被取代的版本會另行保存，絕不刪除。",
        "**下載**：自動偵測新模組，並移入對應遊戲版本的模組資料夾。",
        "**多個磁碟**：最多三個位於不同磁碟上的模組資料夾。",
        "**配置備份**：匯出和匯入配置與設定，方便重新安裝或換電腦。",
        "**導覽**：標題列的燈泡用一分鐘介紹介面，搭配動畫範例（版本、配置、清單、多選、拖放、鍵盤快速鍵）。",
        "**停止使用 FS Passion**：遊戲恢復原始設定，配置資料夾會被移除；你的模組絕不會被更動。",
        "雙色**主題**，以及受熱門主題啟發的深色與淺色主題（{themes}）。",
        "**示範**：本應用程式僅供 Farming Simulator 遊戲的擁有者使用。如果你感到好奇，想在沒有遊戲的情況下試用功能，可以在設定中使用示範套件。",
    ],
    warn="⚠️ 專案仍在開發中（版本：見 [Releases]({releases}) 頁面）。試用前請完整備份你的模組資料夾。此 GitHub 頁面是唯一的官方下載位置。",
    h_dl="下載",
    dl_intro="在 [Releases]({releases}) 頁面：",
    dl_setup="安裝程式：可為目前使用者安裝（不需系統管理員權限），也可為所有使用者安裝；必要時會安裝 Microsoft Edge WebView2（Windows 10）；",
    dl_port="可攜版：免安裝；設定與記錄保存在 `FSPassion.exe` 旁的 `data` 資料夾中；",
    dl_sums="兩個檔案的總和檢查碼。",
    dl_sign="檔案尚未簽署：首次啟動時，Windows SmartScreen 可能會顯示警告；請開啟其他資訊，然後選擇仍要執行。",
    sign="SignPath Foundation 提供的免費簽署計畫在首次發布之後進行。",
    soon="即將推出：另外 {nsoon} 種語言",
    h_help="協助改進翻譯",
    h_rep="回報問題、提出建議",
    rep="請前往 [Issues]({issues}) 分頁。回報問題時，請附上「Copy diagnostics」（Settings → Help and about → Logs and diagnostics）中的文字。",
    h_sup="支持本專案",
    sup="FS Passion 是且將始終是值得信賴、開源且免費的專案。向作者單次捐款只需幾秒鐘，無須註冊帳號：[Buy Me a Coffee]({bmac}) 或 [信用卡捐款（Stripe）]({stripe})。",
    h_net="網路連線",
    net="FS Passion 只連線到 GitHub，用於讀取 DLC 目錄（名稱和圖示，公開儲存庫 `FSPassion-data`），每天最多一次。不會傳送任何個人資料。「Internet connection」設定（Settings → Application）可將其關閉。此外，每次啟動時（之後每天一次）會在 GitHub 上檢查 FS Passion 是否有新版本。「FS Passion updates」設定（Settings → Application）可將其關閉。",
    h_lic="授權",
    lic="FS Passion：**GPLv3**（`LICENSE` 檔案），作者 MichelMichel。開發者文件與完整致謝（圖示、字型、主題）：[英文 README](../README.md)。",
    disc="FS Passion 是獨立專案，與 GIANTS Software 無關。Farming Simulator 是 GIANTS Software 的商標。",
)


# Captures d'écran (assets/screenshots/, dans l'ordre de SHOT_FILES) et section
# « Aider à améliorer les traductions » en entier. Clés : h_shots, shots
# (6 légendes), help (introduction), s1 à s6 (étapes), s2a et s2b (sous-points
# de l'étape 2). Repères remplacés par render() : {code} et {lname} (code et
# nom de la langue du README), {open_folder}, {lang_path}, {personal}
# (libellés de l'interface, en anglais si elle n'existe pas dans cette
# langue), {p_inst} et {p_port} (chemins), {issues}. `{{count}}` s'affiche
# `{count}`.
SHOT_FILES = ["1-all-mods", "2-setups", "3-preview", "4-themes-languages", "5-several-drives", "6-settings"]

HELP: dict[str, dict] = {}

HELP["de"] = dict(
    h_shots="Screenshots",
    shots=[
        "Alle Mods einer Spielversion, Infokarte und Mehrfachauswahl",
        "Setups: Wechsel mit einem Klick (helles Design, französische Oberfläche)",
        "Große Vorschau beim Überfahren mit der Maus (FS22, Design Synthwave '84)",
        "Designs und Sprachen (polnische Oberfläche)",
        "Mod-Ordner auf mehreren Laufwerken",
        "Einstellungen: Infobereich, Internetverbindung, Sicherung (portugiesische Oberfläche)",
    ],
    help='''Die Übersetzungen sind eine erste Fassung: Korrekturen von Muttersprachlern sind sehr willkommen, für die aktuellen und für die kommenden Sprachen. Programmierkenntnisse sind nicht nötig, nur ein Texteditor (der Windows-Editor genügt).''',
    s1='''Öffne in diesem Repository den Ordner [`lang`](../lang/) und lade die Datei deiner Sprache herunter (`{code}.json`). Ist sie noch nicht vorhanden, lade `en.json` herunter.''',
    s2='''Lege sie in den Ordner der persönlichen Sprachen deiner FS-Passion-Installation (die Schaltfläche **{open_folder}** unter {lang_path} öffnet ihn):''',
    s2a='''installierte Version: {p_inst};''',
    s2b='''portable Version: {p_port} neben `FSPassion.exe`.''',
    s3='''Benenne sie um, zum Beispiel in `{code}_corrected.json` (der Name darf nicht mit `_` beginnen). Ändere die Zeile `"code"` oben in der Datei nicht: Deine Datei ersetzt dann die mitgelieferte Sprache. Wenn du von `en.json` ausgehst: Schreibe `"{code}"` in die Zeile `"code"` und `"{lname}"` in die Zeile `"name"`.''',
    s4='''Korrigiere die Texte in Anführungszeichen rechts der `:`-Zeichen und speichere die Datei (Kodierung UTF-8). Lass die Schlüssel links und die Wörter in geschweiften Klammern wie `{{count}}` unverändert.''',
    s5='''Starte FS Passion neu und wähle deine Sprache unter {lang_path}: Sie ist als „{personal}“ markiert. Prüfe deine Korrekturen in der Oberfläche.''',
    s6='''Sende die korrigierte Datei im Reiter [Issues]({issues}): Erstelle ein Issue, zum Beispiel mit dem Titel „Translation: {lname}“, und hänge die Datei an (als ZIP, falls GitHub die Endung `.json` ablehnt).''',
)

HELP["es"] = dict(
    h_shots="Capturas de pantalla",
    shots=[
        "Todos los mods de una versión del juego, ficha de información y selección múltiple",
        "Partidas: cambio en un clic (tema claro, interfaz en francés)",
        "Vista previa grande al pasar el ratón (FS22, tema Synthwave '84)",
        "Temas e idiomas (interfaz en polaco)",
        "Carpetas de mods en varios discos",
        "Ajustes: área de notificación, conexión a Internet, copia de seguridad (interfaz en portugués)",
    ],
    help='''Las traducciones son una primera versión: las correcciones de hablantes nativos son muy bienvenidas, para los idiomas actuales y para los que vienen. No hace falta saber programar, solo un editor de texto (el Bloc de notas sirve).''',
    s1='''En este repositorio, abre la carpeta [`lang`](../lang/) y descarga el archivo de tu idioma (`{code}.json`). Si aún no está, descarga `en.json`.''',
    s2='''Ponlo en la carpeta de idiomas personales de tu instalación de FS Passion (la abre el botón **{open_folder}**, en {lang_path}):''',
    s2a='''versión instalada: {p_inst};''',
    s2b='''versión portátil: {p_port}, junto a `FSPassion.exe`.''',
    s3='''Cámbiale el nombre, por ejemplo `{code}_corrected.json` (el nombre no debe empezar por `_`). No cambies la línea `"code"` del principio del archivo: así tu archivo sustituye al idioma incluido. Si partes de `en.json`: escribe `"{code}"` en la línea `"code"` y `"{lname}"` en la línea `"name"`.''',
    s4='''Corrige los textos entre comillas, a la derecha de los signos `:`, y guarda el archivo (codificación UTF-8). No toques las claves de la izquierda ni las palabras entre llaves como `{{count}}`.''',
    s5='''Reinicia FS Passion y elige tu idioma en {lang_path}: aparece marcado como «{personal}». Comprueba tus correcciones en la interfaz.''',
    s6='''Envía el archivo corregido en la pestaña [Issues]({issues}): crea un issue con un título como «Translation: {lname}» y adjunta el archivo (comprímelo en ZIP si GitHub rechaza la extensión `.json`).''',
)

HELP["es-419"] = dict(
    h_shots="Capturas de pantalla",
    shots=[
        "Todos los mods de una versión del juego, ficha de información y selección múltiple",
        "Partidas: cambio en un clic (tema claro, interfaz en francés)",
        "Vista previa grande al pasar el mouse (FS22, tema Synthwave '84)",
        "Temas e idiomas (interfaz en polaco)",
        "Carpetas de mods en varios discos",
        "Configuración: área de notificación, conexión a Internet, respaldo (interfaz en portugués)",
    ],
    help='''Las traducciones son una primera versión: las correcciones de hablantes nativos son muy bienvenidas, para los idiomas actuales y para los que vienen. No se necesita saber programar, solo un editor de texto (el Bloc de notas funciona).''',
    s1='''En este repositorio, abre la carpeta [`lang`](../lang/) y descarga el archivo de tu idioma (`{code}.json`). Si todavía no está, descarga `es.json` (o `en.json`).''',
    s2='''Colócalo en la carpeta de idiomas personales de tu instalación de FS Passion (la abre el botón **{open_folder}**, en {lang_path}):''',
    s2a='''versión instalada: {p_inst};''',
    s2b='''versión portátil: {p_port}, junto a `FSPassion.exe`.''',
    s3='''Cámbiale el nombre, por ejemplo `{code}_corrected.json` (el nombre no debe comenzar con `_`). No modifiques la línea `"code"` del inicio del archivo: así tu archivo reemplaza al idioma incluido. Si partes de otro archivo (`es.json` o `en.json`): escribe `"{code}"` en la línea `"code"` y `"{lname}"` en la línea `"name"`.''',
    s4='''Corrige los textos entre comillas, a la derecha de los signos `:`, y guarda el archivo (codificación UTF-8). No modifiques las claves de la izquierda ni las palabras entre llaves como `{{count}}`.''',
    s5='''Reinicia FS Passion y selecciona tu idioma en {lang_path}: aparece marcado como «{personal}». Revisa tus correcciones en la interfaz.''',
    s6='''Envía el archivo corregido en la pestaña [Issues]({issues}): crea un issue con un título como «Translation: {lname}» y adjunta el archivo (comprímelo en ZIP si GitHub no acepta la extensión `.json`).''',
)

HELP["it"] = dict(
    h_shots="Schermate",
    shots=[
        "Tutte le mod di una versione del gioco, scheda informativa e selezione multipla",
        "Partite: si cambia con un clic (tema chiaro, interfaccia in francese)",
        "Anteprima grande al passaggio del mouse (FS22, tema Synthwave '84)",
        "Temi e lingue (interfaccia in polacco)",
        "Cartelle delle mod su più dischi",
        "Impostazioni: area di notifica, connessione a Internet, backup (interfaccia in portoghese)",
    ],
    help='''Le traduzioni sono una prima versione: le correzioni dei madrelingua sono molto gradite, per le lingue attuali e per quelle in arrivo. Non serve saper programmare, basta un editor di testo (va bene il Blocco note).''',
    s1='''In questo repository, apri la cartella [`lang`](../lang/) e scarica il file della tua lingua (`{code}.json`). Se non c'è ancora, scarica `en.json`.''',
    s2='''Mettilo nella cartella delle lingue personali della tua installazione di FS Passion (la apre il pulsante **{open_folder}**, in {lang_path}):''',
    s2a='''versione installata: {p_inst};''',
    s2b='''versione portatile: {p_port}, accanto a `FSPassion.exe`.''',
    s3='''Rinominalo, per esempio `{code}_corrected.json` (il nome non deve iniziare con `_`). Non modificare la riga `"code"` all'inizio del file: così il tuo file sostituisce la lingua inclusa. Se parti da `en.json`: scrivi `"{code}"` nella riga `"code"` e `"{lname}"` nella riga `"name"`.''',
    s4='''Correggi i testi tra virgolette, a destra dei segni `:`, e salva il file (codifica UTF-8). Lascia invariate le chiavi a sinistra e le parole tra parentesi graffe come `{{count}}`.''',
    s5='''Riavvia FS Passion e scegli la tua lingua in {lang_path}: è contrassegnata come «{personal}». Controlla le tue correzioni nell'interfaccia.''',
    s6='''Invia il file corretto nella scheda [Issues]({issues}): crea una issue con un titolo come «Translation: {lname}» e allega il file (in uno ZIP se GitHub rifiuta l'estensione `.json`).''',
)

HELP["pt-BR"] = dict(
    h_shots="Capturas de tela",
    shots=[
        "Todos os mods de uma versão do jogo, ficha de informações e seleção múltipla",
        "Partidas: troca com um clique (tema claro, interface em francês)",
        "Prévia grande ao passar o mouse (FS22, tema Synthwave '84)",
        "Temas e idiomas (interface em polonês)",
        "Pastas de mods em vários discos",
        "Configurações: área de notificação, conexão com a Internet, backup (interface em português)",
    ],
    help='''As traduções são uma primeira versão: correções de falantes nativos são muito bem-vindas, para os idiomas atuais e para os que estão chegando. Não é preciso saber programar, só um editor de texto (o Bloco de Notas serve).''',
    s1='''Neste repositório, abra a pasta [`lang`](../lang/) e baixe o arquivo do seu idioma (`{code}.json`). Se ele ainda não existir, baixe `en.json`.''',
    s2='''Coloque-o na pasta de idiomas pessoais da sua instalação do FS Passion (o botão **{open_folder}**, em {lang_path}, abre essa pasta):''',
    s2a='''versão instalada: {p_inst};''',
    s2b='''versão portátil: {p_port}, ao lado de `FSPassion.exe`.''',
    s3='''Renomeie-o, por exemplo `{code}_corrected.json` (o nome não pode começar com `_`). Não altere a linha `"code"` no início do arquivo: assim o seu arquivo substitui o idioma incluído. Se você partiu de `en.json`: escreva `"{code}"` na linha `"code"` e `"{lname}"` na linha `"name"`.''',
    s4='''Corrija os textos entre aspas, à direita dos sinais `:`, e salve o arquivo (codificação UTF-8). Não altere as chaves à esquerda nem as palavras entre chaves como `{{count}}`.''',
    s5='''Reinicie o FS Passion e escolha o seu idioma em {lang_path}: ele aparece marcado como “{personal}”. Confira suas correções na interface.''',
    s6='''Envie o arquivo corrigido na aba [Issues]({issues}): crie uma issue com um título como “Translation: {lname}” e anexe o arquivo (compacte em ZIP se o GitHub recusar a extensão `.json`).''',
)

HELP["pt-PT"] = dict(
    h_shots="Capturas de ecrã",
    shots=[
        "Todos os mods de uma versão do jogo, ficha de informações e seleção múltipla",
        "Partidas: troca com um clique (tema claro, interface em francês)",
        "Pré-visualização grande ao passar o rato (FS22, tema Synthwave '84)",
        "Temas e idiomas (interface em polaco)",
        "Pastas de mods em vários discos",
        "Definições: área de notificação, ligação à Internet, cópia de segurança (interface em português do Brasil)",
    ],
    help='''As traduções são uma primeira versão: as correções de falantes nativos são muito bem-vindas, para os idiomas atuais e para os que aí vêm. Não são precisos conhecimentos de programação, apenas um editor de texto (o Bloco de Notas serve).''',
    s1='''Neste repositório, abra a pasta [`lang`](../lang/) e transfira o ficheiro do seu idioma (`{code}.json`). Se ainda não existir, transfira `en.json`.''',
    s2='''Coloque-o na pasta de idiomas pessoais da sua instalação do FS Passion (o botão **{open_folder}**, em {lang_path}, abre essa pasta):''',
    s2a='''versão instalada: {p_inst};''',
    s2b='''versão portátil: {p_port}, ao lado de `FSPassion.exe`.''',
    s3='''Mude-lhe o nome, por exemplo `{code}_corrected.json` (o nome não pode começar por `_`). Não altere a linha `"code"` no início do ficheiro: assim o seu ficheiro substitui o idioma incluído. Se partir de `en.json`: escreva `"{code}"` na linha `"code"` e `"{lname}"` na linha `"name"`.''',
    s4='''Corrija os textos entre aspas, à direita dos sinais `:`, e guarde o ficheiro (codificação UTF-8). Não altere as chaves à esquerda nem as palavras entre chavetas como `{{count}}`.''',
    s5='''Reinicie o FS Passion e escolha o seu idioma em {lang_path}: aparece marcado como «{personal}». Verifique as suas correções na interface.''',
    s6='''Envie o ficheiro corrigido no separador [Issues]({issues}): crie uma issue com um título como «Translation: {lname}» e anexe o ficheiro (comprima-o em ZIP se o GitHub recusar a extensão `.json`).''',
)

HELP["nl"] = dict(
    h_shots="Schermafbeeldingen",
    shots=[
        "Alle mods van een spelversie, infokaart en meervoudige selectie",
        "Setups: wisselen met één klik (licht thema, Franse interface)",
        "Grote voorvertoning bij aanwijzen met de muis (FS22, thema Synthwave '84)",
        "Thema's en talen (Poolse interface)",
        "Modmappen op meerdere schijven",
        "Instellingen: systeemvak, internetverbinding, back-up (Portugese interface)",
    ],
    help='''De vertalingen zijn een eerste versie: correcties van moedertaalsprekers zijn van harte welkom, voor de huidige talen en voor de talen die nog komen. Programmeerkennis is niet nodig, alleen een teksteditor (Kladblok volstaat).''',
    s1='''Open in deze repository de map [`lang`](../lang/) en download het bestand van je taal (`{code}.json`). Staat het er nog niet, download dan `en.json`.''',
    s2='''Zet het in de map met eigen talen van je FS Passion-installatie (de knop **{open_folder}** onder {lang_path} opent die map):''',
    s2a='''geïnstalleerde versie: {p_inst};''',
    s2b='''draagbare versie: {p_port}, naast `FSPassion.exe`.''',
    s3='''Geef het een andere naam, bijvoorbeeld `{code}_corrected.json` (de naam mag niet met `_` beginnen). Wijzig de regel `"code"` bovenaan het bestand niet: je bestand vervangt dan de meegeleverde taal. Begin je met `en.json`: schrijf `"{code}"` op de regel `"code"` en `"{lname}"` op de regel `"name"`.''',
    s4='''Verbeter de teksten tussen aanhalingstekens, rechts van de `:`-tekens, en sla het bestand op (codering UTF-8). Laat de sleutels links en de woorden tussen accolades zoals `{{count}}` ongewijzigd.''',
    s5='''Start FS Passion opnieuw en kies je taal onder {lang_path}: die is gemarkeerd als „{personal}”. Controleer je correcties in de interface.''',
    s6='''Stuur het verbeterde bestand via het tabblad [Issues]({issues}): maak een issue aan met bijvoorbeeld de titel „Translation: {lname}” en voeg het bestand toe (in een ZIP als GitHub de extensie `.json` weigert).''',
)

HELP["pl"] = dict(
    h_shots="Zrzuty ekranu",
    shots=[
        "Wszystkie mody danej wersji gry, karta informacji i zaznaczanie wielu modów",
        "Zestawy: przełączanie jednym kliknięciem (jasny motyw, interfejs po francusku)",
        "Duży podgląd po najechaniu myszą (FS22, motyw Synthwave '84)",
        "Motywy i języki (interfejs po polsku)",
        "Foldery modów na kilku dyskach",
        "Ustawienia: obszar powiadomień, połączenie z Internetem, kopia zapasowa (interfejs po portugalsku)",
    ],
    help='''Tłumaczenia są pierwszą wersją: poprawki od rodzimych użytkowników języka są bardzo mile widziane, zarówno dla obecnych języków, jak i dla tych, które dopiero się pojawią. Nie trzeba umieć programować, wystarczy edytor tekstu (Notatnik w zupełności wystarczy).''',
    s1='''W tym repozytorium otwórz folder [`lang`](../lang/) i pobierz plik swojego języka (`{code}.json`). Jeśli go jeszcze nie ma, pobierz `en.json`.''',
    s2='''Umieść go w folderze własnych języków swojej instalacji FS Passion (otwiera go przycisk **{open_folder}** w {lang_path}):''',
    s2a='''wersja instalowana: {p_inst};''',
    s2b='''wersja przenośna: {p_port} obok `FSPassion.exe`.''',
    s3='''Zmień jego nazwę, na przykład na `{code}_corrected.json` (nazwa nie może zaczynać się od `_`). Nie zmieniaj wiersza `"code"` na początku pliku: wtedy twój plik zastąpi wbudowany język. Jeśli zaczynasz od `en.json`: wpisz `"{code}"` w wierszu `"code"` i `"{lname}"` w wierszu `"name"`.''',
    s4='''Popraw teksty w cudzysłowach, po prawej stronie znaków `:`, i zapisz plik (kodowanie UTF-8). Nie zmieniaj kluczy po lewej stronie ani słów w nawiasach klamrowych, takich jak `{{count}}`.''',
    s5='''Uruchom ponownie FS Passion i wybierz swój język w {lang_path}: jest oznaczony jako „{personal}”. Sprawdź swoje poprawki w interfejsie.''',
    s6='''Wyślij poprawiony plik w zakładce [Issues]({issues}): utwórz zgłoszenie zatytułowane na przykład „Translation: {lname}” i dołącz plik (spakuj go do ZIP, jeśli GitHub odrzuci rozszerzenie `.json`).''',
)

HELP["cs"] = dict(
    h_shots="Snímky obrazovky",
    shots=[
        "Všechny mody jedné verze hry, informační karta a výběr více modů",
        "Sestavy: přepnutí jedním kliknutím (světlý motiv, francouzské rozhraní)",
        "Velký náhled po najetí myší (FS22, motiv Synthwave '84)",
        "Motivy a jazyky (polské rozhraní)",
        "Složky modů na více discích",
        "Nastavení: oznamovací oblast, připojení k internetu, záloha (portugalské rozhraní)",
    ],
    help='''Překlady jsou první verzí: opravy od rodilých mluvčích jsou velmi vítány, pro současné i pro připravované jazyky. Nepotřebujete znát programování, stačí textový editor (Poznámkový blok postačí).''',
    s1='''V tomto repozitáři otevřete složku [`lang`](../lang/) a stáhněte soubor svého jazyka (`{code}.json`). Pokud tam ještě není, stáhněte `en.json`.''',
    s2='''Vložte ho do složky vlastních jazyků své instalace FS Passion (otevře ji tlačítko **{open_folder}** v {lang_path}):''',
    s2a='''nainstalovaná verze: {p_inst};''',
    s2b='''přenosná verze: {p_port} vedle `FSPassion.exe`.''',
    s3='''Přejmenujte ho, například na `{code}_corrected.json` (název nesmí začínat znakem `_`). Neměňte řádek `"code"` na začátku souboru: váš soubor pak nahradí vestavěný jazyk. Pokud vycházíte z `en.json`: na řádek `"code"` napište `"{code}"` a na řádek `"name"` `"{lname}"`.''',
    s4='''Opravte texty v uvozovkách napravo od znaků `:` a uložte soubor (kódování UTF-8). Klíče vlevo a slova ve složených závorkách, jako `{{count}}`, ponechte beze změny.''',
    s5='''Restartujte FS Passion a vyberte svůj jazyk v {lang_path}: je označen jako „{personal}“. Zkontrolujte své opravy v rozhraní.''',
    s6='''Pošlete opravený soubor na kartě [Issues]({issues}): vytvořte issue s názvem například „Translation: {lname}“ a přiložte soubor (zabalte ho do ZIP, pokud GitHub odmítne příponu `.json`).''',
)

HELP["da"] = dict(
    h_shots="Skærmbilleder",
    shots=[
        "Alle mods i en spilversion, infokort og valg af flere mods",
        "Opsætninger: skift med ét klik (lyst tema, fransk grænseflade)",
        "Stor forhåndsvisning, når musen holdes over (FS22, temaet Synthwave '84)",
        "Temaer og sprog (polsk grænseflade)",
        "Mod-mapper på flere drev",
        "Indstillinger: meddelelsesområde, internetforbindelse, sikkerhedskopi (portugisisk grænseflade)",
    ],
    help='''Oversættelserne er en første udgave: rettelser fra modersmålstalere er meget velkomne, både til de nuværende sprog og til dem, der kommer. Du behøver ikke kunne programmere, kun en teksteditor (Notesblok er fint).''',
    s1='''Åbn mappen [`lang`](../lang/) i dette repository, og hent filen for dit sprog (`{code}.json`). Hvis den ikke findes endnu, så hent `en.json`.''',
    s2='''Læg den i mappen med egne sprog i din FS Passion-installation (knappen **{open_folder}** under {lang_path} åbner den):''',
    s2a='''installeret version: {p_inst};''',
    s2b='''portabel version: {p_port} ved siden af `FSPassion.exe`.''',
    s3='''Omdøb den, for eksempel til `{code}_corrected.json` (navnet må ikke begynde med `_`). Ret ikke linjen `"code"` øverst i filen: så erstatter din fil det indbyggede sprog. Hvis du starter fra `en.json`: skriv `"{code}"` på linjen `"code"` og `"{lname}"` på linjen `"name"`.''',
    s4='''Ret teksterne i anførselstegn til højre for `:`-tegnene, og gem filen (kodning UTF-8). Lad nøglerne til venstre og ordene i krøllede parenteser som `{{count}}` være uændrede.''',
    s5='''Genstart FS Passion, og vælg dit sprog under {lang_path}: det er markeret som »{personal}«. Kontrollér dine rettelser i grænsefladen.''',
    s6='''Send den rettede fil under fanen [Issues]({issues}): opret et issue med en titel som »Translation: {lname}«, og vedhæft filen (pak den i en ZIP, hvis GitHub afviser filtypen `.json`).''',
)

HELP["fi"] = dict(
    h_shots="Kuvakaappaukset",
    shots=[
        "Pelin version kaikki modit, tietokortti ja usean modin valinta",
        "Kokoonpanot: vaihto yhdellä napsautuksella (vaalea teema, ranskankielinen käyttöliittymä)",
        "Suuri esikatselu, kun hiiri viedään modin päälle (FS22, teema Synthwave '84)",
        "Teemat ja kielet (puolankielinen käyttöliittymä)",
        "Modikansiot usealla levyllä",
        "Asetukset: ilmaisinalue, internetyhteys, varmuuskopio (portugalinkielinen käyttöliittymä)",
    ],
    help='''Käännökset ovat ensimmäinen versio: äidinkielisten korjaukset ovat erittäin tervetulleita, sekä nykyisiin että tuleviin kieliin. Ohjelmointitaitoa ei tarvita, vain tekstieditori (Muistio riittää).''',
    s1='''Avaa tämän repositorion kansio [`lang`](../lang/) ja lataa oman kielesi tiedosto (`{code}.json`). Jos sitä ei vielä ole, lataa `en.json`.''',
    s2='''Siirrä se FS Passion -asennuksesi omien kielten kansioon (painike **{open_folder}** kohdassa {lang_path} avaa sen):''',
    s2a='''asennettu versio: {p_inst};''',
    s2b='''siirrettävä versio: {p_port} tiedoston `FSPassion.exe` vieressä.''',
    s3='''Nimeä se uudelleen, esimerkiksi `{code}_corrected.json` (nimi ei saa alkaa merkillä `_`). Älä muuta tiedoston alussa olevaa riviä `"code"`: silloin tiedostosi korvaa sisäänrakennetun kielen. Jos aloitat tiedostosta `en.json`: kirjoita riville `"code"` `"{code}"` ja riville `"name"` `"{lname}"`.''',
    s4='''Korjaa lainausmerkeissä olevat tekstit `:`-merkkien oikealla puolella ja tallenna tiedosto (merkistö UTF-8). Jätä vasemmalla olevat avaimet ja aaltosulkeissa olevat sanat, kuten `{{count}}`, ennalleen.''',
    s5='''Käynnistä FS Passion uudelleen ja valitse kielesi kohdassa {lang_path}: se on merkitty ”{personal}”. Tarkista korjauksesi käyttöliittymässä.''',
    s6='''Lähetä korjattu tiedosto välilehdellä [Issues]({issues}): luo issue, jonka otsikko on esimerkiksi ”Translation: {lname}”, ja liitä tiedosto (pakkaa se ZIP-tiedostoon, jos GitHub ei hyväksy päätettä `.json`).''',
)

HELP["hu"] = dict(
    h_shots="Képernyőképek",
    shots=[
        "Egy játékverzió összes modja, információs kártya és többszörös kijelölés",
        "Összeállítások: váltás egy kattintással (világos téma, francia felület)",
        "Nagy előnézet, ha az egeret a mod fölé viszi (FS22, Synthwave '84 téma)",
        "Témák és nyelvek (lengyel felület)",
        "Modmappák több meghajtón",
        "Beállítások: értesítési terület, internetkapcsolat, biztonsági mentés (portugál felület)",
    ],
    help='''A fordítások első változatok: az anyanyelvi beszélők javításait nagy örömmel fogadjuk, a jelenlegi és a hamarosan érkező nyelvekhez is. Nem kell programozni tudni, csak egy szövegszerkesztő kell (a Jegyzettömb is megfelel).''',
    s1='''Ebben a tárolóban nyisd meg a [`lang`](../lang/) mappát, és töltsd le a nyelved fájlját (`{code}.json`). Ha még nincs ott, töltsd le az `en.json` fájlt.''',
    s2='''Tedd az FS Passion-telepítésed saját nyelveinek mappájába (a {lang_path} alatti **{open_folder}** gomb megnyitja):''',
    s2a='''telepített változat: {p_inst};''',
    s2b='''hordozható változat: {p_port}, a `FSPassion.exe` mellett.''',
    s3='''Nevezd át, például `{code}_corrected.json` névre (a név nem kezdődhet `_` jellel). A fájl elején lévő `"code"` sort ne módosítsd: így a fájlod a beépített nyelv helyére lép. Ha az `en.json` fájlból indulsz: a `"code"` sorba írd be: `"{code}"`, a `"name"` sorba: `"{lname}"`.''',
    s4='''Javítsd ki az idézőjelek közötti szövegeket a `:` jelektől jobbra, majd mentsd a fájlt (UTF-8 kódolással). A bal oldali kulcsokat és a kapcsos zárójelek közötti szavakat, például `{{count}}`, hagyd változatlanul.''',
    s5='''Indítsd újra az FS Passiont, és válaszd ki a nyelvedet itt: {lang_path}. A nyelv „{personal}” jelölést kap. Ellenőrizd a javításaidat a felületen.''',
    s6='''Küldd el a javított fájlt az [Issues]({issues}) lapon: hozz létre egy issue-t például „Translation: {lname}” címmel, és csatold a fájlt (ZIP-be tömörítve, ha a GitHub nem fogadja el a `.json` kiterjesztést).''',
)

HELP["nb"] = dict(
    h_shots="Skjermbilder",
    shots=[
        "Alle moddene i en spillversjon, infokort og valg av flere modder",
        "Oppsett: bytt med ett klikk (lyst tema, fransk grensesnitt)",
        "Stor forhåndsvisning når musen holdes over (FS22, temaet Synthwave '84)",
        "Temaer og språk (polsk grensesnitt)",
        "Modmapper på flere disker",
        "Innstillinger: varslingsområde, internettilkobling, sikkerhetskopi (portugisisk grensesnitt)",
    ],
    help='''Oversettelsene er en første versjon: rettelser fra morsmålsbrukere er hjertelig velkomne, både for de nåværende språkene og for dem som kommer. Du trenger ikke kunne programmere, bare et tekstredigeringsprogram (Notisblokk holder).''',
    s1='''Åpne mappen [`lang`](../lang/) i dette repositoriet, og last ned filen for språket ditt (`{code}.json`). Hvis den ikke finnes ennå, last ned `en.json`.''',
    s2='''Legg den i mappen for egne språk i FS Passion-installasjonen din (knappen **{open_folder}** under {lang_path} åpner den):''',
    s2a='''installert versjon: {p_inst};''',
    s2b='''bærbar versjon: {p_port} ved siden av `FSPassion.exe`.''',
    s3='''Gi den nytt navn, for eksempel `{code}_corrected.json` (navnet kan ikke begynne med `_`). Ikke endre linjen `"code"` øverst i filen: da erstatter filen din det innebygde språket. Hvis du starter fra `en.json`: skriv `"{code}"` på linjen `"code"` og `"{lname}"` på linjen `"name"`.''',
    s4='''Rett tekstene i anførselstegn til høyre for `:`-tegnene, og lagre filen (koding UTF-8). La nøklene til venstre og ordene i krøllparenteser som `{{count}}` være uendret.''',
    s5='''Start FS Passion på nytt, og velg språket ditt under {lang_path}: det er merket «{personal}». Kontroller rettelsene dine i grensesnittet.''',
    s6='''Send den rettede filen under fanen [Issues]({issues}): opprett et issue med en tittel som «Translation: {lname}», og legg ved filen (pakk den i en ZIP hvis GitHub avviser filtypen `.json`).''',
)

HELP["ro"] = dict(
    h_shots="Capturi de ecran",
    shots=[
        "Toate modurile unei versiuni a jocului, fișa de informații și selecția multiplă",
        "Configurații: schimbare dintr-un clic (temă deschisă, interfață în franceză)",
        "Previzualizare mare la trecerea cu mouse-ul (FS22, tema Synthwave '84)",
        "Teme și limbi (interfață în poloneză)",
        "Foldere de moduri pe mai multe discuri",
        "Setări: zona de notificare, conexiunea la Internet, copia de siguranță (interfață în portugheză)",
    ],
    help='''Traducerile sunt o primă versiune: corecturile vorbitorilor nativi sunt foarte binevenite, pentru limbile actuale și pentru cele care urmează. Nu e nevoie să știi programare, doar un editor de text (Notepad e suficient).''',
    s1='''În acest depozit, deschide folderul [`lang`](../lang/) și descarcă fișierul limbii tale (`{code}.json`). Dacă nu există încă, descarcă `en.json`.''',
    s2='''Pune-l în folderul de limbi personale al instalării tale FS Passion (butonul **{open_folder}** din {lang_path} îl deschide):''',
    s2a='''versiunea instalată: {p_inst};''',
    s2b='''versiunea portabilă: {p_port}, lângă `FSPassion.exe`.''',
    s3='''Redenumește-l, de exemplu `{code}_corrected.json` (numele nu trebuie să înceapă cu `_`). Nu modifica linia `"code"` de la începutul fișierului: astfel fișierul tău înlocuiește limba inclusă. Dacă pornești de la `en.json`: scrie `"{code}"` pe linia `"code"` și `"{lname}"` pe linia `"name"`.''',
    s4='''Corectează textele dintre ghilimele, din dreapta semnelor `:`, și salvează fișierul (codificare UTF-8). Lasă neschimbate cheile din stânga și cuvintele dintre acolade, precum `{{count}}`.''',
    s5='''Repornește FS Passion și alege-ți limba din {lang_path}: este marcată „{personal}”. Verifică-ți corecturile în interfață.''',
    s6='''Trimite fișierul corectat în fila [Issues]({issues}): creează un issue cu un titlu precum „Translation: {lname}” și atașează fișierul (arhivat ZIP dacă GitHub refuză extensia `.json`).''',
)

HELP["ru"] = dict(
    h_shots="Снимки экрана",
    shots=[
        "Все моды одной версии игры, карточка мода и выбор нескольких модов",
        "Сборки: переключение одним щелчком (светлая тема, интерфейс на французском)",
        "Большое превью при наведении мыши (FS22, тема Synthwave '84)",
        "Темы и языки (интерфейс на польском)",
        "Папки модов на нескольких дисках",
        "Настройки: область уведомлений, подключение к Интернету, резервная копия (интерфейс на португальском)",
    ],
    help='''Переводы — это первая версия: исправления от носителей языка очень приветствуются, как для текущих языков, так и для будущих. Знать программирование не нужно, достаточно текстового редактора (подойдёт Блокнот).''',
    s1='''В этом репозитории откройте папку [`lang`](../lang/) и скачайте файл своего языка (`{code}.json`). Если его ещё нет, скачайте `en.json`.''',
    s2='''Поместите его в папку личных языков вашей установки FS Passion (её открывает кнопка **{open_folder}** в разделе {lang_path}):''',
    s2a='''установленная версия: {p_inst};''',
    s2b='''портативная версия: {p_port} рядом с `FSPassion.exe`.''',
    s3='''Переименуйте его, например в `{code}_corrected.json` (имя не должно начинаться с `_`). Не меняйте строку `"code"` в начале файла: тогда ваш файл заменит встроенный язык. Если вы начинаете с `en.json`: впишите `"{code}"` в строку `"code"` и `"{lname}"` в строку `"name"`.''',
    s4='''Исправьте тексты в кавычках справа от знаков `:` и сохраните файл (кодировка UTF-8). Ключи слева и слова в фигурных скобках, например `{{count}}`, оставьте без изменений.''',
    s5='''Перезапустите FS Passion и выберите свой язык в разделе {lang_path}: он отмечен как «{personal}». Проверьте свои исправления в интерфейсе.''',
    s6='''Отправьте исправленный файл на вкладке [Issues]({issues}): создайте issue с заголовком, например, «Translation: {lname}» и приложите файл (в ZIP-архиве, если GitHub не принимает расширение `.json`).''',
)

HELP["sv"] = dict(
    h_shots="Skärmbilder",
    shots=[
        "Alla moddar i en spelversion, infokort och val av flera moddar",
        "Uppsättningar: byt med ett klick (ljust tema, franskt gränssnitt)",
        "Stor förhandsvisning när musen hålls över (FS22, temat Synthwave '84)",
        "Teman och språk (polskt gränssnitt)",
        "Modmappar på flera enheter",
        "Inställningar: meddelandefält, internetanslutning, säkerhetskopia (portugisiskt gränssnitt)",
    ],
    help='''Översättningarna är en första version: rättelser från modersmålstalare är mycket välkomna, både för de nuvarande språken och för dem som kommer. Du behöver inte kunna programmera, bara en textredigerare (Anteckningar räcker).''',
    s1='''Öppna mappen [`lang`](../lang/) i det här repositoryt och ladda ned filen för ditt språk (`{code}.json`). Om den inte finns än, ladda ned `en.json`.''',
    s2='''Lägg den i mappen för egna språk i din FS Passion-installation (knappen **{open_folder}** under {lang_path} öppnar den):''',
    s2a='''installerad version: {p_inst};''',
    s2b='''portabel version: {p_port} bredvid `FSPassion.exe`.''',
    s3='''Byt namn på den, till exempel `{code}_corrected.json` (namnet får inte börja med `_`). Ändra inte raden `"code"` högst upp i filen: då ersätter din fil det inbyggda språket. Om du utgår från `en.json`: skriv `"{code}"` på raden `"code"` och `"{lname}"` på raden `"name"`.''',
    s4='''Rätta texterna inom citattecken till höger om `:`-tecknen och spara filen (kodning UTF-8). Låt nycklarna till vänster och orden inom klammerparenteser som `{{count}}` vara oförändrade.''',
    s5='''Starta om FS Passion och välj ditt språk under {lang_path}: det är markerat som ”{personal}”. Kontrollera dina rättelser i gränssnittet.''',
    s6='''Skicka den rättade filen under fliken [Issues]({issues}): skapa ett issue med en titel som ”Translation: {lname}” och bifoga filen (packa den i en ZIP om GitHub inte godtar filändelsen `.json`).''',
)

HELP["tr"] = dict(
    h_shots="Ekran görüntüleri",
    shots=[
        "Bir oyun sürümünün tüm modları, bilgi kartı ve çoklu seçim",
        "Kurulumlar: tek tıkla geçiş (açık tema, Fransızca arayüz)",
        "Fareyle üzerine gelince büyük önizleme (FS22, Synthwave '84 teması)",
        "Temalar ve diller (Lehçe arayüz)",
        "Birden çok sürücüde mod klasörleri",
        "Ayarlar: bildirim alanı, İnternet bağlantısı, yedekleme (Portekizce arayüz)",
    ],
    help='''Çeviriler ilk sürümdür: ana dili konuşanların düzeltmeleri, hem mevcut diller hem de gelecek diller için memnuniyetle karşılanır. Kodlama bilgisi gerekmez, yalnızca bir metin düzenleyici yeterlidir (Not Defteri olur).''',
    s1='''Bu depoda [`lang`](../lang/) klasörünü açın ve dilinizin dosyasını indirin (`{code}.json`). Henüz yoksa `en.json` dosyasını indirin.''',
    s2='''Dosyayı FS Passion kurulumunuzun kişisel diller klasörüne koyun ({lang_path} altındaki **{open_folder}** düğmesi bu klasörü açar):''',
    s2a='''kurulu sürüm: {p_inst};''',
    s2b='''taşınabilir sürüm: `FSPassion.exe` dosyasının yanındaki {p_port}.''',
    s3='''Dosyayı yeniden adlandırın, örneğin `{code}_corrected.json` (ad `_` ile başlamamalıdır). Dosyanın başındaki `"code"` satırını değiştirmeyin: böylece dosyanız yerleşik dilin yerini alır. `en.json` dosyasından başlıyorsanız: `"code"` satırına `"{code}"`, `"name"` satırına `"{lname}"` yazın.''',
    s4='''`:` işaretlerinin sağındaki tırnak içindeki metinleri düzeltin ve dosyayı kaydedin (UTF-8 kodlaması). Soldaki anahtarlara ve `{{count}}` gibi süslü parantez içindeki sözcüklere dokunmayın.''',
    s5='''FS Passion'ı yeniden başlatın ve {lang_path} altında dilinizi seçin: “{personal}” olarak işaretlenmiştir. Düzeltmelerinizi arayüzde kontrol edin.''',
    s6='''Düzeltilmiş dosyayı [Issues]({issues}) sekmesinden gönderin: örneğin “Translation: {lname}” başlıklı bir issue oluşturun ve dosyayı ekleyin (GitHub `.json` uzantısını kabul etmezse ZIP olarak sıkıştırın).''',
)

HELP["uk"] = dict(
    h_shots="Знімки екрана",
    shots=[
        "Усі моди однієї версії гри, картка мода й вибір кількох модів",
        "Збірки: перемикання одним клацанням (світла тема, інтерфейс французькою)",
        "Великий попередній перегляд під час наведення миші (FS22, тема Synthwave '84)",
        "Теми й мови (інтерфейс польською)",
        "Теки модів на кількох дисках",
        "Налаштування: область сповіщень, підключення до Інтернету, резервна копія (інтерфейс португальською)",
    ],
    help='''Переклади — це перша версія: виправлення від носіїв мови дуже вітаються, як для поточних мов, так і для майбутніх. Знати програмування не потрібно, досить текстового редактора (підійде Блокнот).''',
    s1='''У цьому репозиторії відкрийте теку [`lang`](../lang/) і завантажте файл своєї мови (`{code}.json`). Якщо його ще немає, завантажте `en.json`.''',
    s2='''Покладіть його в теку особистих мов вашої інсталяції FS Passion (її відкриває кнопка **{open_folder}** у розділі {lang_path}):''',
    s2a='''встановлена версія: {p_inst};''',
    s2b='''портативна версія: {p_port} поруч із `FSPassion.exe`.''',
    s3='''Перейменуйте його, наприклад на `{code}_corrected.json` (назва не повинна починатися з `_`). Не змінюйте рядок `"code"` на початку файлу: тоді ваш файл замінить вбудовану мову. Якщо ви починаєте з `en.json`: впишіть `"{code}"` у рядок `"code"` і `"{lname}"` у рядок `"name"`.''',
    s4='''Виправте тексти в лапках праворуч від знаків `:` і збережіть файл (кодування UTF-8). Ключі ліворуч і слова у фігурних дужках, як-от `{{count}}`, залиште без змін.''',
    s5='''Перезапустіть FS Passion і виберіть свою мову в розділі {lang_path}: вона позначена як «{personal}». Перевірте свої виправлення в інтерфейсі.''',
    s6='''Надішліть виправлений файл на вкладці [Issues]({issues}): створіть issue із заголовком, наприклад, «Translation: {lname}» і додайте файл (у ZIP-архіві, якщо GitHub не приймає розширення `.json`).''',
)

HELP["vi"] = dict(
    h_shots="Ảnh chụp màn hình",
    shots=[
        "Tất cả mod của một phiên bản game, thẻ thông tin và chọn nhiều mod",
        "Bộ cấu hình: chuyển đổi chỉ với một cú nhấp (giao diện sáng, tiếng Pháp)",
        "Xem trước cỡ lớn khi rê chuột (FS22, chủ đề Synthwave '84)",
        "Chủ đề và ngôn ngữ (giao diện tiếng Ba Lan)",
        "Thư mục mod trên nhiều ổ đĩa",
        "Cài đặt: vùng thông báo, kết nối Internet, sao lưu (giao diện tiếng Bồ Đào Nha)",
    ],
    help='''Các bản dịch mới là phiên bản đầu tiên: rất hoan nghênh người bản ngữ góp ý sửa lỗi, cho các ngôn ngữ hiện có lẫn các ngôn ngữ sắp ra mắt. Bạn không cần biết lập trình, chỉ cần một trình soạn thảo văn bản (Notepad là đủ).''',
    s1='''Trong kho mã này, mở thư mục [`lang`](../lang/) và tải tệp ngôn ngữ của bạn (`{code}.json`). Nếu tệp chưa có, hãy tải `en.json`.''',
    s2='''Đặt tệp vào thư mục ngôn ngữ cá nhân của bản cài đặt FS Passion (nút **{open_folder}** trong {lang_path} sẽ mở thư mục này):''',
    s2a='''bản cài đặt: {p_inst};''',
    s2b='''bản di động: {p_port}, cạnh `FSPassion.exe`.''',
    s3='''Đổi tên tệp, ví dụ `{code}_corrected.json` (tên không được bắt đầu bằng `_`). Đừng sửa dòng `"code"` ở đầu tệp: khi đó tệp của bạn sẽ thay thế ngôn ngữ có sẵn. Nếu bạn bắt đầu từ `en.json`: ghi `"{code}"` vào dòng `"code"` và `"{lname}"` vào dòng `"name"`.''',
    s4='''Sửa các đoạn văn bản trong dấu ngoặc kép, ở bên phải dấu `:`, rồi lưu tệp (mã hóa UTF-8). Giữ nguyên các khóa ở bên trái và các từ trong dấu ngoặc nhọn như `{{count}}`.''',
    s5='''Khởi động lại FS Passion và chọn ngôn ngữ của bạn trong {lang_path}: ngôn ngữ đó được đánh dấu “{personal}”. Kiểm tra các chỗ sửa trong giao diện.''',
    s6='''Gửi tệp đã sửa trong thẻ [Issues]({issues}): tạo một issue có tiêu đề ví dụ “Translation: {lname}” và đính kèm tệp (nén thành ZIP nếu GitHub không nhận đuôi `.json`).''',
)

HELP["id"] = dict(
    h_shots="Tangkapan layar",
    shots=[
        "Semua mod dari satu versi game, kartu info, dan pilihan banyak mod",
        "Konfigurasi: berganti dengan satu klik (tema terang, antarmuka bahasa Prancis)",
        "Pratinjau besar saat kursor diarahkan (FS22, tema Synthwave '84)",
        "Tema dan bahasa (antarmuka bahasa Polandia)",
        "Folder mod di beberapa drive",
        "Pengaturan: area notifikasi, koneksi Internet, cadangan (antarmuka bahasa Portugis)",
    ],
    help='''Terjemahan ini masih versi pertama: koreksi dari penutur asli sangat diharapkan, untuk bahasa yang sudah ada maupun yang akan datang. Tidak perlu bisa memprogram, cukup editor teks (Notepad pun bisa).''',
    s1='''Di repositori ini, buka folder [`lang`](../lang/) dan unduh berkas bahasa Anda (`{code}.json`). Jika belum ada, unduh `en.json`.''',
    s2='''Letakkan berkas itu di folder bahasa pribadi instalasi FS Passion Anda (tombol **{open_folder}** di {lang_path} membukanya):''',
    s2a='''versi terpasang: {p_inst};''',
    s2b='''versi portabel: {p_port}, di samping `FSPassion.exe`.''',
    s3='''Ganti namanya, misalnya `{code}_corrected.json` (nama tidak boleh diawali `_`). Jangan ubah baris `"code"` di awal berkas: dengan begitu berkas Anda menggantikan bahasa bawaan. Jika Anda mulai dari `en.json`: tulis `"{code}"` di baris `"code"` dan `"{lname}"` di baris `"name"`.''',
    s4='''Perbaiki teks di antara tanda kutip, di sebelah kanan tanda `:`, lalu simpan berkas (pengodean UTF-8). Jangan ubah kunci di sebelah kiri dan kata di dalam kurung kurawal seperti `{{count}}`.''',
    s5='''Mulai ulang FS Passion dan pilih bahasa Anda di {lang_path}: bahasa itu ditandai “{personal}”. Periksa koreksi Anda di antarmuka.''',
    s6='''Kirim berkas yang sudah dikoreksi di tab [Issues]({issues}): buat issue dengan judul misalnya “Translation: {lname}” dan lampirkan berkasnya (kompres menjadi ZIP jika GitHub menolak ekstensi `.json`).''',
)

HELP["ja"] = dict(
    h_shots="スクリーンショット",
    shots=[
        "ゲームバージョンのすべての MOD、情報カード、複数選択",
        "構成：ワンクリックで切り替え（ライトテーマ、フランス語の画面）",
        "マウスを重ねると大きなプレビュー（FS22、Synthwave '84 テーマ）",
        "テーマと言語（ポーランド語の画面）",
        "複数ドライブ上の MOD フォルダー",
        "設定：通知領域、インターネット接続、バックアップ（ポルトガル語の画面）",
    ],
    help='''翻訳はまだ最初の版です。ネイティブスピーカーによる修正を大歓迎します。現在の言語も、これから追加される言語も対象です。プログラミングの知識は不要で、テキストエディター（メモ帳で十分）があれば作業できます。''',
    s1='''このリポジトリの [`lang`](../lang/) フォルダーを開き、自分の言語のファイル（`{code}.json`）をダウンロードします。まだない場合は `en.json` をダウンロードします。''',
    s2='''FS Passion のインストールにある個人用言語フォルダーにファイルを置きます（{lang_path} の **{open_folder}** ボタンで開けます）。''',
    s2a='''インストール版：{p_inst}''',
    s2b='''ポータブル版：`FSPassion.exe` の隣の {p_port}''',
    s3='''ファイル名を変更します。例：`{code}_corrected.json`（名前を `_` で始めないでください）。ファイル先頭の `"code"` 行は変更しないでください。そうすれば、このファイルが内蔵の言語を置き換えます。`en.json` から始める場合は、`"code"` 行に `"{code}"`、`"name"` 行に `"{lname}"` と書きます。''',
    s4='''`:` の右側にある引用符内のテキストを修正し、ファイルを保存します（文字コード UTF-8）。左側のキーと、`{{count}}` のような波かっこ内の語は変更しないでください。''',
    s5='''FS Passion を再起動し、{lang_path} で自分の言語を選びます。言語には「{personal}」と表示されます。画面で修正内容を確認してください。''',
    s6='''修正したファイルを [Issues]({issues}) タブから送ってください。「Translation: {lname}」のようなタイトルで issue を作成し、ファイルを添付します（GitHub が `.json` 拡張子を受け付けない場合は ZIP に圧縮してください）。''',
)

HELP["ko"] = dict(
    h_shots="스크린샷",
    shots=[
        "게임 버전의 모든 모드, 정보 카드, 여러 항목 선택",
        "구성: 클릭 한 번으로 전환 (밝은 테마, 프랑스어 화면)",
        "마우스를 올리면 큰 미리 보기 (FS22, Synthwave '84 테마)",
        "테마와 언어 (폴란드어 화면)",
        "여러 드라이브의 모드 폴더",
        "설정: 알림 영역, 인터넷 연결, 백업 (포르투갈어 화면)",
    ],
    help='''번역은 아직 첫 버전입니다. 원어민의 수정을 언제나 환영합니다. 현재 언어와 앞으로 추가될 언어 모두 해당됩니다. 프로그래밍 지식은 필요 없고 텍스트 편집기(메모장이면 충분)만 있으면 됩니다.''',
    s1='''이 저장소에서 [`lang`](../lang/) 폴더를 열고 자신의 언어 파일(`{code}.json`)을 내려받습니다. 아직 없다면 `en.json`을 내려받습니다.''',
    s2='''FS Passion 설치의 개인 언어 폴더에 파일을 넣습니다({lang_path}의 **{open_folder}** 버튼으로 열 수 있습니다).''',
    s2a='''설치 버전: {p_inst};''',
    s2b='''포터블 버전: `FSPassion.exe` 옆의 {p_port}.''',
    s3='''파일 이름을 바꿉니다. 예: `{code}_corrected.json` (이름은 `_`로 시작하면 안 됩니다). 파일 맨 위의 `"code"` 줄은 바꾸지 마세요. 그러면 이 파일이 기본 제공 언어를 대신합니다. `en.json`에서 시작한다면 `"code"` 줄에 `"{code}"`, `"name"` 줄에 `"{lname}"`을 적습니다.''',
    s4='''`:` 기호 오른쪽의 따옴표 안 텍스트를 고치고 파일을 저장합니다(UTF-8 인코딩). 왼쪽의 키와 `{{count}}`처럼 중괄호 안에 있는 단어는 그대로 두세요.''',
    s5='''FS Passion을 다시 시작하고 {lang_path}에서 언어를 선택합니다. 해당 언어에는 '{personal}' 표시가 붙습니다. 화면에서 수정 내용을 확인하세요.''',
    s6='''수정한 파일을 [Issues]({issues}) 탭으로 보내 주세요. 'Translation: {lname}' 같은 제목으로 issue를 만들고 파일을 첨부합니다(GitHub가 `.json` 확장자를 거부하면 ZIP으로 압축하세요).''',
)

HELP["zh-Hans"] = dict(
    h_shots="截图",
    shots=[
        "某个游戏版本的全部模组、信息卡片和多选",
        "配置：一键切换（浅色主题，法语界面）",
        "鼠标悬停时的大图预览（FS22，Synthwave '84 主题）",
        "主题和语言（波兰语界面）",
        "位于多个硬盘上的模组文件夹",
        "设置：通知区域、互联网连接、备份（葡萄牙语界面）",
    ],
    help='''翻译还只是第一版：非常欢迎母语使用者提出修改，现有语言和即将推出的语言都可以。不需要任何编程知识，只要一个文本编辑器（记事本就行）。''',
    s1='''在本仓库中打开 [`lang`](../lang/) 文件夹，下载你的语言文件（`{code}.json`）。如果还没有，就下载 `en.json`。''',
    s2='''把它放到 FS Passion 安装的个人语言文件夹中（{lang_path} 中的 **{open_folder}** 按钮可以打开它）：''',
    s2a='''安装版：{p_inst}；''',
    s2b='''便携版：`FSPassion.exe` 旁边的 {p_port}。''',
    s3='''重命名文件，例如 `{code}_corrected.json`（文件名不能以 `_` 开头）。不要修改文件开头的 `"code"` 行：这样你的文件就会替换内置语言。如果从 `en.json` 开始：在 `"code"` 行写 `"{code}"`，在 `"name"` 行写 `"{lname}"`。''',
    s4='''修改 `:` 右侧引号中的文字，然后保存文件（UTF-8 编码）。左侧的键以及花括号中的词（如 `{{count}}`）保持不变。''',
    s5='''重启 FS Passion，在 {lang_path} 中选择你的语言：它会标为“{personal}”。在界面中检查你的修改。''',
    s6='''在 [Issues]({issues}) 标签页提交修改后的文件：新建一个 issue，标题例如“Translation: {lname}”，并附上文件（如果 GitHub 不接受 `.json` 扩展名，请压缩为 ZIP）。''',
)

HELP["zh-Hant"] = dict(
    h_shots="螢幕截圖",
    shots=[
        "某個遊戲版本的全部模組、資訊卡片和多選",
        "配置：一鍵切換（淺色主題，法文介面）",
        "滑鼠停留時的大圖預覽（FS22，Synthwave '84 主題）",
        "主題和語言（波蘭文介面）",
        "位於多個磁碟上的模組資料夾",
        "設定：通知區域、網際網路連線、備份（葡萄牙文介面）",
    ],
    help='''翻譯目前還是第一版：非常歡迎母語使用者提供修正，現有語言和即將推出的語言都可以。不需要任何程式設計知識，只要一個文字編輯器（記事本就可以）。''',
    s1='''在本儲存庫中開啟 [`lang`](../lang/) 資料夾，下載你的語言檔（`{code}.json`）。如果還沒有，就下載 `en.json`。''',
    s2='''把它放到 FS Passion 安裝的個人語言資料夾中（{lang_path} 中的 **{open_folder}** 按鈕可以開啟它）：''',
    s2a='''安裝版：{p_inst}；''',
    s2b='''可攜版：`FSPassion.exe` 旁邊的 {p_port}。''',
    s3='''重新命名檔案，例如 `{code}_corrected.json`（檔名不能以 `_` 開頭）。不要修改檔案開頭的 `"code"` 行：這樣你的檔案就會取代內建語言。如果從 `en.json` 開始：在 `"code"` 行寫 `"{code}"`，在 `"name"` 行寫 `"{lname}"`。''',
    s4='''修改 `:` 右側引號中的文字，然後儲存檔案（UTF-8 編碼）。左側的鍵以及大括號中的詞（如 `{{count}}`）保持不變。''',
    s5='''重新啟動 FS Passion，在 {lang_path} 中選擇你的語言：它會標示為「{personal}」。在介面中檢查你的修正。''',
    s6='''在 [Issues]({issues}) 分頁提交修正後的檔案：建立一個 issue，標題例如「Translation: {lname}」，並附上檔案（如果 GitHub 不接受 `.json` 副檔名，請壓縮為 ZIP）。''',
)

# Libellés de l'interface cités dans la section d'aide : repris de
# lang/<langue>.json quand l'interface existe dans cette langue.
HELP_LABELS = {
    "open_folder": ("Open the personal languages folder", ("settings.language.open_folder",)),
    "lang_path": ("Settings → Display → Language", ("settings.title", "settings.look.title", "settings.language.title")),
    "personal": ("personal", ("settings.language.personal",)),
}


# Point « Langues », inséré après le point des thèmes. {nlang} : nombre
# de langues de l'interface ; {langs} : leurs noms, chacun dans sa langue.
LANG_BULLET = {
    "de": "**Sprachen**: Oberfläche in {nlang} Sprachen ({langs}), automatisch nach der Windows-Sprache gewählt und in den Einstellungen änderbar; eigene Übersetzungen können hinzugefügt werden.",
    "es": "**Idiomas**: interfaz en {nlang} idiomas ({langs}), elegida según el idioma de Windows y modificable en los ajustes; puedes añadir tu propia traducción.",
    "es-419": "**Idiomas**: interfaz en {nlang} idiomas ({langs}), elegida según el idioma de Windows y modificable en los ajustes; puedes agregar tu propia traducción.",
    "it": "**Lingue**: interfaccia in {nlang} lingue ({langs}), scelta in base alla lingua di Windows e modificabile nelle Impostazioni; puoi aggiungere la tua traduzione.",
    "pt-BR": "**Idiomas**: interface em {nlang} idiomas ({langs}), escolhida conforme o idioma do Windows e alterável nas Configurações; você pode adicionar sua própria tradução.",
    "pt-PT": "**Idiomas**: interface em {nlang} idiomas ({langs}), escolhida de acordo com o idioma do Windows e alterável nas Definições; pode adicionar a sua própria tradução.",
    "nl": "**Talen**: interface in {nlang} talen ({langs}), gekozen op basis van de Windows-taal en aan te passen in de Instellingen; je kunt je eigen vertaling toevoegen.",
    "pl": "**Języki**: interfejs w {nlang} językach ({langs}), wybierany według języka systemu Windows i zmieniany w Ustawieniach; możesz dodać własne tłumaczenie.",
    "cs": "**Jazyky**: rozhraní v {nlang} jazycích ({langs}), vybrané podle jazyka Windows a změnitelné v Nastavení; můžete přidat vlastní překlad.",
    "da": "**Sprog**: grænseflade på {nlang} sprog ({langs}), valgt ud fra Windows-sproget og kan ændres i Indstillinger; du kan tilføje din egen oversættelse.",
    "fi": "**Kielet**: käyttöliittymä {nlang} kielellä ({langs}), valitaan Windowsin kielen mukaan ja vaihdettavissa asetuksista; voit lisätä oman käännöksesi.",
    "hu": "**Nyelvek**: a felület {nlang} nyelven érhető el ({langs}), a Windows nyelve alapján választva, és a Beállításokban módosítható; saját fordítás is hozzáadható.",
    "nb": "**Språk**: grensesnitt på {nlang} språk ({langs}), valgt etter Windows-språket og kan endres i Innstillinger; du kan legge til din egen oversettelse.",
    "ro": "**Limbi**: interfață în {nlang} limbi ({langs}), aleasă după limba Windows și modificabilă din Setări; poți adăuga propria traducere.",
    "ru": "**Языки**: интерфейс на {nlang} языках ({langs}), выбирается по языку Windows и меняется в настройках; можно добавить собственный перевод.",
    "sv": "**Språk**: gränssnitt på {nlang} språk ({langs}), väljs efter Windows-språket och kan ändras i Inställningar; du kan lägga till en egen översättning.",
    "tr": "**Diller**: {nlang} dilde arayüz ({langs}); Windows diline göre seçilir ve Ayarlar'dan değiştirilebilir; kendi çevirinizi ekleyebilirsiniz.",
    "uk": "**Мови**: інтерфейс {nlang} мовами ({langs}), обирається за мовою Windows і змінюється в налаштуваннях; можна додати власний переклад.",
    "vi": "**Ngôn ngữ**: giao diện bằng {nlang} ngôn ngữ ({langs}), tự chọn theo ngôn ngữ của Windows và có thể đổi trong phần Cài đặt; bạn có thể thêm bản dịch của riêng mình.",
    "id": "**Bahasa**: antarmuka dalam {nlang} bahasa ({langs}), dipilih sesuai bahasa Windows dan dapat diubah di Pengaturan; Anda dapat menambahkan terjemahan sendiri.",
    "ja": "**言語**：インターフェースは {nlang} 言語に対応（{langs}）。Windows の言語に合わせて選ばれ、設定で変更できます。独自の翻訳を追加することもできます。",
    "ko": "**언어**: 인터페이스는 {nlang}개 언어를 지원합니다({langs}). Windows 언어에 따라 선택되며 설정에서 바꿀 수 있고, 직접 번역을 추가할 수도 있습니다.",
    "zh-Hans": "**语言**：界面支持 {nlang} 种语言（{langs}），根据 Windows 语言自动选择，可在设置中更改；也可以添加自己的翻译。",
    "zh-Hant": "**語言**：介面支援 {nlang} 種語言（{langs}），依 Windows 語言自動選擇，可在設定中變更；也可以加入自己的翻譯。",
}

# Ordre des langues de l'interface dans le point « Langues » (celles absentes
# de lang/ sont ignorées, celles qui manquent ici sont ajoutées à la fin).
UI_ORDER = ["en", "fr", "de", "es", "it", "pt-BR", "pt-PT", "nl", "pl", "cs", "da", "fi", "nb", "sv"]


def ui_languages() -> list[str]:
    """Noms des langues de l'interface (champ _meta.name de lang/*.json)."""
    names = {}
    for path in sorted((ROOT / "lang").glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))["_meta"]
        names[meta["code"]] = meta["name"]
    order = [c for c in UI_ORDER if c in names] + sorted(c for c in names if c not in UI_ORDER)
    return [names[c] for c in order]


# Libellés de l'interface cités en anglais dans les textes : remplacés par ceux
# de lang/<langue>.json quand l'interface existe dans cette langue.
UI_FILE = {"es-419": "es"}
UI_LABELS = {
    "Settings → Help and about → Logs and diagnostics": ("settings.title", "settings.help.title", "settings.logs.title"),
    "Settings → Application": ("settings.title", "settings.app.title"),
    "Copy diagnostics": ("settings.logs.copy_diag",),
    "Internet connection": ("settings.internet.title",),
    "FS Passion updates": ("settings.updates.title",),
}


def localize_labels(code: str, text: str) -> str:
    path = ROOT / "lang" / f"{UI_FILE.get(code, code)}.json"
    if not path.exists():
        return text
    data = json.loads(path.read_text(encoding="utf-8"))

    def get(key: str) -> str:
        node = data
        for part in key.split("."):
            node = node[part]
        return node

    for english, keys in UI_LABELS.items():
        text = text.replace(english, " → ".join(get(k) for k in keys))
    return text


def ui_label(code: str, name: str) -> str:
    """Libellé de l'interface pour la section d'aide (anglais par défaut)."""
    english, keys = HELP_LABELS[name]
    path = ROOT / "lang" / f"{UI_FILE.get(code, code)}.json"
    if not path.exists():
        return english
    data = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for key in keys:
        node = data
        for part in key.split("."):
            node = node[part]
        parts.append(node)
    return " → ".join(parts)


def screenshots(d: dict) -> list[str]:
    """Galerie de captures, deux par ligne ; un clic ouvre l'image entière."""
    cells = []
    for name, caption in zip(SHOT_FILES, d["shots"], strict=True):
        src = f"../assets/screenshots/{name}.webp"
        cells.append(f'<td width="50%"><a href="{src}"><img src="{src}" alt="{caption}" /></a><br />{caption}</td>')
    rows = ["<table>"]
    for i in range(0, len(cells), 2):
        rows += ["<tr>", *cells[i:i + 2], "</tr>"]
    rows.append("</table>")
    return rows


def help_section(code: str, h: dict) -> list[str]:
    """Section « Aider à améliorer les traductions », étapes numérotées."""
    values = dict(
        code=code, lname=NAMES[code], issues=ISSUES,
        p_inst="`%APPDATA%\\FSPassion\\lang\\`", p_port="`data\\lang\\`",
        **{k: ui_label(code, k) for k in HELP_LABELS},
    )

    def f(key: str) -> str:
        return h[key].format(**values)

    return [
        f("help"),
        "",
        f"1. {f('s1')}",
        f"2. {f('s2')}",
        f"   - {f('s2a')}",
        f"   - {f('s2b')}",
        *[f"{n}. {f(f's{n}')}" for n in range(3, 7)],
    ]


def render(code: str, d: dict) -> str:
    langs = ui_languages()
    links = dict(releases=RELEASES, issues=ISSUES, bmac=BMAC, stripe=STRIPE, themes=THEMES,
                 nlang=len(langs), langs=", ".join(langs),
                 nsoon=len(SOON), soonlist=", ".join(NAMES[c] for c in SOON))
    lang_item = f"{LANG_BULLET[code]} **{d['soon']}**: {{soonlist}}."
    features = [*d["f"][:8], lang_item, *d["f"][8:]]
    # Même ligne de liens que README.md (l.13), avec la langue courante en gras.
    nav = " · ".join(["[English](../README.md)"] + [
        f"**{name}**" if c == code else f"[{name}](README.{c}.md)" for c, name in NAMES.items()])

    def f(text: str) -> str:
        return text.format(**links)

    lines = [
        "# FS Passion",
        "",
        '<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />',
        "",
        nav,
        "",
        f(d["sub"]),
        "",
        f(d["p1"]),
        "",
        f(d["p2"]),
        "",
        *[f"- {f(x)}" for x in features],
        "",
        f"> {f(d['warn'])}",
        "",
        f"## {HELP[code]['h_shots']}",
        "",
        *screenshots(HELP[code]),
        "",
        f"## {d['h_dl']}",
        "",
        f(d["dl_intro"]),
        "",
        f"- `FSPassion-X.Y.Z-setup.exe`: {f(d['dl_setup'])}",
        f"- `FSPassion-X.Y.Z-portable.zip`: {f(d['dl_port'])}",
        f"- `SHA256SUMS.txt`: {f(d['dl_sums'])}",
        "",
        f(d["dl_sign"] + " " + d["sign"]),
        "",
        f"## {d['h_help']}",
        "",
        *help_section(code, HELP[code]),
        "",
        f"## {d['h_rep']}",
        "",
        f(d["rep"]),
        "",
        f"## {d['h_sup']}",
        "",
        f(d["sup"]),
        "",
        f"## {d['h_net']}",
        "",
        f(d["net"]),
        "",
        f"## {d['h_lic']}",
        "",
        f(d["lic"]),
        "",
        f(d["disc"]),
        "",
    ]
    return localize_labels(code, "\n".join(lines))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for code, data in T.items():
        assert len(data["f"]) == 9 and code in LANG_BULLET, code
        assert code in HELP and len(HELP[code]["shots"]) == len(SHOT_FILES), code
        (OUT / f"README.{code}.md").write_text(render(code, data), encoding="utf-8")
    print(f"{len(T)} traductions écrites dans {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
