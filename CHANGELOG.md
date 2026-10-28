# Journal des versions

Les versions sont numérotées 0.x.y.

## 0.9.6 — 28 octobre 2026 — mises à jour automatiques de FS Passion

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Paramètres → Application → Mises à jour de FS Passion**, premier encart de la page :
   - un interrupteur, **activé par défaut**, autorise FS Passion à rechercher ses mises à jour sur GitHub. Il est indépendant de « Connexion Internet » (catalogue des DLC) ;
   - état de la recherche (à jour, dernière recherche, erreur) et bouton « Rechercher maintenant ».
2. **Recherche automatique** au lancement, puis une fois par jour tant que FS Passion reste ouvert (zone de notification). Seule la dernière publication définitive de la page Releases compte : ni brouillon, ni préversion. Aucune donnée personnelle n'est envoyée.
3. **Mise à jour disponible**, signalée sans message qui surgit :
   - une pastille sur la roue des Paramètres ;
   - « Nouvelle version x.y.z » à côté du numéro de version, en bas de la fenêtre (un clic ouvre l'encart) ;
   - une entrée dans l'historique des notifications (cloche).
4. **Installation en un clic** (« Installer la mise à jour ») :
   - l'installeur est téléchargé depuis la page Releases et vérifié avec son empreinte SHA-256 (`SHA256SUMS.txt`, publié avec lui) ; sans empreinte, ou si elle ne correspond pas, rien n'est installé ;
   - FS Passion se ferme, l'installeur s'exécute en silencieux avec sa barre de progression, puis relance FS Passion. Réglages, parties et mods sont conservés ;
   - refusée tant que Farming Simulator tourne : la remise en ordre des parties se fait à la fermeture du jeu.
5. **Version portable** : le `.zip` vérifié est téléchargé dans le dossier des téléchargements et montré dans l'Explorateur ; on remplace ensuite les fichiers du dossier de FS Passion en gardant le dossier `data`.
6. Installeur : nouveau paramètre `/RELAUNCH=1` (relance de FS Passion après une installation silencieuse).
7. Le réglage est repris par l'export de la configuration et figure dans le diagnostic. Textes dans les 14 langues, notice et README mis à jour.

## 0.9.5 — 28 octobre 2026 — sélecteur de langue, bienvenue agrandie, README (langues à venir)

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Paramètres → Affichage → Langue** : l'icône Langue est placée devant le bouton-liste, et non plus dedans. Le bouton ne montre que le nom de la langue et la flèche.
2. **Fenêtre de bienvenue** (premier lancement) agrandie : logo animé, sélecteur de langue en haut à droite, phrase d'introduction en bas, puis le bouton OK. Changer de langue traduit aussitôt la fenêtre.
3. **README GitHub** (anglais) : le point Languages annonce 12 nouvelles langues à venir, avec une section « Help improve the translations » qui explique comment proposer une traduction (télécharger le fichier `lang\XX.json`, le placer dans le dossier des langues personnelles, le corriger, puis l'envoyer dans l'onglet Issues).
4. **Taille maximale d'une langue personnelle : 100 Ko → 300 Ko.** Sans cela, une traduction en alphabet non latin (russe, japonais, chinois…) aurait été refusée. Le mode d'emploi du dossier des langues personnelles est mis à jour.

## 0.9.4 — 28 octobre 2026 — page GitHub illustrée, polices chinoises, japonaises et coréennes

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Image en tête du README** dans les 25 langues, par un chemin relatif, visible sur la page GitHub.
2. **Liste des fonctionnalités** : le point « Langues » remplace « French and English ». L'interface existe en 14 langues, chacune nommée dans sa propre langue ; la langue est choisie selon celle de Windows et reste modifiable dans les Paramètres. Une traduction personnelle est possible.
3. Dans les README traduits, les menus et boutons cités sont ceux de l'interface dans la langue du README quand elle existe, et restent en anglais sinon.
4. **Polices pour le chinois, le japonais et le coréen** : quatre sous-ensembles de **Sarasa Gothic**, une police par langue, renommés « FS Passion CJK J / K / SC / TC » comme l'exige la SIL OFL pour le nom réservé. Chacun ne garde que les caractères utiles (kana et kanji courants, hangûl courants, caractères simplifiés et traditionnels courants, et ceux des fichiers de langue correspondants).
   - Une police n'est chargée que si l'interface est dans sa langue, et seulement pour les caractères CJK ; le latin reste en Iosevka.
   - Repli sur les polices de Windows pour un caractère absent.
   - Police distribuée sous la SIL OFL 1.1 (texte : `assets\fonts\OFL-Sarasa.txt`), crédit ajouté au README.

## 0.9.3 — 28 octobre 2026 — six nouvelles langues (deuxième lot)

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Six nouvelles langues** : tchèque, danois, finnois, norvégien (bokmål), suédois, portugais du Portugal. FS Passion parle maintenant **14 langues**.
   - Vocabulaire repris des traductions du README. Vouvoiement en tchèque et en portugais du Portugal, tutoiement dans les langues nordiques.
   - Le tchèque a ses quatre formes de pluriel. Le finnois est construit pour que les noms insérés automatiquement (partie, jeu) restent corrects malgré les déclinaisons.
   - Le portugais du Portugal est distinct du portugais du Brésil.
   - Les noms Windows (Corbeille, Explorateur, zone de notification) sont ceux de chaque langue.
2. **Langue au premier lancement** : un Windows en portugais du Portugal reçoit ce portugais ; un Windows en norvégien nynorsk reçoit le bokmål.
3. **Libellés raccourcis** pour qu'ils tiennent (« Bientôt » sous FS28 dans certaines langues ; menu « Aide » des Paramètres en tchèque).

## 0.9.2 — 27 octobre 2026 — publication publique, six nouvelles langues

**Aucun fichier du jeu ni des mods n'est touché.**

Publication publique de la version actuelle.

### Ce qui change

1. Suppression de l'ancien mécanisme de protection.
2. **Paramètres → Application → Ne plus utiliser FS Passion** : le bouton **Exporter** porte la flèche vers le haut (`file-up`), comme le bouton Exporter de Paramètres → Sauvegarde.
3. **Six nouvelles langues** (premier lot) : allemand, espagnol, italien, polonais, portugais du Brésil, néerlandais. Vocabulaire repris des traductions du README, tutoiement comme sur la page GitHub. Le polonais a ses quatre formes de pluriel. La police de l'interface couvre toutes les lettres de ces langues.
4. **Notice en anglais** mise à jour d'après la notice française.
5. **Message « Erreur imprévue »** : il renvoie maintenant vers « Paramètres → Aide et à propos », au lieu d'un menu qui n'existe plus.
6. **Langue au premier lancement** : un Windows en portugais du Portugal reçoit le portugais du Brésil tant que le portugais du Portugal n'existe pas ; un Windows en espagnol d'Amérique latine reçoit l'espagnol.

## 0.9.1 — 27 octobre 2026 — visite guidée complétée, icône, dormance pendant le jeu

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Visite guidée : deux étapes de plus** (15 au lieu de 13).
   - **Nouveaux mods téléchargés**, après « Tous les mods » : le bouton de recherche des téléchargements est éclairé, puis une petite liste d'exemple montre chaque fichier partir vers le dossier de mods de sa version.
   - **Fermer sans quitter**, avant la fin : la croix de la fenêtre, puis un aperçu de la barre des tâches de Windows 11 et de la zone de notification. Infobulles : « Afficher les icônes cachées », « Clic : FS Passion revient · Clic droit : Quitter ».
2. **Glisser-déposer** de la visite : les tuiles qui suivent les flèches vont deux fois moins vite.
3. **Bulles et touches de la visite** : texte centré verticalement, et centré dans la touche.
4. **Icône de l'application** reconstruite en 10 tailles (16 à 256 px), dans les formats que l'Explorateur lit le plus sûrement. Le script de fabrication demande à Windows de relire ses icônes à la fin, pour éviter l'affichage de l'ancien logo depuis le cache.
5. **Icône des maps** : `map.svg` partout (plus lisible en petit).
6. **Dormance pendant le jeu** : quand FS Passion se réduit au lancement du jeu ou se cache dans la zone de notification, son interface est mise en veille et sa mémoire est réduite. La surveillance du jeu, les téléchargements et l'icône de notification continuent. Dès que la fenêtre revient, l'interface se réveille et relit tout.
7. **Plus de mention de la version de développement** dans les textes de l'application.
8. **Renommer un mod** : l'avertissement précise qu'il s'agit des sauvegardes **du jeu** qui utilisent le mod.
9. **README** : la page GitHub s'ouvre en anglais, avec des liens vers 25 traductions. La version française est revue.

## 0.9.0 — 26 octobre 2026 — visite guidée, versions absentes non sélectionnables

**Aucun fichier du jeu ni des mods n'est touché.** Pendant la visite, rien n'est modifié : les versions, parties et mods montrés sont des exemples.

### Ce qui change

1. **Versions absentes** (ni le jeu, ni son dossier de documents, ni un dossier de mods) : grisées, sans agrandissement au survol, non sélectionnables. L'infobulle indique « Non installée » et renvoie à Paramètres → Jeu et chemins, où l'on peut indiquer les chemins à la main. Auparavant, une version non installée n'était qu'atténuée.
2. **Visite guidée** : nouvelle **ampoule** dans l'en-tête (également dans Paramètres → Aide et à propos). L'interface s'assombrit et un faisceau de lumière passe d'un élément à l'autre, avec un titre, une flèche et une courte animation. Les étapes couvrent les versions du jeu, les parties, les opérations sur les parties, les mods communs et « Appliquer », le thème et les notifications, les trois listes, la sélection multiple, le glisser-déposer et les raccourcis clavier.
3. **Commandes de la visite** : Précédent (←), Rejouer (R), Suivant (→, Entrée, Espace), Quitter (Échap), Début et Fin. Les autres raccourcis sont désactivés pendant la visite.
4. **Premier lancement** : après la bienvenue et la notice, l'ampoule est mise en évidence une seule fois. Les fenêtres de démarrage attendent la fin de la visite.
5. **Police des titres** : Caveat (SIL OFL 1.1), pour les alphabets latin et cyrillique ; les autres écritures gardent la police de l'interface.
6. **Mouvement réduit** : la visite montre directement l'état final de chaque animation.

## 0.8.7 — 26 octobre 2026 — correctif : l'exécutable ne démarrait plus

### Ce qui s'est passé

En 0.8.5, les petits fichiers WebView2 pour ARM64 et 32 bits avaient été retirés pour alléger l'exécutable. pywebview vérifie pourtant au démarrage la présence des trois dossiers (`win-arm64`, `win-x64`, `win-x86`), même s'il n'en utilise qu'un : sans eux, il s'arrête. Le défaut n'apparaissait qu'avec l'exécutable fabriqué sous Windows.

### Ce qui change

- Les trois dossiers sont de nouveau embarqués. Les autres allègements restent (environ 8,7 Mo de moins).
- Un test empêche de les retirer à nouveau.

## 0.8.5 — 26 octobre 2026 — ordre des DLC de FS2011, icônes JPEG, exécutable allégé

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Ordre des DLC de FS2011** : le catalogue téléchargé était « nettoyé » à la réception, ce qui effaçait le champ d'ordre imposé. Corrigé, avec un test. Les catalogues sont datés pour que la correction s'applique tout de suite.
2. **Interface non mise en cache** : WebView2 ne garde plus les fichiers de l'interface pendant 10 minutes. Après une mise à jour, d'anciens fichiers ne peuvent plus servir.
3. **Exécutable allégé** (environ 9 Mo de moins) :
   - les 20 icônes de DLC au format AVIF (nommées « .jpg ») du dépôt de données sont devenues de vrais JPEG, et le module AVIF de Pillow n'est plus nécessaire. Les icônes déjà téléchargées sont remplacées automatiquement ;
   - retirés aussi : les parties de pywebview pour Android, ARM64 et 32 bits, deux modules de Pillow inutilisés, une documentation de pythonnet.

## 0.8.4 — 26 octobre 2026 — icône, version unique, bienvenue, détection FS15 / FS2013

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Icône** : l'exécutable, l'installeur et la zone de notification utilisent la même icône (`assets\brand\tray.png`).
2. **Numéro de version à un seul endroit** (`src\fspassion\__init__.py`). Le reste (exécutable, installeur, archives, À propos, pied de page, journaux) le lit à cet endroit. Un test vérifie qu'aucune copie ne réapparaît.
3. **Bienvenue et notice** : le fond de la fenêtre sert à la déplacer. Un clic sur le fond ne ferme plus la notice ; la croix et Échap restent.
4. **Thème par défaut : Gruvbox Light** au premier lancement et à la réinitialisation. Les réglages déjà enregistrés gardent leur thème.
5. **Champs de texte des thèmes clairs** : plus de blanc vif ; une teinte intermédiaire entre le fond et les sections.
6. **Precision Farming (FS25)** : l'icône est acceptée, son empreinte ayant été corrigée dans le catalogue.
7. **FS2011 : ordre imposé des DLC** : Classics Add-on 2, DLC 1, DLC 2, DLC 3, ProFarm 1, possédés ou non (nouveau champ `fixed_order` du catalogue).
8. **Paramètres** : le bouton « Réinitialiser les thèmes » est retiré de la section Affichage ; un petit espace sépare l'avertissement du bouton « Ne plus utiliser FS Passion ».
9. **Détection FS2013** : le dossier est reconnu même quand l'exécutable se trouve dans `x64\`. Les noms d'exécutables sont cherchés à la racine, la version 64 bits en premier.
10. **Détection FS15** : tout dossier dont le nom commence par « Farming Simulator » est examiné (racine des disques, Games, Jeux, Program Files), avec les deux noms de dossier.
11. **Message « … n'est pas encore configuré »** : il est dans une carte lisible, et la grille reste vide tant que la version n'est pas configurée.

## 0.8.3 — 26 octobre 2026 — fabrication : FS Passion encore ouvert

**Aucun changement de l'application.**

### Ce qui s'est passé

La fabrication échouait quand FS Passion tournait encore depuis le dossier de fabrication : Windows verrouille les fichiers d'un programme ouvert.

### Ce qui change

- Avant l'étape finale, `tools\build.py` cherche un FS Passion lancé depuis le dossier de fabrication. S'il en trouve un, la fabrication s'arrête avec un message demandant de le fermer.
- Si un fichier reste verrouillé malgré tout, le message indique son nom.

## 0.8.2 — 25 octobre 2026 — premier exécutable : icônes des DLC, thèmes, droits

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui s'est passé, et ce qui change

1. **Icônes des DLC absentes dans l'exécutable**, qui les télécharge depuis le dépôt de données. Trois défauts corrigés :
   - 20 icônes étaient des fichiers AVIF nommés « .jpg », refusés par le contrôle d'image. L'AVIF est accepté, reconnu à son contenu ;
   - seules les icônes des DLC possédés étaient téléchargées. Désormais, celles de tous les DLC du catalogue sont téléchargées, d'après le champ `icon` de chaque entrée ;
   - Precision Farming (FS25) : empreinte corrigée dans le catalogue.
2. **Thèmes** : les thèmes livrés reviennent à ceux de la 0.7.8. Les thèmes issus de réglages d'atelier ne sont plus livrés.
3. **Bienvenue** : en mode installé, la bienvenue ne s'affiche pas si les réglages existent déjà. La notice ne s'affiche que si sa case « à chaque démarrage » est cochée. La version portable démarre avec des réglages neufs : bienvenue, choix de la langue et notice.
4. **Avertissement de droits administrateur** : FS Passion ne demande jamais lui-même les droits administrateur, sauf si on le choisit. Le journal indique désormais à chaque démarrage le mode, « administrateur : oui/non » et l'état du réglage correspondant. L'installeur lance FS Passion avec les droits normaux de l'utilisateur.

## 0.8.1 — 25 octobre 2026 — la fabrication

**Aucun changement de l'application** : seuls les tests et les thèmes livrés changent.

### Ce qui change

1. **Tests sur liens symboliques** : quand Windows refuse les liens symboliques, les tests qui en exigent sont **ignorés**, avec la raison affichée, au lieu d'échouer.
2. **Suppression d'un mod** : sous Windows, le mod part dans la Corbeille. Le test accepte les deux comportements.
3. **Détection du dossier de mods** : comparaison des chemins normalisée, avec les séparateurs Windows.
4. **Thèmes livrés** : les réglages de l'atelier (néon, couleurs, grain) ont été repris comme thèmes livrés (`themes_default.json`). « Réinitialiser les thèmes » y revient. Le test vérifie que les thèmes livrés sont complets, sans exiger qu'ils soient identiques aux réglages de l'atelier.

## 0.8.0 — 25 octobre 2026 — fabrication : exécutable, installeur, désinstalleur, version portable, GitHub Actions

**Aucun fichier du jeu ni des mods n'est touché par la fabrication.** Le désinstalleur rétablit la ligne d'override du jeu.

### Corrections de l'en-tête

1. **En-tête bloqué sur deux lignes** (défaut de la 0.7.9) : la marge se mesure maintenant dans les espaces, et l'en-tête revient sur une ligne quand la fenêtre s'élargit.
2. **Logo à 100 % de la hauteur de l'en-tête**, quelle qu'elle soit.
3. Logo allégé (`assets\FS_Passion_logo\logo.svg`) ; l'ancien fichier n'est plus utilisé.

### Fabrication

Un seul script, `tools\build.py`, sert en local (`fabriquer.bat`) et sur GitHub Actions. Le résultat est écrit dans `build\release\`.

1. **`FSPassion.exe`** (PyInstaller, en mode dossier pour un démarrage plus rapide et moins d'alertes antivirus, sans UPX) :
   - seules les ressources utilisées sont embarquées ;
   - icône de l'exécutable ; Propriétés → Détails : nom, version, GPLv3 ;
   - le pack de démonstration est posé à côté : « Essayer sans le jeu » fonctionne hors ligne.
2. **Version portable** `FSPassion-X.Y.Z-portable.zip` : le même dossier, plus `portable.txt`. Réglages, journaux, caches et langues personnelles restent dans `data\` à côté de l'exécutable. Supprimer `portable.txt` revient au mode installé.
3. **Installeur** `FSPassion-X.Y.Z-setup.exe` (Inno Setup), en français ou en anglais :
   - sans droits administrateur par défaut, pour l'utilisateur courant ; pour tous les utilisateurs si on le choisit ;
   - WebView2 installé seulement s'il manque (Windows 10) ;
   - raccourci dans le menu Démarrer, sur le Bureau si on le coche ; « Lancer FS Passion » à la fin ;
   - FS Passion doit être fermé pour installer ou désinstaller ;
   - Windows 10 (1809 et plus) et 11, 64 bits.
4. **Désinstalleur** : ouvre la fenêtre « Ne plus utiliser FS Passion ». Fermée sans confirmer (Annuler ou la croix), elle rétablit quand même la ligne d'override de chaque version, sans rien supprimer. Une version dont le jeu tourne est laissée. Option `--uninstall-quiet` pour une désinstallation silencieuse. Le réglage « Exécuter en tant qu'administrateur » posé par FS Passion est retiré. Les dossiers de mods ne sont jamais touchés.
5. **Empreintes** `SHA256SUMS.txt`, publiées avec les fichiers.
6. **GitHub Actions** : à chaque envoi sur la branche principale et à chaque demande de fusion, contrôle de style, tests et fabrication complète ; fichiers téléchargeables pendant 30 jours. À chaque étiquette `vX.Y.Z`, la même fabrication puis un brouillon de publication (Releases) avec l'installeur, la version portable et les empreintes. L'étiquette doit correspondre à la version du projet.

Fichiers non signés : un avertissement SmartScreen peut apparaître (« Informations complémentaires » → « Exécuter quand même ») jusqu'à la signature prévue.

## 0.7.9 — 25 octobre 2026 — langues, molette, atelier, icônes, redimensionnement

**Aucun fichier du jeu ni des mods n'est touché** (le cache des icônes des anciennes versions est seulement allégé).

### Ce qui change

1. **Paramètres → Langue** : liste sobre, de simples lignes de texte ; la langue choisie est dans la couleur d'accent.
2. **Molette dans les Paramètres** : dans la section Thème, un cran avance d'une rangée de pastilles.
3. **Atelier de thèmes** : hauteur limitée à 640 px. Les réglages défilent, et les boutons Enregistrer, Copier la définition et Nouveau restent visibles ; la position de défilement est conservée.
4. **Cache des icônes** : la variante 300 px n'est créée que pour FS25 et FS28. Avant FS25, la grande icône d'origine sert directement. Les variantes 300 px des anciennes versions sont effacées au prochain scan.
5. **Redimensionnement de la fenêtre** :
   - fiches des mods : pendant le redimensionnement, elles ne s'ouvrent plus et les fiches ouvertes se ferment ;
   - en-tête : il passe sur deux lignes sans alterner, et ne revient sur une ligne qu'avec une marge suffisante ;
   - logo de la version : il glisse régulièrement avec la largeur, sans saut.

## 0.7.8 — 25 octobre 2026 — thèmes définitifs

**Aucun fichier du jeu ni des mods n'est touché** : cette version ne change que l'interface.

### Ce qui change

1. **Thèmes bicolores** (Lime, Blanc, Jade, Cuivre), à deux couleurs seulement. Le rouge est remplacé par **Blanc** (blanc sur fond bleu `#272B3E`) ; si Rouge était le thème choisi, FS Passion passe à Blanc.
   - couleur sombre partout, couleur dominante dans les textes et les icônes ;
   - un trait fin de la couleur dominante autour des listes, fenêtres et sections ;
   - une lueur qui court le long des contours des listes, des fenêtres et des Paramètres ;
   - boutons à contour fin, avec une lueur au survol.
   - Les seules autres couleurs : le rouge des actions irréversibles, le jaune des avertissements, et les images des mods.
2. **Thèmes inspirés de thèmes populaires**, chacun en version sombre et claire : Catppuccin Mocha / Latte, Nord / Nord Snow, Solarized Dark / Light, Monokai Pro / Monokai Pro Light, Gruvbox Dark / Light, Dracula Van Helsing / Alucard, Tokyo Night / Tokyo Night Light, Synthwave '84 / Synthwave '84 Light.
   - Les fonds et les textes reprennent les couleurs officielles de chaque palette (sources : dépôts officiels des thèmes, catppuccin.com, nordtheme.com).
3. **Effet néon** : réglage « Néon » (0 à 100) dans l'atelier, pour tout thème ; lueur des titres, des icônes, des contours et des interrupteurs. Synthwave '84 : néon à 70 ; sa version claire : 35.
4. **Paramètres → Affichage → Thème** : trois groupes, « Bicolores », « Sombres », « Clairs ». Chaque thème sombre est placé au-dessus de son jumeau clair.
5. **« Effets de lumière »** coupe les lueurs des contours et le néon. **« Réduire les animations »** arrête les lueurs qui bougent. Elles s'arrêtent aussi quand la fenêtre n'est pas au premier plan.
6. **Atelier de thèmes** : style Bicolore, Palette officielle ou Voiles calculés. « Fond (Mica) » devient « Fond de la fenêtre » et « Accent » devient « Couleur dominante ».

Notes :
- Synthwave '84 n'a pas de version claire officielle : la version claire est une proposition.
- Monokai Pro et Dracula Pro sont des thèmes payants de leurs auteurs : seules leurs couleurs sont reprises, pas leurs fichiers, et le nom du thème permet de les reconnaître.
- Solarized n'a que deux fonds officiels par mode ; ils alternent dans l'interface.

## 0.7.7 — 25 octobre 2026 — retrait d'un DLC (FS17)

**Aucun fichier du jeu ni des mods n'est touché.**

1. **FS17 : Farming Classics retiré** du catalogue des DLC.

## 0.7.6 — 25 octobre 2026 — correctif des icônes 300 px, DLC retirés

**Aucun fichier du jeu ni des mods n'est touché.**

1. **Icônes 300 px** : les caches créés avant la 0.7.5 n'avaient pas cette variante. Ces entrées sont relues une fois au démarrage, puis les trois variantes (300 px, 512 px, 96 px) sont recréées.
2. **Entrées retirées du catalogue des DLC**, car ce ne sont pas des DLC (mods gratuits installés dans `mods`, ou codes à saisir en jeu) : FS2011 Classic Bale Equipment ; FS2013 Lamborghini R6.125 ; FS15 Farming Classics (Free) et Lamborghini Nitro ; FS17 Challenger MT700E Stealth Edition et Fendt 900 BlackBeauty ; FS19 John Deere Gator.

## 0.7.5 — 25 octobre 2026 — DLC absents, cache 300 et 512 px, icônes Exporter / Importer

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Paramètres > Exporter / Importer** : Exporter a la flèche vers le haut, Importer la flèche vers le bas.
2. **Cache des icônes, trois tailles** par mod : 300 px pour la liste 1, 96 px pour les listes 2 et 3, et une grande variante plafonnée à 512 px (écrans à 125 % et plus). Le cache est reconverti une fois au premier scan.
3. **DLC absents** : le catalogue affiche aussi les DLC non possédés, estompés en niveaux de gris. Ils ne sont jamais reconnus comme installés.
4. **Catalogue des DLC** : noms repris de la page wiki « Downloadable Content Packs » ; 16 DLC reconnus par leur nom de fichier, avec leur icône (FS15 à FS25) ; DLC absents ajoutés pour FS2011, FS2013, FS17 et FS19.

## 0.7.4 — 24 octobre 2026 — retouches : infobulle, langues, technique de la fenêtre

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Infobulle des liens** (fiche d'un mod) : une longue adresse sans espace passe à la ligne dans la bulle, comme pour toutes les infobulles.
2. **Paramètres → Affichage → Langue** : le bouton-liste est sur la ligne du titre. La liste s'ouvre par-dessus le reste, sans rien décaler ; au-delà de 360 px, elle défile à la molette. Elle se ferme par un choix, un clic ailleurs ou Échap, qui ne ferme que la liste.
3. **Technique de la fenêtre** : déplacée vers **Application**, sous « Fenêtre ». Ses trois boutons sont sur la ligne du titre.

## 0.7.3 — 24 octobre 2026 — mods requis et facultatifs des anciennes versions, fiche épinglée

**Aucun fichier du jeu ni des mods n'est touché** : cette version lit un peu plus le `modDesc.xml` et change l'interface.

### Ce qui change

1. **Balise `<SearchMods>`** (FS15, FS17…), lue en plus de `<dependencies>` :
   - `<mod>` : mod requis, qui rejoint les dépendances ;
   - `<optionalMod>` : mod facultatif, nouvelle catégorie.
   Un mod déclaré dans les deux balises ne compte qu'une fois. Au premier lancement, les mods sont relus une fois pour trouver ces balises.
2. **Fiche d'un mod** : dépendances requises, puis « N mods facultatifs », présents ou absents. Sous chaque mod qui a un lien de téléchargement, le nom du site ; l'adresse complète est dans l'infobulle.
3. **Bouton « i »** sur chaque tuile (touche I au clavier). Un clic épingle la fiche, qui reste à l'écran, défile si besoin, et dont les liens s'ouvrent dans le navigateur. Elle se ferme par sa croix, Échap, un clic ailleurs ou un nouveau clic sur « i ». Note affichée : « Liens donnés par l'auteur du mod, souvent anciens : la page n'existe parfois plus. »
4. **« ＋ Partie »** : les dépendances absentes ont leur lien. Une section « N mods facultatifs » propose une case par mod présent, décochée.
5. **« Ajouter aussi ses dépendances ? »** : les mods facultatifs présents sont proposés, décochés. S'il n'y a que des facultatifs, la fenêtre s'intitule « Ajouter aussi des mods facultatifs ? ».
6. **Sécurité des liens** : seules les adresses `http` ou `https` écrites dans le `modDesc.xml` du mod concerné sont ouvertes, sans identifiants, de 1000 caractères au plus. Les autres ne sont pas affichées.

## 0.7.2 — 24 octobre 2026 — redimensionnement de la fenêtre

**Aucun fichier du jeu ni des mods n'est touché** : cette version ne change que l'interface et la taille minimale de la fenêtre.

### Ce qui change

1. **Réduction de l'échelle plus tardive** : l'interface n'est réduite qu'en dessous de 1140 px de large. La hauteur ne change pas : la réduction commence sous 900 px.
2. **Liste « Tous les mods »** : deux colonnes de tuiles au minimum, trois à partir d'environ 1470 px, quatre à partir d'environ 1790 px. La recherche rétrécit, puis passe sur une ligne si la place manque. Le bandeau d'actions passe en deux colonnes (2 + 2) quand il ne tient plus sur une ligne.
3. **Listes 2 et 3** : inchangées.
4. **En-tête sur deux lignes** quand la fenêtre est étroite : « Partie en cours » et le menu des parties sur la première ligne, les boutons sur la seconde. Le passage se fait selon la place réelle (vers 1440 px en français, 1400 px en anglais). Correction : à 1600 px en français, la cloche et les paramètres sortaient de la fenêtre.
5. **Fenêtre Paramètres** : toujours 1240 px de large ; les marges diminuent avant que la fenêtre ne rétrécisse.
6. **Taille minimale de la fenêtre : 960 px de large** (contre 1280 px auparavant), 720 px de haut.

## 0.7.0 — 22 octobre 2026 — sauvegarde de la configuration, « Ne plus utiliser », catalogue des DLC distant

**Cette version peut modifier `gameSettings.xml` et supprimer des dossiers de parties**, mais seulement quand l'utilisateur clique sur « Ne plus utiliser FS Passion » et confirme. Les dossiers de mods ne sont jamais touchés.

### Ce qui change

1. **Dons** : titre « Soutenir le projet ». Le logo Buy Me a Coffee reste net au survol (animation d'arrivée corrigée, tasse en tracé vectoriel).
2. **Invitation au don** (popup de 10 secondes) supprimée. Le compteur d'ouvertures disparaît au prochain lancement.
3. **Exporter la configuration** (Paramètres → Application → Sauvegarde) : fichier `fspassion-export-AAAA-MM-JJ.json` proposé dans Documents. Il contient les réglages, les parties et les mods communs de chaque version, et les anomalies masquées. Aucun mod n'y figure, seulement leurs noms.
4. **Importer la configuration** : aperçu (date de l'export, versions, parties). L'option « Conserver vos chemins actuels », cochée par défaut, garde les chemins du PC. L'état précédent est sauvegardé dans `backups\` (les 10 derniers). Les parties des versions concernées sont remplacées, mais rien n'est appliqué avant « Appliquer ». L'override ne pointe jamais vers un dossier supprimé. Refusé pendant que le jeu tourne et en mode démonstration.
5. **Ne plus utiliser FS Passion** (Paramètres → Application) : invitation à exporter d'abord ; pour chaque version, le bilan de ce qui va se passer ; cases à cocher toutes décochées (parties, caches, réglages, journaux, langues personnelles) ; confirmation explicite.
   - l'override retrouve sa valeur d'origine, ou est désactivé si elle n'existe pas ;
   - les dossiers de parties sont vidés lien par lien, puis supprimés ; un fichier physique trouvé est mis de côté, jamais effacé ;
   - le réglage « Exécuter en tant qu'administrateur » posé par FS Passion est retiré ;
   - refusé tant qu'un jeu configuré tourne. L'option `--uninstall` ouvre directement cette fenêtre.
6. **Catalogue des DLC distant** : FS Passion lit le catalogue (`dlc/dlc_catalog.json`) et les icônes dans un dépôt GitHub public séparé, FSPassion-data, au plus une fois par jour, si la connexion Internet est activée. Seules les icônes manquantes des DLC présents sont téléchargées. Contrôles : adresses https uniquement, tailles limitées, format d'image vérifié, empreinte contrôlée si fournie ; une entrée abîmée est écartée. Le catalogue le plus récent (téléchargé ou embarqué) est utilisé. Paramètres → Application → Connexion Internet affiche la date, l'origine et le bouton « Vérifier maintenant ».
7. **Bienvenue** : le logo FS Passion remplace le texte.
8. **Notice** : rappel de sauvegarde ; « Cliquez Appliquer » dans la première utilisation ; rubrique « Garder ses parties » (export et import).
9. **Diagnostic** (« Copier le diagnostic ») : langue, thème, mode démonstration, Mode développeur de Windows, liens symboliques possibles, réglage administrateur, accès Internet, catalogue des DLC (date, origine, dernière erreur), et pour chaque version les dossiers de mods et les parties.
10. **Section « Performance » du diagnostic** : temps d'affichage de l'interface au démarrage, mise à l'échelle de Windows, fluidité du défilement des listes (images par seconde, images trop longues, pire image), durée du dernier scan, mémoire. Rien n'est affiché ni envoyé : les chiffres restent en mémoire jusqu'à la fermeture.

Autres : « Quitter » le mode démonstration pendant une conversion d'icônes ne peut plus échouer.

## 0.6.7 — 22 octobre 2026 — relance en administrateur corrigée, logo FS Passion, logo GitHub

### Ce qui s'est passé

Lors d'une relance en administrateur, la nouvelle instance démarrait pendant que l'ancienne tenait encore le port local : elle s'arrêtait aussitôt. Le port n'était libéré qu'à la fin complète du processus.

### Ce qui change

1. **Relance en administrateur** : le port est libéré à la fermeture. Au démarrage, FS Passion réessaie pendant 15 secondes si le port est encore occupé. Le journal indique si FS Passion tourne en administrateur.
2. **Logo FS Passion** dans l'en-tête et dans « À propos », à la place du texte. Il prend la couleur d'accent du thème.
3. **Pied de page** : au repos, le logo GitHub est centré avec le texte ; au survol, il glisse vers la gauche et le mot « GitHub » apparaît.
4. **`archiver_version.bat`** à la racine : double-clic pour créer l'archive de la version en cours. Une archive existante n'est jamais écrasée.

## 0.6.6 — 22 octobre 2026 — retouches de l'interface, réinitialisation des thèmes, invitation au don

### Ce qui change

1. **Archives** : `tools\archive_version.py` crée une copie complète d'une version. Il refuse d'écraser une archive existante, exclut les dossiers régénérables et écrit `ARCHIVE.txt`.
2. **Lancement** : seule la fenêtre de l'application s'ouvre ; le navigateur n'est plus lancé.
3. **En-tête** : le logo Farming Simulator et l'icône de version sont plus proches. La rangée des versions, au survol, est de nouveau centrée sous son icône.
4. **Liste 3** : « Non incluse dans cette partie » est sur sa propre ligne, alignée à droite.
5. **Thèmes** : les pastilles ont un espacement régulier.
6. **Réinitialiser les thèmes** (Paramètres → Affichage) : remet le thème par défaut et les options des thèmes. Sans confirmation.
7. **Paramètres** : les pages se terminent par leur dernier bloc, sans bande vide.
8. **Dons** : Stripe en violet ; Buy Me a Coffee reprend ses couleurs d'origine.
9. **Pied de page** : le logo GitHub parcourt moins de chemin ; en thème clair, le numéro de version est lisible.
10. **Invitation au don, une seule fois** : à la dixième ouverture, un message reste 10 secondes en bas à droite, avec les logos Stripe et Buy Me a Coffee cliquables, puis ne revient plus. Le compteur est local, et aucune donnée n'est envoyée.

## 0.6.5 — 22 octobre 2026 — liens GitHub et dons, dépôt GitHub

### Ce qui change

1. **Liens actifs** : GitHub (pied de page et À propos), et les dons par Buy Me a Coffee et Stripe.
2. **Ouverture des liens plus sûre** : l'interface ne transmet aucune adresse ; elle désigne un lien prévu par son nom, et seules les adresses https des domaines prévus sont ouvertes dans le navigateur par défaut.
3. **À propos** : « FS Passion est un projet indépendant, non affilié à GIANTS Software. Farming Simulator est une marque de GIANTS Software. » (français et anglais).
4. **Dépôt GitHub** : premier envoi du projet. README public en français et en anglais : présentation, lancement, emplacement des fichiers, signalement, dons, mentions légales et mention GIANTS. Les dossiers « Old versions » et « Recovered » y prennent leurs noms.
5. **PayPal retiré** : la page Dons montre les deux logos restants, centrés.
6. **`FUNDING.yml`** : bouton « Sponsor » vers Buy Me a Coffee et Stripe.

## 0.6.4 — 21 octobre 2026 — dégradé bicolore, teinte des images, logo doublé, préparation GitHub

### Ce qui change

1. **Dégradé de deux couleurs** par thème (champ `gradient`), par exemple Catppuccin Mocha : Flamingo → Mauve. Le dégradé ne s'applique qu'à quelques textes importants (« FS » du logo, titres des listes, titres des Paramètres) ; les icônes, logos, images et interrupteurs restent en couleurs pleines. « Appliquer » et « Lancer le jeu » ont un dégradé qui défile en continu, arrêté si « Réduire les animations » est actif.
2. **Teinte des images** : elle prend la couleur principale du thème (et non la couleur de zone) dans les listes 1, 2 et 3.
3. **Logo Farming Simulator doublé** dans l'en-tête, aligné sur les chiffres du logo de version.
4. **Logo de version** : plus de fond au survol.
5. **Atelier de thèmes** : réglage « Dégradé bicolore » (départ, arrivée).
6. **Préparation de la publication GitHub** : `.gitignore` corrigé (les données de l'application étaient exclues par erreur), fins de ligne Windows pour les fichiers `.bat`, bouton « Sponsor », modèles de signalement « Signaler un problème » et « Proposer une idée », en français et en anglais.

## 0.6.3 — 21 octobre 2026 — thèmes clairs et multicolores, logo, retouches

### Ce qui change

1. **Logo Farming Simulator** dans l'en-tête, à gauche de l'icône de version. Il prend la couleur des textes.
2. **Icônes Lucide** agrandies de 10 %.
3. **Paramètres : défilement par sous-sections** : un cran de molette avance d'un chemin, d'un réglage ou d'un bloc.
4. **Teinte des images** (listes 1, 2 et 3) : voile de la couleur d'accent réduit de 0,20 à 0,12 ; réglable dans `ui\css\base.css` (variable `--tile-tint`).
5. **Partie Pleine** : « Idéal pour faire les mises à jour des mods en jeu » sous son nom.
6. **Thèmes clairs et sombres** :
   - bouton soleil/lune dans l'en-tête, qui passe au thème jumeau (Catppuccin Mocha ↔ Latte, Nord ↔ Nord Snow) ;
   - interface claire complète : textes sombres, surfaces plus claires que le fond, couleurs d'état de Windows 11 ;
   - quatre nouveaux thèmes aux couleurs officielles : Catppuccin Mocha et Latte, Nord et Nord Snow ;
   - plusieurs couleurs d'accent par thème (boutons des parties, listes, catégories, Paramètres), et des dégradés ;
   - lisibilité : un accent trop peu contrasté est ajusté en gardant sa teinte (4,5:1 au moins pour les textes, 3:1 pour les icônes) ;
   - atelier de thèmes : mode clair ou sombre, couleur des textes, plusieurs couleurs d'accent, thème jumeau.
7. **Correction** : la navigation au clavier du menu des parties (flèches, Échap) provoquait une erreur depuis la 0.5. Elle fonctionne de nouveau.

## 0.6.2 — 21 octobre 2026 — version plus ancienne déposée par le jeu : confirmation demandée

### Ce qui s'est passé

- Une mise à jour proposée par le jeu était plus ancienne que la version présente dans le dossier de mods. Elle était mise de côté sans que l'utilisateur soit consulté.
- Le lien vers la version présente n'était pas refait dans le dossier de la partie : le mod manquait jusqu'à la prochaine application.

### Ce qui change

1. **Fenêtre « Version plus ancienne téléchargée par le jeu »**, à la fermeture du jeu ou au démarrage : pour chaque mod, les deux versions, avec « Garder ma version » (rien ne change), « Utiliser celle du jeu » (la version présente va dans `Old versions`, et toutes les parties suivent) ou « Plus tard ».
2. Le lien vers la version présente est refait aussitôt : la partie garde le mod en attendant la décision.
3. **Dossiers en anglais** : `Recuperes` devient `Recovered`, et `Anciennes versions` devient `Old versions`. Les dossiers existants sont renommés automatiquement.
4. La notice mentionne ce cas, dans la rubrique « Les mises à jour ».

## 0.6.1 — 21 octobre 2026 — correction : relance en administrateur

### Ce qui s'est passé

La relance en administrateur démarrait Python directement, sans les réglages préparés par le lanceur de développement ; de plus, la case « administrateur » avait été cochée sur l'interpréteur Python de développement au lieu de l'application. FS Passion ne redémarrait donc pas.

### Ce qui change

- Un script de réparation (`reparer_admin.bat`) décoche ce réglage. FS Passion le retire aussi lui-même s'il le trouve au démarrage.
- En développement, « Relancer en administrateur » ne redémarre que pour cette fois, sans réglage permanent. La case « Toujours en administrateur » est réservée à l'application fabriquée.

## 0.6.0 — 20 octobre 2026 — stockage sur plusieurs disques, corrections de la 0.5

**Cette version crée des liens symboliques** dans les dossiers de parties, vers les mods situés sur d'autres disques. Les dossiers de stockage supplémentaires ne reçoivent jamais de fichier de FS Passion : une ancienne version y est copiée vers `Anciennes versions\` (disque principal), vérifiée, puis retirée.

### Ce qui change

1. **Stockage sur plusieurs disques** : Paramètres → Jeu et chemins → Dossiers de mods. Deux dossiers supplémentaires au maximum (n° 2 et n° 3). Chaque chemin est contrôlé (introuvable, chevauchement, doublon) ; un chemin en erreur est ignoré, pour qu'un mod ne soit jamais lu deux fois. Retirer un dossier ne touche pas à ses mods.
   - liste 1 : mods de tous les stockages, le détail indique le dossier ;
   - liens : hardlink pour un mod `.zip` du même disque, lien symbolique pour un mod d'un autre disque, jonction pour un mod non compressé ;
   - Partie Pleine : avec plusieurs stockages, dossier de liens vers tous les mods (`Parties\_pleine\`) ;
   - mises à jour du jeu : elles rejoignent le stockage d'où venait le mod ;
   - renommer et supprimer un mod suivent ses liens partout ;
   - téléchargements : colonne « Stockage » quand plusieurs stockages existent.
2. **Droits pour les liens symboliques** : si Windows les refuse (ni Mode développeur, ni administrateur), un encadré l'indique, avec « Obtenir les droits… » et « Vérifier à nouveau ». Sans droits, les mods des autres disques restent listés mais n'entrent dans aucune partie, et un avertissement le signale. Deux options : « Toujours lancer en administrateur » (avec ses conséquences) ou le Mode développeur de Windows.
3. **Choix de la version dans l'en-tête** : une seule icône, celle de la version en cours. Au survol, les versions s'ouvrent en rangée horizontale ; un clic choisit. Clavier : flèches gauche et droite, Échap.
4. **Repère de la liste 1** : chaque nom commence au même endroit pendant le défilement ; les trois premières lettres sont en couleur d'accent.
5. **Notifications réduites** : ne restent affichés que les erreurs, les avertissements, les téléchargements, la réconciliation et « Appliquer ».

## 0.5.0 — 20 octobre 2026 — repère, version en icônes, notifications réduites

**Aucun fichier du jeu ni des mods n'est touché** : cette version ne change que l'interface et le numéro de version.

### Ce qui change

1. **Repère alphabétique (liste 1)** : le texte est aligné à gauche, les trois premières lettres du nom sont en couleur d'accent. Les listes 2 et 3 gardent leur repère d'origine.
2. **Notifications réduites** : les messages de réussite (lancement, renommage, thème enregistré) ne sont plus affichés. Les erreurs et les avertissements restent.
3. **Version du jeu dans l'en-tête** : une rangée d'icônes. L'icône survolée grossit, un clic suffit, et la version active est soulignée d'un trait d'accent. FS28, à venir, reste visible, atténuée, sans réaction.

## 0.4.0 — 18 octobre 2026 — réconciliation, téléchargements, supprimer et renommer

**Cette version déplace des fichiers dans le dossier de mods** : téléchargements intégrés, mises à jour récupérées dans les parties et dans `pending_downloads`. Elle renomme et supprime des mods, mais seulement à la demande de l'utilisateur. Une version remplacée est toujours mise de côté dans `Anciennes versions\<date>\`, jamais effacée. Seul « Supprimer définitivement » supprime, en passant par la Corbeille.

### Ce qui change

1. **Arguments de lancement** : FS17 utilise `-restart` ; FS22 et FS25 utilisent `-skipStartVideos`.
   - **Steam** : FS Passion lance le jeu sans arguments, par `steam://`, donc sans demande de confirmation. Paramètres → Jeu et chemins montre où saisir les arguments, avec un bouton Copier.
   - **Epic Games** : même principe, avec son chemin indiqué.
   - **Microsoft Store / Xbox** : Windows ne prévoit pas de moyen de passer des arguments ; un encadré le signale.
   - **Console dans `game.xml`** : son état est affiché, avec un bouton « Activer dans game.xml ».
2. **Réconciliation** : remise en ordre de tous les dossiers de parties, sans rien demander, au démarrage, à la fermeture du jeu, avant chaque « Appliquer », et après une intégration, un renommage ou une suppression.
   - mise à jour déposée par le jeu dans une partie : rapatriée dans le dossier de mods, l'ancienne version est mise de côté, et les liens de toutes les parties sont refaits ;
   - lien orphelin : refait ; mod téléchargé par le jeu : rapatrié et ajouté à sa partie ;
   - fichiers de `pending_downloads` (jeu fermé) : les mods sont récupérés ; `pendingDownloadQueue.dat` n'est jamais modifié ;
   - version plus ancienne que celle du dossier de mods : mise de côté dans `Recovered\` ;
   - un message discret n'apparaît que s'il s'est passé quelque chose. Le contenu d'une partie ne change qu'avec « Appliquer ».
3. **Mods absents au démarrage** : une fenêtre (une fois par session) liste les mods manquants, avec pour chacun : **Restaurer dans Mods** (si une copie existe encore dans un dossier de partie), **Remplacer par…** (mod renommé par son auteur), **Retirer des listes** ou **Plus tard**.
4. **Mod décompressé puis recompressé** : le ModHub voyait une archive modifiée, car le dossier décompressé restait à côté de l'archive. La réconciliation suit maintenant la forme du mod. Un dossier et une archive de même nom côte à côte sont signalés (anomalie A9), car le jeu n'en charge qu'un.
5. **Téléchargements et intégration** : bouton « Rechercher de nouveaux mods dans les téléchargements ». La fenêtre « Nouveaux mods trouvés » indique pour chaque fichier l'état (nouveau, mise à jour, version plus ancienne, déjà présent), la version du jeu (modifiable) et la destination. Boutons : Intégrer, Ignorer ces fichiers, Plus tard. Intégrer déplace le fichier, avec vérification entre disques. Un doublon du navigateur `(1)` est intégré sous son nom de base. Une version plus ancienne ne remplace la version présente que si on coche sa case. Jeu ouvert : l'intégration est reportée à la fermeture.
6. **Supprimer définitivement** : une fenêtre liste les mods, leur taille et les parties qui les contiennent ; le bouton rouge n'est actif qu'après une case de confirmation. Le mod est retiré des listes et de toutes les parties, puis envoyé dans la Corbeille de Windows. Un mod non compressé est supprimé sans suivre de lien. Refusé pendant que le jeu tourne.
7. **Renommer un mod** : bouton du bandeau d'actions, touche F2, ou depuis une anomalie. Le fichier est renommé et son contenu ne change pas ; les liens des parties suivent. Une fenêtre demande ensuite si les listes doivent être mises à jour, avec un avertissement sur les effets (ModHub, sauvegardes du jeu, mods dépendants). Refusé pendant que le jeu tourne.
8. **Corrections** : la recherche trouve aussi les mods par le nom de leur auteur ; Ctrl pendant un glisser-déposer entre les listes 2 et 3 copie le mod ; la fenêtre des Paramètres est plus large ; les arguments de lancement et « Ne plus utiliser FS Passion » sont repliés par défaut.
9. **Notice** : nouvelle rubrique « Ajouter, renommer, supprimer des mods », qui recommande de supprimer les mods dans FS Passion plutôt que dans l'Explorateur.

## 0.3.0 — 18 octobre 2026 — « Appliquer » : le jeu charge vraiment la partie

**Première version qui écrit dans les dossiers du jeu** : les dossiers de parties (uniquement des liens) et la seule ligne `modsDirectoryOverride` de `gameSettings.xml`. Les mods ne sont jamais déplacés, copiés, modifiés ni supprimés.

### Ce qui change

1. **Appliquer** (bouton de l'en-tête) : calcul des mods actifs (mods de la partie et mods communs, sans doublon), construction d'un dossier de liens (hardlinks et jonctions), puis bascule en un seul geste ; l'ancien dossier est vidé lien par lien. Message : « Partie … appliquée : N mods ». Partie Pleine : l'override pointe sur le dossier de mods ; Partie Vide : sur un dossier vide. Le bouton est mis en évidence quand la partie n'est pas appliquée ou a été modifiée.
2. **`gameSettings.xml`** : seule la ligne d'override est remplacée. Une sauvegarde est faite avant chaque modification, puis un contrôle ; en cas d'échec, restauration automatique. La sauvegarde d'origine n'est jamais écrasée.
3. **Fichiers déposés par le jeu** dans un dossier de partie, traités avant chaque « Appliquer » : mise à jour (ancienne version mise de côté), version plus ancienne (mise de côté), mod inconnu (rejoint le dossier de mods et la partie), lien orphelin (refait).
4. **Renommer** une partie renomme aussi son dossier. **Supprimer la partie appliquée** réapplique la précédente de l'historique, ou la Partie Pleine.
5. **Jeu en cours** : Appliquer, renommer ou supprimer une partie qui a un dossier sont refusés.
6. **Journal d'opérations** : une opération interrompue par une coupure de courant est terminée ou annulée au démarrage suivant, avec un message.
7. **Contrôle de l'override au démarrage** : si le jeu charge un dossier inconnu, une fenêtre propose « Adopter comme dossier de mods », « Réappliquer » la partie ou « Ne rien faire ».
8. **Lancer le jeu** : si la partie sélectionnée n'est pas appliquée, FS Passion propose « Appliquer et lancer », « Lancer sans appliquer » ou Annuler.
9. **Ligne « Partie appliquée »** : courte ligne sous le menu des parties, qui signale aussi un jeu en cours ou un dossier inconnu.
10. **Paramètres** : sections séparées par un trait fin, avec une bande sur deux légèrement plus claire ; défilement par section à la molette.
11. **Pack de démonstration** : 103 faux mods pour FS25, FS22 et FS19, avec des maps, des dépendances et des icônes neutres générées. Proposé au premier lancement si aucun jeu n'est trouvé, et dans Paramètres → Jeu et chemins (« Essayer sans le jeu »). L'archive est vérifiée par son empreinte SHA-256 et décompressée dans le dossier local de FS Passion. Pendant la démonstration, un repère « Démonstration · Quitter » s'affiche ; « Quitter et tout effacer » supprime le pack et rétablit les vrais chemins.

## 0.2.2 — 17 octobre 2026 — refonte du design : Fluent / Mica

**Aucune fonction ne change**, et aucun fichier du jeu ni des mods n'est touché.

### Ce qui change

1. **Principe des thèmes** : la couleur sombre devient le fond « Mica » de la fenêtre. Les surfaces (listes, cartes, menus, fenêtres) sont des voiles neutres posés sur ce fond. La couleur claire devient l'accent (contours, icônes, sélection, bouton principal). Les textes sont blancs ou gris neutres.
2. **Fond Mica** : la couleur sombre, éclairée par deux grandes lueurs neutres et du grain. Réglage `mica` par thème.
3. **Calques et acrylique** : listes posées sur des calques, menus, bulles et bandeaux en verre dépoli. Les fenêtres ont des coins de 10 px et une bande de boutons plus sombre.
4. **Contrôles dans le style de Windows 11** : boutons, champs soulignés, interrupteurs, cases à cocher.
5. **Indicateur de sélection** : une petite barre d'accent à gauche de l'élément choisi.
6. **Tuiles de la liste 1** : coins de 8 px, léger soulèvement au survol. Les badges et repères sont des pastilles sombres en verre dépoli.
7. **Couleurs d'état** de Windows 11 : jaune pour les avertissements, rouge pour les erreurs et les actions irréversibles.
8. **Coins arrondis** : 6 px pour les contrôles, 8 px pour les cartes et tuiles, 10 px pour les menus et fenêtres.
9. **Thèmes fournis** : les couleurs claires d'origine sont conservées ; les fonds passent à des gris neutres proches de Windows 11.

## 0.2.1 — 16 octobre 2026 — retouches de la 0.2 et zone de notification

**Aucun fichier du jeu ni des mods n'est touché.**

### Ce qui change

1. **Textes agrandis** : noms des mods plus grands dans les listes (26 px dans la liste 1). Les autres textes passent de 15 à 19 px ; les petits textes et les infobulles sont aussi agrandis. Tout se règle dans `ui/css/base.css`.
2. **Nom complet des mods** partout, d'après la balise `<title>` du `modDesc.xml`, dans la langue de l'interface si elle existe. La recherche trouve aussi le nom du fichier.
3. **Images ajoutées** pour deux DLC : FS2013 (Classics Pack) et FS15 (New Holland Loader Pack).
4. **FS2011** : tout DLC dont le nom contient « profarm » s'intitule « ProFarm1 » et reçoit son image.
5. **Noms des DLC** : titres de la page du wiki, sans le préfixe « Farming Simulator XX - ».
6. **Icônes des anciens mods** : une icône déclarée dans des balises de langue est maintenant trouvée. Au premier lancement, les mods sont relus une fois pour cela.
7. **Tuiles des maps** : l'icône `farm.svg` est en bas à gauche de l'image ; « ＋ Partie » apparaît au centre, plus grand.
8. **Maps en tête** des « Non classés », puis en tête de la liste 2 (la liste 3 suit la même règle).
9. **Liste 1** : compteurs alignés sur le titre ; pointillés des mods non classés plus épais ; la fenêtre des dépendances indique quel mod les réclame.
10. **Fenêtre des anomalies** : version du jeu et dossier de mods en haut ; le nom de chaque élément ouvre l'Explorateur.
11. **Fenêtres superposées** : les bandeaux des Paramètres ne passent plus devant la fenêtre des anomalies.
12. **Notifications** : une cloche à côté des Paramètres garde les messages courts de la session, avec une pastille pour les messages non lus.
13. **Zone de notification** : une icône FS Passion près de l'horloge. Clic : la fenêtre revient. Clic droit : « Afficher FS Passion » ou « Quitter FS Passion ». Avec le réglage « Fermer dans la zone de notification » (actif par défaut), la croix cache la fenêtre ; « Quitter » ferme vraiment l'application. Le réglage « Revenir au premier plan quand le jeu se ferme » (actif par défaut) fait réapparaître la fenêtre à la fermeture du jeu.

Dépendance ajoutée : pystray (LGPL-3.0, compatible GPLv3).

## 0.2.0 — 16 octobre 2026 — les parties et le classement des mods

**Aucun fichier du jeu ni des mods n'est touché** : les parties n'existent que dans un fichier `parties.json` à côté du dossier de mods. « Appliquer » arrive en 0.3.

### Ce qui change

1. **Parties** : créer, dupliquer, renommer, supprimer, depuis l'en-tête. Le menu des parties affiche la map et le nombre de mods de chaque partie ; la Partie Pleine et la Partie Vide sont présentées à part. Chaque partie a son switch « Mods communs ». La partie appliquée est lue dans `gameSettings.xml`, avec un historique des 10 dernières. L'écriture du fichier est atomique, avec cinq sauvegardes ; un fichier illisible est remplacé par la sauvegarde valide la plus récente, et le fichier abîmé est mis de côté, jamais effacé.
2. **« ＋ Partie »** sur une map : le nom est prérempli avec le titre de la map, et les dépendances (y compris celles des dépendances) sont listées avec leur état. La partie reçoit la map et les dépendances présentes ; les absentes sont signalées pour être téléchargées.
3. **Listes 2 et 3** : tuiles horizontales, hauteurs partagées ; au survol, la liste qui déborde s'agrandit. Un cran de molette fait défiler trois tuiles. Un mod référencé mais absent est signalé, avec « Remplacer par… » pour rattacher un mod renommé par son auteur.
4. **Liste 1** : catégorie « Non classés » en tête ; repère d'appartenance (point plein : dans la partie ; anneau : dans les mods communs) ; compteurs Sélectionnés, Actifs, Tous.
5. **Sélection** : clic, Ctrl, Maj, lasso, Ctrl+A, Échap. Le clavier fonctionne dans les trois listes.
6. **Bandeau d'actions** : il apparaît dès qu'un mod est sélectionné, avec les boutons d'ajout et de retrait des parties et des mods communs.
7. **Glisser-déposer** entre les trois listes : liste 1 vers 2 (ajouter à la partie), vers 3 (mods communs), entre 2 et 3 (déplacer), vers 1 (retirer).
8. **Dépendances** : quand un mod ajouté à une liste a des dépendances absentes de celle-ci, FS Passion propose de les ajouter.
9. **Défilement sans délai** : une tuile qui entre pendant un défilement s'affiche aussitôt, son icône chargée dès qu'elle approche de la vue.

## 0.1.1 — 15 octobre 2026 — retouches de l'interface

### Ce qui change

1. **En-tête** 1,5 fois plus haut.
2. **Boutons de fenêtre** dans l'angle haut-droit, visibles au survol ; le bouton Fermer devient rouge au survol.
3. **Boutons des parties** sur la ligne du menu ; « Partie en cours » est affiché au-dessus.
4. **Icône de la version** à mi-distance du logo et de la barre « Partie en cours ».
5. **Bouton « Rechercher de nouveaux mods dans les téléchargements »**.
6. **Liste 1** : icônes moins grises, voile du thème plus léger ; affichage différé pendant un défilement, puis déploiement des tuiles ; une molette d'un cran fait défiler une rangée.
7. **Listes 2 et 3** : la liste 3 commence en haut de la moitié basse de la colonne.
8. **Pied de page** 1,5 fois plus haut. Le logo GitHub glisse au survol et laisse apparaître le mot « GitHub ».
9. **Paramètres** : quatre sections au lieu de onze (Version du jeu et chemins ; Général ; Dons ; À propos). Les chemins affichent « Trouvé » au survol, avec un cadre lumineux. Les drapeaux des langues sont supprimés.
10. **Police Iosevka Etoile Compact** dans toute l'interface.
11. **Icônes des DLC** : une couverture par DLC, copiée dans le dépôt de données et renommée d'après le fichier du DLC.

## 0.1.0 — 13 octobre 2026 — squelette complet en lecture seule

### Ce qui change

- **Lancement** de l'application dans sa fenêtre. Une seule instance : relancer FS Passion ramène la fenêtre existante.
- **Premier lancement** : bienvenue dans la langue de Windows (repli : anglais), choix de la langue, puis notice. La notice s'affiche à chaque démarrage tant que sa case reste cochée.
- **Détection des installations** : Steam (toutes les bibliothèques), Epic Games, Xbox / Game Pass, GIANTS (registre), Microsoft Store, dossiers « Farming Simulator » des disques fixes. Le dossier Documents de Windows est demandé au système. Un champ personnalisé n'est jamais modifié.
- **Paramètres** en sections : rangée des huit versions (FS28 « À venir »), chemins avec contrôle, téléchargements, langue, thèmes, notice, anomalies, journaux et diagnostic, dons, à propos.
- **Lecture des mods** : archives `.zip` et mods non compressés, lecture tolérante du XML, dépendances, version du jeu reconnue.
- **Cache** des mods à côté du dossier de mods : seuls les mods nouveaux ou modifiés sont relus.
- **Icônes** : DDS et PNG convertis en WebP à leur résolution d'origine, plus une variante de 96 px, en arrière-plan.
- **Liste 1** : catégories DLC, Maps, Autres mods ; recherche (accents ignorés, Ctrl+F) ; tuiles de 300 px ; détail d'un mod au survol, avec ses dépendances.
- **DLC** : fichiers des dossiers de DLC ; icônes lues dans le dépôt de données quand elles existent, sinon tuile générique.
- **Anomalies** dans une fenêtre qui s'ouvre quand il y en a de nouvelles.
- **Thèmes** Lime, Red, Jade et Cuivre, avec grain, reflet métallique du Cuivre, thème Loop et animations réductibles ; atelier de thèmes (outil de développement).
- **Fenêtre** sans barre de titre : boutons au survol de l'en-tête, déplacement par l'en-tête, redimensionnement par les bords, taille et position mémorisées, taille minimale 1280 × 720.
- **« Lancer le jeu »** par la plateforme (Steam, Epic, Xbox) ; FS Passion se réduit, puis affiche que le jeu est en cours d'exécution.
- **Journaux** avec rotation, et « Copier le diagnostic ».
- **Sauvegarde d'origine** `gameSettings.xml.original.bak`, créée une seule fois par version et jamais écrasée.
- **Sécurité** : serveur local sur `127.0.0.1` seulement, jeton secret par session, contrôle de l'origine des requêtes.
