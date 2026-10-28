; FS Passion — installeur Inno Setup 6.
;
; Compilé par tools/build.py, qui donne les valeurs suivantes :
;   /DAppVersion=X.Y.Z  /DSourceDir=build\dist\FSPassion  /DOutputDir=build\release
;   /DRootDir=<projet>  /DIconFile=build\fspassion.ico  [/DWebView2Setup=…exe]
;
; Choix :
; - installation pour l'utilisateur courant par défaut, sans droits
;   administrateur (%LOCALAPPDATA%\Programs\FS Passion), ou pour tous les
;   utilisateurs (Program Files) si on le choisit dans la première fenêtre ;
; - WebView2 installé seulement s'il manque (Windows 10) ;
; - désinstalleur : il lance d'abord « FSPassion.exe --uninstall » (fenêtre
;   « Ne plus utiliser FS Passion », 4.18 B) ; en désinstallation silencieuse,
;   « --uninstall-quiet » rétablit seulement la ligne d'override du jeu ;
; - les dossiers de mods ne sont jamais touchés ; les réglages (%APPDATA%) ne
;   sont supprimés que si on le coche dans FS Passion.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\dist\FSPassion"
#endif
#ifndef OutputDir
  #define OutputDir "..\build\release"
#endif
#ifndef RootDir
  #define RootDir ".."
#endif
#ifndef IconFile
  #define IconFile "..\build\fspassion.ico"
#endif

#define AppName "FS Passion"
#define AppExe "FSPassion.exe"
; Identifiant fixe : ne jamais le changer (mises à jour et désinstallation).
#define AppId "{{6E1C3B0A-58F2-4C7D-9A41-2F5B8D3E7C10}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=MichelMichel
AppPublisherURL=https://github.com/Michel-MichelMichel/FSPassion
AppSupportURL=https://github.com/Michel-MichelMichel/FSPassion/issues
AppUpdatesURL=https://github.com/Michel-MichelMichel/FSPassion/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename=FSPassion-{#AppVersion}-setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile={#RootDir}\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; FS Passion ouvert : l'installation et la désinstallation demandent de le fermer
; (même nom que le verrou d'instance unique de app.py).
AppMutex=Local\FSPassion.Instance,FSPassion.Instance
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} — installation

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
fr.DesktopIcon=Créer un raccourci sur le Bureau
en.DesktopIcon=Create a desktop shortcut
fr.LaunchApp=Lancer FS Passion
en.LaunchApp=Launch FS Passion
fr.WebView2Install=Installation de Microsoft Edge WebView2 (affichage de FS Passion)…
en.WebView2Install=Installing Microsoft Edge WebView2 (FS Passion display)…
fr.WebView2Failed=Microsoft Edge WebView2 n'a pas pu être installé. FS Passion s'ouvrira dans votre navigateur. Vous pouvez l'installer plus tard depuis le site de Microsoft.
en.WebView2Failed=Microsoft Edge WebView2 could not be installed. FS Passion will open in your browser. You can install it later from Microsoft's website.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifdef WebView2Setup
Source: "{#WebView2Setup}"; DestDir: "{tmp}"; DestName: "MicrosoftEdgeWebview2Setup.exe"; Flags: deleteafterinstall; Check: NeedsWebView2
#endif

[InstallDelete]
; Une version portable copiée par erreur dans le dossier d'installation ne doit
; pas faire passer FS Passion en mode portable.
Type: files; Name: "{app}\portable.txt"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
#ifdef WebView2Setup
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "{cm:WebView2Install}"; Flags: waituntilterminated; Check: NeedsWebView2
#endif
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
; La fenêtre « Ne plus utiliser FS Passion » (override rétabli, dossiers de parties
; retirés, suppressions au choix). Fermée sans confirmer, FS Passion rétablit quand
; même la ligne d'override. Le désinstalleur attend sa fin.
; Pas de Check : UninstallSilent ne peut pas être appelée pendant l'installation.
; skipifsilent n'est pas permis dans [UninstallRun] : la fenêtre s'affiche donc aussi
; en désinstallation silencieuse.
Filename: "{app}\{#AppExe}"; Parameters: "--uninstall"; Flags: waituntilterminated; RunOnceId: "FSPassionStopUsing"
Filename: "{app}\{#AppExe}"; Parameters: "--uninstall-quiet"; Flags: waituntilterminated runhidden; RunOnceId: "FSPassionStopUsingQuiet"

[Code]
const
  WebView2Key = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Version(Root: Integer; Key: String): String;
begin
  if not RegQueryStringValue(Root, Key, 'pv', Result) then
    Result := '';
end;

// WebView2 est présent (intégré à Windows 11, souvent déjà installé sous
// Windows 10) : rien à faire.
function NeedsWebView2(): Boolean;
var
  V: String;
begin
  V := WebView2Version(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Key);
  if (V = '') or (V = '0.0.0.0') then
    V := WebView2Version(HKLM, 'SOFTWARE\' + WebView2Key);
  if (V = '') or (V = '0.0.0.0') then
    V := WebView2Version(HKCU, 'Software\' + WebView2Key);
  Result := (V = '') or (V = '0.0.0.0');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and NeedsWebView2() and not WizardSilent() then
    MsgBox(CustomMessage('WebView2Failed'), mbInformation, MB_OK);
end;
