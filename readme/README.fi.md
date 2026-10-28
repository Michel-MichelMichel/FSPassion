# FS Passion

<img width="1004" alt="FS Passion" src="../assets/FS_Passion_logo/Final_grand.png" />

[English](../README.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Español (Latinoamérica)](README.es-419.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Português (Portugal)](README.pt-PT.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · **Suomi** · [Magyar](README.hu.md) · [Norsk bokmål](README.nb.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [简体中文](README.zh-Hans.md) · [繁體中文](README.zh-Hant.md)

Modienhallinta Farming Simulatoriin (FS2011–FS25), Windows 10:lle ja 11:lle.

Farming Simulatorin heikkous on, että siinä on vain yksi modikansio, johon kertyy paljon karttoja ja modeja, jotka eivät aina sovi yhteen. Siirtyminen pelikokoonpanosta toiseen on niin työlästä, että uusien karttojen kokeileminen jää helposti tekemättä.

FS Passionin ydin ratkaisee tämän ongelman hämmästyttävän tehokkaasti: luo muutamalla napsautuksella **kokoonpanoja** eli modikokoelmia ja vaihda niiden välillä yhdellä napsautuksella. Kaikki modisi pysyvät yhtenä kappaleena alkuperäisessä kansiossaan, Mods-kansiossa.

- **Kokoonpanot**: kartta, sen riippuvuudet ja valitsemasi modit; **yhteiset modit**, jotka kaikki kokoonpanot jakavat.
- **Päivitykset**: pelin tekemät päivitykset (ModHub) otetaan talteen ja niitä seurataan kaikissa kokoonpanoissa; korvattu versio siirretään sivuun, ei koskaan poisteta.
- **Lataukset**: uudet modit tunnistetaan ja siirretään oikean peliversion modikansioon.
- **Useita levyjä**: enintään kolme modikansiota eri levyillä.
- **Asetusten varmuuskopio**: kokoonpanojen ja asetusten vienti ja tuonti uudelleenasennusta tai toista tietokonetta varten.
- **Esittelykierros**: otsikkopalkin hehkulamppu esittelee käyttöliittymän minuutissa animoiduin esimerkein (versiot, kokoonpanot, luettelot, monivalinta, vedä ja pudota, pikanäppäimet).
- **Lopeta FS Passionin käyttö**: peli saa alkuperäisen asetuksensa takaisin ja kokoonpanokansiot poistetaan; modeihisi ei kosketa.
- Kaksiväriset **teemat** sekä suosittujen teemojen innoittamat teemat, tummat ja vaaleat (Catppuccin, Nord, Solarized, Monokai Pro, Gruvbox, Dracula, Tokyo Night, Synthwave '84).
- **Kielet**: käyttöliittymä 14 kielellä (English, Français, Deutsch, Español, Italiano, Português (Brasil), Português (Portugal), Nederlands, Polski, Čeština, Dansk, Suomi, Norsk bokmål, Svenska), valitaan Windowsin kielen mukaan ja vaihdettavissa asetuksista; voit lisätä oman käännöksesi. **Tulossa pian: 12 kieltä lisää**: Magyar, Română, Русский, Українська, Türkçe, Tiếng Việt, Bahasa Indonesia, Español (Latinoamérica), 日本語, 한국어, 简体中文, 繁體中文.
- **Demo**: sovellus on tarkoitettu vain Farming Simulator -pelien omistajille. Jos olet utelias ja haluat kokeilla ominaisuuksia ilman peliä, asetuksista löytyy esittelypaketti.

> ⚠️ Projekti on kehitysvaiheessa (versio: katso sivu [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases)). Tee täydellinen varmuuskopio modikansiostasi ennen kokeilua. Tämä GitHub-sivu on ainoa virallinen latauspaikka.

## Lataus

Sivulla [Releases](https://github.com/Michel-MichelMichel/FSPassion/releases):

- `FSPassion-X.Y.Z-setup.exe`: asennusohjelma nykyiselle käyttäjälle ilman järjestelmänvalvojan oikeuksia tai kaikille käyttäjille; asentaa tarvittaessa Microsoft Edge WebView2:n (Windows 10);
- `FSPassion-X.Y.Z-portable.zip`: siirrettävä versio ilman asennusta; asetukset ja lokit pysyvät kansiossa `data` tiedoston `FSPassion.exe` vieressä;
- `SHA256SUMS.txt`: molempien tiedostojen tarkistussummat.

Tiedostoja ei ole vielä allekirjoitettu: ensimmäisellä käynnistyskerralla Windows SmartScreen voi näyttää varoituksen; avaa lisätiedot ja valitse sovelluksen suorittaminen silti. SignPath Foundationin ilmainen allekirjoitus on suunniteltu ensimmäisen julkaisun jälkeen.

## Auta parantamaan käännöksiä

Äidinkielisten puhujien korjaukset ovat tervetulleita. Vaiheittainen ohje (English): [Help improve the translations](../README.md#help-improve-the-translations).

## Ilmoita ongelmasta, ehdota ideaa

Välilehti [Issues](https://github.com/Michel-MichelMichel/FSPassion/issues). Liitä ongelmailmoitukseen teksti kohdasta ”Kopioi diagnostiikka” (Asetukset → Ohje ja tietoja → Lokit ja diagnostiikka).

## Tue projektia

FS Passion on ja pysyy luotettavana, avoimen lähdekoodin ja maksuttomana projektina. Kertalahjoitus tekijälle vie muutaman sekunnin ilman tilin luomista: [Buy Me a Coffee](https://buymeacoffee.com/michel.michelmichel) tai [lahjoitus kortilla (Stripe)](https://donate.stripe.com/3cI00k2szgLvcx80Xdgfu00).

## Internet-yhteys

FS Passion muodostaa yhteyden vain GitHubiin lukeakseen DLC-luettelon (nimet ja kuvakkeet, julkinen `FSPassion-data`-repositorio), enintään kerran päivässä. Henkilötietoja ei lähetetä. Asetus ”Internet-yhteys” (Asetukset → Sovellus) poistaa sen käytöstä. Lisäksi se etsii GitHubista FS Passionin uutta versiota joka käynnistyksellä (sen jälkeen kerran päivässä): asetus ”FS Passionin päivitykset” (Asetukset → Sovellus) poistaa sen käytöstä.

## Lisenssi

FS Passion: **GPLv3** (tiedosto `LICENSE`), tekijä MichelMichel. Kehittäjien dokumentaatio ja täydet tekijätiedot (kuvakkeet, fontit, teemat): [englanninkielinen README](../README.md).

FS Passion on itsenäinen projekti, joka ei liity GIANTS Softwareen. Farming Simulator on GIANTS Softwaren tavaramerkki.
