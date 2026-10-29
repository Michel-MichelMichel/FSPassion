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
; - désinstalleur : il pose lui-même ses questions dans une petite fenêtre
;   Windows (suppressions en plus, aucune cochée par défaut), sans ouvrir
;   FS Passion, puis lance « FSPassion.exe --uninstall-quiet --remove … » sans
;   fenêtre : réglage du jeu rétabli, dossiers de parties retirés. Jeu ouvert :
;   il demande de le fermer (« --uninstall-check », avant toute suppression).
;   En désinstallation silencieuse : aucune question, aucune suppression en plus ;
; - les dossiers de mods ne sont jamais touchés ; les réglages (%APPDATA%) ne
;   sont supprimés que si on le coche.

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
fr.StartMenuIcon=Créer un raccourci dans le menu Démarrer
en.StartMenuIcon=Create a Start menu shortcut
fr.LaunchApp=Lancer FS Passion
en.LaunchApp=Launch FS Passion
fr.WebView2Install=Installation de Microsoft Edge WebView2 (affichage de FS Passion)…
en.WebView2Install=Installing Microsoft Edge WebView2 (FS Passion display)…
fr.WebView2Failed=Microsoft Edge WebView2 n'a pas pu être installé. FS Passion s'ouvrira dans votre navigateur. Vous pouvez l'installer plus tard depuis le site de Microsoft.
en.WebView2Failed=Microsoft Edge WebView2 could not be installed. FS Passion will open in your browser. You can install it later from Microsoft's website.
fr.UninstTitle=Désinstaller FS Passion
en.UninstTitle=Uninstall FS Passion
fr.UninstIntro=Le jeu va retrouver son réglage d'origine et les dossiers de parties de FS Passion seront retirés (ils ne contiennent que des liens). Vos dossiers de mods ne sont jamais touchés, ni « Old versions » et « Recovered », qui contiennent des mods mis de côté.
en.UninstIntro=The game will get its original setting back and FS Passion's setup folders will be removed (they only contain links). Your mods folders are never touched, nor “Old versions” and “Recovered”, which contain mods set aside.
fr.UninstOptions=Supprimer aussi :
en.UninstOptions=Also delete:
fr.UninstParties=les parties et les mods communs (parties.json)
en.UninstParties=setups and common mods (parties.json)
fr.UninstCaches=les caches (icônes converties, catalogue des DLC)
en.UninstCaches=caches (converted icons, DLC catalog)
fr.UninstSettings=les réglages de FS Passion
en.UninstSettings=FS Passion settings
fr.UninstLogs=les journaux
en.UninstLogs=logs
fr.UninstLangs=les langues personnelles
en.UninstLangs=personal languages
fr.UninstKeepHint=Rien n'est coché : vous retrouverez vos parties et vos réglages si vous réinstallez FS Passion.
en.UninstKeepHint=Nothing is ticked: you will get your setups and settings back if you reinstall FS Passion.
fr.UninstContinue=Continuer
en.UninstContinue=Continue
fr.UninstGameRunning=Farming Simulator est ouvert. Fermez le jeu, puis cliquez sur Réessayer : son réglage doit être rétabli jeu fermé.
en.UninstGameRunning=Farming Simulator is running. Close the game, then click Retry: its setting must be restored while the game is closed.
fr.UninstFailed=Le réglage du jeu n'a pas pu être rétabli pour au moins une version. Le journal de FS Passion donne le détail.
en.UninstFailed=The game setting could not be restored for at least one version. FS Passion's log gives the details.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"
Name: "startmenuicon"; Description: "{cm:StartMenuIcon}"

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
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
#ifdef WebView2Setup
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "{cm:WebView2Install}"; Flags: waituntilterminated; Check: NeedsWebView2
#endif
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent runasoriginaluser
; Mise à jour lancée depuis FS Passion (installation silencieuse, /RELAUNCH=1) :
; FS Passion est relancé à la fin, avec les droits de l'utilisateur.
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: RelaunchAfterUpdate

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

// Mise à jour depuis FS Passion : setup.exe /SILENT … /RELAUNCH=1.
function RelaunchAfterUpdate(): Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

// --------------------------------------------------------------------------
// Désinstallation : questions posées ici, FS Passion n'est pas ouvert.
// --------------------------------------------------------------------------

var
  UninstallOptions: String;

function AppExePath(): String;
begin
  Result := ExpandConstant('{app}\{#AppExe}');
end;

// Lancé par FS Passion après « Ne plus utiliser FS Passion » : déjà fait.
function AlreadyStopped(): Boolean;
begin
  Result := ExpandConstant('{param:FSPDONE|0}') = '1';
end;

function RunApp(Params: String): Integer;
var
  Code: Integer;
begin
  Result := -1;
  if FileExists(AppExePath()) then
    if Exec(AppExePath(), Params, '', SW_HIDE, ewWaitUntilTerminated, Code) then
      Result := Code;
