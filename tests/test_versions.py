"""Reconnaissance de la version d'un mod : préfixe du fichier, puis DescVersion."""

from __future__ import annotations

import pytest

from fspassion import versions


@pytest.mark.parametrize(
    "name, expected",
    [
        ("FS25_HofBergmann", "FS25"),
        ("fs25_lowercase", "FS25"),
        ("LS22_Trailer", "FS22"),
        ("FS17Contest_Thing", "FS17"),
        ("FS19_Map", "FS19"),
        ("FS28_Future", "FS28"),
        ("LSFM22_Pack", None),      # « LSFM22_ » n'est pas reconnu par le préfixe
        ("FS2013_Something", None),  # « FS20… » n'est pas un code de version
        ("FS250_Odd", None),         # chiffre après le code : pas un préfixe
        ("Bergmann", None),
    ],
)
def test_prefix(name, expected):
    assert versions.version_from_prefix(name) == expected


@pytest.mark.parametrize(
    "desc, expected",
    [
        (4, "FS2011"), (6, "FS2011"), (8, "FS2011"),
        (9, "FS2013"), (19, "FS2013"),
        (20, "FS15"), (21, "FS15"), (29, "FS15"),
        (32, "FS17"), (39, "FS17"),
        (40, "FS19"), (53, "FS19"), (59, "FS19"),
        (60, "FS22"), (80, "FS22"), (89, "FS22"),
        (90, "FS25"), (114, "FS25"), (150, "FS25"), (999, "FS25"),  # plage ouverte
    ],
)
def test_desc_ranges(desc, expected):
    assert versions.version_from_desc(desc) == expected


def test_detection_order():
    # Préfixe prioritaire, avec avertissement en cas de désaccord.
    r = versions.detect_mod_version("FS25_Thing", "80")
    assert (r.version, r.source, r.warning) == ("FS25", "prefix", "conflict")
    # Sans préfixe : descVersion.
    r = versions.detect_mod_version("Thing", "96")
    assert (r.version, r.source) == ("FS25", "desc")
    # Attribut absent : valeur 1, donc non pris en charge (FS2009 ou plus ancien).
    assert versions.detect_mod_version("Thing", None).status == "unsupported"
    # Valeur illisible : inconnue.
    assert versions.detect_mod_version("Thing", "abc").status == "unknown"
    assert versions.detect_mod_version("Thing", "3").status == "unsupported"


def test_short_name():
    assert versions.short_name("FS25_HofBergmann") == "HofBergmann"
    assert versions.short_name("LS22_Trailer") == "Trailer"
    assert versions.short_name("bergmannShuttle900K") == "bergmannShuttle900K"
    assert versions.short_name("FS25_") == "FS25_"


def test_table_fs28_not_available():
    fs28 = versions.require("FS28")
    assert not fs28.available
    assert versions.require("FS2011").has_override is False
    assert versions.require("FS2011").dlc_folder == "pdlc2.1"


@pytest.mark.parametrize(
    "filename, desc, expected",
    [
        ("FS25_ExempleTracteur.zip", "97", "FS25"),
        ("FS25_ExempleMoissonneuse.zip", "108", "FS25"),
        ("FS22_ExempleSemoir.zip", "79", "FS22"),
        ("FS15_ExempleClassic.zip", "23", "FS15"),
        ("exemple_remorque.zip", "39", "FS17"),
        ("exemple_pulverisateur.zip", "44", "FS19"),
        ("exemple_chargeur.zip", "9", "FS2013"),
        ("exemple_fourgon.zip", "6", "FS2011"),
        ("exemple_moissonneuse.zip", "21", "FS15"),
    ],
)
def test_mod_version_from_prefix_or_descversion(filename, desc, expected):
    """Version reconnue d'après le préfixe du fichier ou, sans préfixe, d'après DescVersion."""
    res = versions.detect_mod_version(filename[:-4], desc)
    assert res.version == expected


def test_unreadable_descversion_gives_no_version():
    res = versions.detect_mod_version("exemple_illisible", "ZIP ILLISIBLE")
    assert res.version is None
