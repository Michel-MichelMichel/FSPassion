# FS Passion

<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />

[English](../README.md) · **Français** · [Deutsch](README.de.md) · [Español](README.es.md) · [Español (Latinoamérica)](README.es-419.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Português (Portugal)](README.pt-PT.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Suomi](README.fi.md) · [Magyar](README.hu.md) · [Norsk bokmål](README.nb.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [简体中文](README.zh-Hans.md) · [繁體中文](README.zh-Hant.md)

Gestionnaire de mods pour Farming Simulator (FS2011 à FS25), pour Windows 10 et 11.

L'inconvénient de Farming Simulator est qu'il n'offre qu'un seul répertoire de mods dans lequel nous nous retrouvons avec de nombreuses maps et des mods parfois incompatibles entre eux. La difficulté de passer d'une configuration de partie à l'autre freine la tentation de tester de nouvelles maps.

Le cœur de FS Passion est de répondre à ce problème avec une efficacité déconcertante : créez en quelques clics des **Parties** qui sont des collections de mods, et passez de l'une à l'autre en un seul clic. Tous vos mods resteront en un seul exemplaire dans leur répertoire d'origine, le dossier Mods.

- **Parties** : une map, ses dépendances et les mods de votre choix ; des **mods communs** partagés par toutes les parties.
- **Mises à jour** : celles faites par le jeu (ModHub) sont récupérées et suivies dans toutes les parties ; une version remplacée est mise de côté, jamais effacée.
- **Téléchargements** : les nouveaux mods sont repérés et rangés dans le dossier de mods de la version du jeu correspondante.
- **Plusieurs disques** : jusqu'à trois dossiers de mods situés sur différents disques.
- **Sauvegarde de la configuration** : export et import des parties et des réglages, pour une réinstallation ou un autre PC.
- **Visite guidée** : l'ampoule de l'en-tête présente l'interface en une minute, avec des exemples animés (versions, parties, listes, sélection multiple, glisser-déposer, raccourcis clavier).
- **Ne plus utiliser FS Passion** : le jeu retrouve son réglage d'origine, les dossiers de parties sont retirés ; vos mods ne sont jamais touchés.
- **Thèmes** bicolores, et thèmes inspirés de thèmes populaires en sombre et en clair (Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84).
- **Langues** : interface en 14 langues (English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska), choisie selon la langue de Windows et modifiable dans les Paramètres ; vous pouvez ajouter votre propre traduction. **Bientôt : 12 autres langues** : Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文.
- **Démo** : l'application s'adresse exclusivement aux possesseurs des jeux Farming Simulator. Si vous êtes un curieux qui veut tester les fonctionnalités de l'application sans posséder de jeu, un pack de démonstration est à votre disposition dans les Paramètres.

> ⚠️ Projet en développement (version : voir la page [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases)). Faites une sauvegarde complète de votre dossier de mods avant de l'essayer. Le seul lien officiel de téléchargement est cette page GitHub.

## Téléchargement

Sur la page [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases) :

- `FSPassion-X.Y.Z-setup.exe` : installeur, pour l'utilisateur courant sans droits administrateur, ou pour tous les utilisateurs ; il installe Microsoft Edge WebView2 si besoin (Windows 10) ;
- `FSPassion-X.Y.Z-portable.zip` : version portable, sans installation ; réglages et journaux dans le dossier `data` à côté de `FSPassion.exe` ;
- `SHA256SUMS.txt` : empreintes des deux fichiers.

Les fichiers ne sont pas encore signés : au premier lancement, Windows peut afficher « Windows a protégé votre ordinateur » (SmartScreen) → « Informations complémentaires » → « Exécuter quand même ». La signature gratuite par SignPath Foundation est prévue après une première publication.

## Aider à améliorer les traductions

Les corrections des locuteurs natifs sont les bienvenues. Le mode d'emploi détaillé est en anglais : [Help improve the translations](../README.md#help-improve-the-translations) (English).

## Signaler un problème, proposer une idée

Onglet [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues). Pour un problème, joignez le texte de « Copier le diagnostic » (Paramètres → Aide et à propos → Journaux et diagnostic).

## Soutenir le projet

FS Passion est et restera un projet de confiance, open source et gratuit. Pour remercier son auteur, un don ponctuel se fait en quelques secondes, sans création de compte : [Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) ou [don par carte (Stripe)](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00).

## Connexion Internet

FS Passion ne se connecte qu'à GitHub, pour lire le catalogue des DLC (noms et icônes, dépôt public `FSPassion-data`), au plus une fois par jour. Aucune donnée personnelle n'est envoyée. Le réglage « Connexion Internet » (Paramètres → Application) le désactive. Il recherche aussi sur GitHub une nouvelle version de FS Passion à chaque lancement (puis une fois par jour) : le réglage « Mises à jour de FS Passion » (Paramètres → Application) le désactive.

## Pour les développeurs

### Lancer depuis les sources

Prérequis : **Python 3.12, 64 bits** ([python.org](https://www.python.org/downloads/windows/)), installé avec la case « Add python.exe to PATH » cochée.

Double-cliquez sur **`lancer_dev.bat`**. Au premier lancement, il prépare l'environnement Python et installe les dépendances (une minute environ). Il ouvre ensuite la fenêtre de l'application. Options : voir le [README anglais](../README.md#run-from-source).

Tests automatiques : `lancer_tests.bat` (pytest et ruff).

### Fabriquer l'application

Double-cliquez sur **`fabriquer.bat`** (après un premier `lancer_dev.bat`). Résultat dans `build\release\` : l'installeur, la version portable et `SHA256SUMS.txt`. L'installeur demande [Inno Setup 6](https://jrsoftware.org/isdl.php) ; sans lui, seule la version portable est fabriquée.

Sur GitHub, la même fabrication tourne à chaque envoi (onglet **Actions**). Une étiquette `vX.Y.Z` crée en plus un brouillon de publication (**Releases**) avec les fichiers.

### Où sont les fichiers

| Emplacement | Contenu |
|---|---|
| `%APPDATA%\FSPassion\settings.json` | réglages, chemins par version |
| `%APPDATA%\FSPassion\lang\` | langues personnelles (modèle `_modele_en.json`) |
| `%APPDATA%\FSPassion\backups\` | état sauvegardé automatiquement avant chaque import (10 derniers) |
| `%LOCALAPPDATA%\FSPassion\logs\fspassion.log` | journal (chemins anonymisés), à joindre à un signalement |
| `%LOCALAPPDATA%\FSPassion\dlc\` | catalogue des DLC et icônes téléchargés depuis GitHub |
| `<dossier de mods>\..\FSPassion\<version>\parties.json` | parties, mods communs (+ 5 sauvegardes) |
| `<dossier de mods>\..\FSPassion\<version>\Parties\` | dossiers de parties : uniquement des liens |
| `<dossier de mods>\..\FSPassion\<version>\Old versions\` | versions remplacées (jamais effacées) |
| `<dossier de mods>\..\FSPassion\<version>\Recovered\` | fichiers récupérés (version plus ancienne…) |

## Licence et mentions

- FS Passion : **GPLv3** (fichier `LICENSE`), auteur MichelMichel.
- Icônes d'interface : [Lucide](https://lucide.dev), licence ISC (`assets\icons\LICENSE.txt`).
- Police : Iosevka Etoile Compact (version personnalisée), licence SIL OFL 1.1 (`assets\fonts\OFL-Iosevka.txt`).
- Police des titres de la visite guidée : [Caveat](https://github.com/googlefonts/caveat), licence SIL OFL 1.1 (`assets\fonts\OFL-Caveat.txt`).
- Police du chinois, du japonais et du coréen : sous-ensembles de [Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic) (elle-même construite à partir de Source Han Sans et d'Iosevka), renommés « FS Passion CJK » comme l'exige la licence, licence SIL OFL 1.1 (`assets\fonts\OFL-Sarasa.txt`).
- Dépendances : pywebview (BSD), Pillow (MIT-CMU), psutil (BSD), pystray (LGPL-3.0).
- Thèmes inspirés des palettes de : Catppuccin, Nord, Solarized, Gruvbox, Tokyo Night, Synthwave '84, Dracula Neue Pro et Monokai Pro (détails et liens dans le [README anglais](../README.md#license-and-credits)). Seules leurs couleurs sont reprises ; aucun fichier de ces thèmes n'est inclus.

FS Passion est un projet indépendant, non affilié à GIANTS Software. Farming Simulator est une marque de GIANTS Software. Les tests utilisent de faux mods générés : aucun contenu GIANTS n'est fourni.