end;

// Jeu ouvert : on demande de le fermer, avant toute suppression.
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if UninstallSilent() or AlreadyStopped() then
    Exit;
  while RunApp('--uninstall-check') = 3 do
    if MsgBox(CustomMessage('UninstGameRunning'), mbError, MB_RETRYCANCEL) <> IDRETRY then
    begin
      Result := False;
      Exit;
    end;
end;

function AddBox(Form: TSetupForm; Caption: String; var Top: Integer): TNewCheckBox;
begin
  Result := TNewCheckBox.Create(Form);
  Result.Parent := Form;
  Result.Left := ScaleX(24);
  Result.Top := Top;
  Result.Width := Form.ClientWidth - ScaleX(36);
  Result.Height := ScaleY(20);
  Result.Caption := Caption;
  Result.Checked := False;
  Top := Top + ScaleY(24);
end;

procedure AddOption(Box: TNewCheckBox; Key: String);
begin
  if Box.Checked then
  begin
    if UninstallOptions <> '' then
      UninstallOptions := UninstallOptions + ',';
    UninstallOptions := UninstallOptions + Key;
  end;
end;

// Petite fenêtre Windows : ce qui va se passer, et les suppressions en plus
// (aucune cochée par défaut). Elle ne propose pas d'annuler : la désinstallation
// vient d'être confirmée.
procedure AskOptions();
var
  Form: TSetupForm;
  Intro, OptTitle, Hint: TNewStaticText;
  BParties, BCaches, BSettings, BLogs, BLangs: TNewCheckBox;
  OkButton: TNewButton;
  Top: Integer;
begin
  UninstallOptions := '';
  Form := CreateCustomForm(ScaleX(460), ScaleY(330), False, False);
  try
    Form.Caption := CustomMessage('UninstTitle');

    Intro := TNewStaticText.Create(Form);
    Intro.Parent := Form;
    Intro.AutoSize := False;
    Intro.WordWrap := True;
    Intro.Left := ScaleX(12);
    Intro.Top := ScaleY(12);
    Intro.Width := Form.ClientWidth - ScaleX(24);
    Intro.Height := ScaleY(72);
    Intro.Caption := CustomMessage('UninstIntro');

    OptTitle := TNewStaticText.Create(Form);
    OptTitle.Parent := Form;
    OptTitle.Left := ScaleX(12);
    OptTitle.Top := ScaleY(92);
    OptTitle.Caption := CustomMessage('UninstOptions');
    OptTitle.Font.Style := [fsBold];

    Top := ScaleY(114);
    BParties := AddBox(Form, CustomMessage('UninstParties'), Top);
    BCaches := AddBox(Form, CustomMessage('UninstCaches'), Top);
    BSettings := AddBox(Form, CustomMessage('UninstSettings'), Top);
    BLogs := AddBox(Form, CustomMessage('UninstLogs'), Top);
    BLangs := AddBox(Form, CustomMessage('UninstLangs'), Top);

    Hint := TNewStaticText.Create(Form);
    Hint.Parent := Form;
    Hint.AutoSize := False;
    Hint.WordWrap := True;
    Hint.Left := ScaleX(12);
    Hint.Top := Top + ScaleY(4);
    Hint.Width := Form.ClientWidth - ScaleX(24);
    Hint.Height := ScaleY(36);
    Hint.Caption := CustomMessage('UninstKeepHint');

    OkButton := TNewButton.Create(Form);
    OkButton.Parent := Form;
    OkButton.Width := ScaleX(100);
    OkButton.Height := ScaleY(25);
    OkButton.Left := Form.ClientWidth - OkButton.Width - ScaleX(12);
    OkButton.Top := Form.ClientHeight - OkButton.Height - ScaleY(12);
    OkButton.Caption := CustomMessage('UninstContinue');
    OkButton.ModalResult := mrOk;
    OkButton.Default := True;

    Form.ActiveControl := OkButton;
    Form.ShowModal();

    AddOption(BParties, 'parties');
    AddOption(BCaches, 'caches');
    AddOption(BSettings, 'settings');
    AddOption(BLogs, 'logs');
    AddOption(BLangs, 'langs');
  finally
    Form.Free();
  end;
end;

// Juste avant la suppression des fichiers (FS Passion est fermé) : réglage du
// jeu rétabli, dossiers de parties retirés, suppressions choisies.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Params: String;
  Code: Integer;
begin
  if CurUninstallStep <> usUninstall then
    Exit;
  if AlreadyStopped() then
    Exit;
  if not UninstallSilent() then
    AskOptions();
  Params := '--uninstall-quiet';
  if UninstallOptions <> '' then
    Params := Params + ' --remove ' + UninstallOptions;
  Code := RunApp(Params);
  if (Code = 1) and not UninstallSilent() then
    MsgBox(CustomMessage('UninstFailed'), mbError, MB_OK);
end;
