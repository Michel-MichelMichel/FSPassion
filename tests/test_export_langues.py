"""0.9.2 : publication libre — plus de clé de licence ; export avec la flèche
vers le haut dans « Ne plus utiliser FS Passion »."""

from __future__ import annotations

import json
from pathlib import Path

from fspassion import config

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_old_licence_settings_are_dropped(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"licence_key": "FSP-0000-1111-2222-3333", "licence_ok_at": 5}), "utf-8")
    s = config.Settings(path)
    assert s.get("licence_key") is None and s.get("licence_ok_at") is None
    assert "licence_key" not in config.default_settings()


def test_stop_using_export_uses_up_arrow():
    stop = _read("ui", "js", "stopuse.js")
    assert "icon('file-up'), t('settings.backup.export')" in stop
    assert "icon('file-down'), t('settings.backup.export')" not in stop
    # Même icône que le bouton Exporter de Paramètres → Sauvegarde.
    assert "icon('file-up'), t('settings.backup.export')" in _read("ui", "js", "settings.js")


# ---------------------------------------------------------------------------
# Traductions (0.9.2) : chaque fichier de langue reprend toutes les clés de
# en.json, garde les variables {…} et donne les formes de pluriel attendues.
# ---------------------------------------------------------------------------

import re  # noqa: E402

_PLURAL = {"zero", "one", "two", "few", "many", "other"}
# Formes exigées en plus de « other » selon la langue (Intl.PluralRules).
_EXTRA_FORMS = {"pl": {"few", "many"}, "cs": {"few", "many"}}


def _is_plural(v):
    return isinstance(v, dict) and "other" in v and set(v) <= _PLURAL


def _compare(ref, tr, code, path, errors):
    if _is_plural(ref):
        if not _is_plural(tr):
            errors.append(f"{path}: pluriel attendu")
            return
        missing = (set(ref) | _EXTRA_FORMS.get(code, set())) - set(tr)
        if missing:
            errors.append(f"{path}: formes manquantes {sorted(missing)}")
        want = set(re.findall(r"\{(\w+)\}", " ".join(ref.values()))) - {"count"}
        got = set(re.findall(r"\{(\w+)\}", " ".join(tr.values())))
        if want - got:
            errors.append(f"{path}: variables perdues {sorted(want - got)}")
        return
    if isinstance(ref, dict):
        if not isinstance(tr, dict):
            errors.append(f"{path}: objet attendu")
            return
        for k in ref:
            if k == "_meta":
                continue
            if k not in tr:
                errors.append(f"{path}.{k}: absente")
            else:
                _compare(ref[k], tr[k], code, f"{path}.{k}", errors)
        return
    if isinstance(ref, list):
        if not isinstance(tr, list) or len(ref) != len(tr):
            errors.append(f"{path}: liste de longueur différente")
            return
        for i, (a, b) in enumerate(zip(ref, tr, strict=True)):
            _compare(a, b, code, f"{path}[{i}]", errors)
        return
    if not isinstance(tr, str):
        errors.append(f"{path}: texte attendu")
        return
    if sorted(re.findall(r"\{(\w+)\}", ref)) != sorted(re.findall(r"\{(\w+)\}", tr)):
        errors.append(f"{path}: variables différentes")


def test_every_language_file_is_complete():
    en = json.loads(_read("lang", "en.json"))
    codes = sorted(p.stem for p in (ROOT / "lang").glob("*.json"))
    for code in ("de", "es", "it", "pl", "pt-BR", "nl", "cs", "da", "fi", "nb", "sv", "pt-PT"):
        assert code in codes
    for code in codes:
        data = json.loads(_read("lang", f"{code}.json"))
        assert data["_meta"]["code"] == code and data["_meta"]["name"]
        errors: list[str] = []
        _compare(en, data, code, code, errors)
        assert errors == [], errors[:10]
