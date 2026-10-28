"""Lecture des modDesc.xml et des archives (4.4, 4.12)."""

from __future__ import annotations

import zipfile

from fspassion import moddesc

import fakemods


def test_map_example_descriptor(data_dir):
    data = (data_dir / "modDesc_FS25_Carte_exemple.xml").read_bytes()
    info = moddesc.extract_info(data)
    assert info is not None
    assert info.desc_version == "96"
    assert info.version == "1.0.0.0"
    assert info.titles == {"en": "Carte exemple"}
    assert info.is_map
    assert info.map_titles == {"en": "Carte exemple"}
    assert info.icon_filename == "icon.png"
    assert info.multiplayer is True
    # La ligne en commentaire est ignorée : 8 dépendances, pas 9.
    assert len(info.dependencies) == 8
    assert "FS25_ExempleCommente" not in info.dependencies
    assert info.dependencies[0] == "FS25_ExempleTracteur_A"


def test_tolerant_bom_and_encoding():
    xml = '<?xml version="1.0" encoding="iso-8859-1"?><modDesc descVersion="40"><title><fr>Remorque à fourrage</fr></title></modDesc>'
    info = moddesc.extract_info(xml.encode("latin-1"))
    assert info.titles["fr"] == "Remorque à fourrage"
    bom = b"\xef\xbb\xbf" + '<modDesc descVersion="90"><title><en>Été</en></title></modDesc>'.encode()
    assert moddesc.extract_info(bom).titles["en"] == "Été"


def test_tolerant_bad_ampersand_and_fallback():
    info = moddesc.extract_info(b'<modDesc descVersion="61"><title><en>Pack A & B</en></title><version>1.0</version></modDesc>')
    assert info.titles["en"] == "Pack A & B"
    assert info.xml_ok
    broken = b'<modDesc descVersion="61"><title><en>Broken</en></title><version>2.0</version><maps><map></modDesc'
    info = moddesc.extract_info(broken)
    assert info is not None and not info.xml_ok
    assert info.desc_version == "61" and info.version == "2.0" and info.is_map


def test_not_a_moddesc():
    assert moddesc.extract_info(b"<gameSettings/>") is None


def test_l10n_inline_and_external():
    xml = (
        '<modDesc descVersion="96"><title>$l10n_myTitle</title>'
        '<l10n><text name="myTitle"><en>Big Trailer</en><de>Großer Anhänger</de></text></l10n></modDesc>'
    )
    info = moddesc.extract_info(xml.encode())
    assert info.titles == {"en": "Big Trailer", "de": "Großer Anhänger"}

    files = {
        "translations/l10n_en.xml": b'<l10n><elements><e k="t" v="Farm Pack"/></elements></l10n>',
        "translations/l10n_fr.xml": b'<l10n><texts><text name="t" text="Pack ferme"/></texts></l10n>',
    }
    xml2 = b'<modDesc descVersion="96"><title><en>$l10n_t</en><fr>$l10n_t</fr></title><l10n filenamePrefix="translations/l10n"/></modDesc>'
    info = moddesc.extract_info(xml2, files.get, lambda: list(files))
    assert info.titles == {"en": "Farm Pack", "fr": "Pack ferme"}


def test_find_icon_order():
    names = ["modDesc.xml", "icons/Icon_Big.dds", "store/icon_other.png"]
    assert moddesc.find_icon("icons/icon_big.dds", names) == "icons/Icon_Big.dds"  # casse ignorée
    assert moddesc.find_icon("icons/icon_big.png", names) == "icons/Icon_Big.dds"  # autre extension
    assert moddesc.find_icon("elsewhere/icon_other.dds", names) == "store/icon_other.png"  # par nom
    assert moddesc.find_icon("missing.dds", names) is None
    assert moddesc.find_icon("$data/icon.dds", names) is None


def test_read_zip_ok(tmp_path):
    p = fakemods.make_zip_mod(tmp_path, "FS25_Test", seed=1)  # icône déclarée .png, présente en .dds
    res = moddesc.read_zip(p)
    assert res.ok and res.icon_path == "icon_Test.dds"
    data = moddesc.read_icon_bytes(p, "zip", res.icon_path)
    assert data and data[:4] == b"DDS "


def test_read_zip_anomalies(tmp_path):
    nested = fakemods.write_zip(tmp_path / "pack.zip", {"inner/modDesc.xml": fakemods.moddesc_xml("x")})
    res = moddesc.read_zip(nested)
    assert res.anomaly == "A2" and res.detail["nested"] == "inner/modDesc.xml"

    empty = fakemods.write_zip(tmp_path / "empty.zip", {"readme.txt": "x"})
    assert moddesc.read_zip(empty).anomaly == "A2"

    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"not a zip")
    assert moddesc.read_zip(broken).anomaly == "A3"

    bad_xml = fakemods.write_zip(tmp_path / "badxml.zip", {"modDesc.xml": "<other/>"})
    assert moddesc.read_zip(bad_xml).anomaly == "A3"


def test_read_zip_never_writes(tmp_path):
    """I9 : l'archive n'est jamais modifiée."""
    p = fakemods.make_zip_mod(tmp_path, "FS25_Hash", seed=2)
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    moddesc.read_zip(p)
    with zipfile.ZipFile(p) as zf:
        assert zf.testzip() is None
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before


def test_read_dir(tmp_path):
    d = fakemods.make_dir_mod(tmp_path, "FS25_Dev", seed=3)
    res = moddesc.read_dir(d)
    assert res.ok and res.icon_path == "icon.png"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert moddesc.read_dir(empty).anomaly == "A4"


def test_icon_in_language_tags(tmp_path):
    """0.2.1 : FS2011 / FS2013 déclarent souvent l'icône dans des balises de langue."""
    xml = (
        '<modDesc descVersion="11"><title><en>Claas Lexion 770 TT</en></title>'
        "<iconFilename>\n  <en>store_package.dds</en>\n  <de>store_package.dds</de>\n"
        "  <fr>store_package.dds</fr>\n</iconFilename></modDesc>"
    )
    info = moddesc.extract_info(xml.encode())
    assert info is not None and info.icon_filename == "store_package.dds"
    # Lecture de repli (XML invalide) : même résultat.
    broken = xml.replace("</title>", "</title><bad & >")
    info = moddesc.extract_info(broken.encode())
    assert info is not None and info.icon_filename == "store_package.dds"
    p = fakemods.write_zip(tmp_path / "ClaasLexion770TT.zip", {
        "modDesc.xml": xml,
        "store_package.dds": fakemods.make_icon(3, fmt="dds"),
    })
    res = moddesc.read_zip(p)
    assert res.ok and res.icon_path == "store_package.dds"
