"""Cohérence de l'interface : icônes, police, logos et sections des paramètres (0.1.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fspassion import i18n

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "ui" / "js"
CSS = ROOT / "ui" / "css"


def _js_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(JS.glob("*.js")))


def test_every_ui_icon_exists():
    names = set(re.findall(r"\bicon\('([a-z0-9-]+)'", _js_text()))
    assert {"folder-sync", "window-close", "settings"} <= names
    missing = sorted(n for n in names if not (ROOT / "assets" / "icons" / f"{n}.svg").is_file())
    assert missing == []


def test_font_is_declared_and_present():
    css = (CSS / "base.css").read_text(encoding="utf-8")
    m = re.search(r'@font-face\s*{[^}]*url\("/assets/([^"]+)"\)', css)
    assert m, "@font-face absent"
    assert (ROOT / "assets" / m.group(1)).is_file()
    assert "font-synthesis: none" in css


def test_brand_files_present():
    text = _js_text()
    files = set(re.findall(r"/assets/brand/([A-Za-z-]+\.svg)", text))
    files |= set(re.findall(r"'([A-Za-z-]+\.svg)'", (JS / "settings.js").read_text(encoding="utf-8")))
    # 0.6.6 : Buy Me a Coffee en deux fichiers (pictogramme, texte), remplace Buymeacoffee.svg.
    assert {"github.svg", "github-text.svg", "Buymeacoffee-icon.svg", "Buymeacoffee-text.svg", "Stripe.svg"} <= files
    for f in files:
        assert (ROOT / "assets" / "brand" / f).is_file(), f


def test_settings_sections_have_titles():
    src = (JS / "settings.js").read_text(encoding="utf-8")
    block = src[src.index("const SECTIONS = ["): src.index("];", src.index("const SECTIONS = ["))]
    ids = re.findall(r"id: '([a-z]+)'", block)
    assert ids == ["game", "look", "app", "help"]
    for code in ("fr", "en"):
        strings = json.loads((ROOT / "lang" / f"{code}.json").read_text(encoding="utf-8"))
        for sid in ids:
            assert strings["settings"][sid]["title"], (code, sid)


def test_languages_have_no_flags():
    langs = i18n.Languages()
    assert langs.available()
    for lang in langs.available():
        assert set(lang) == {"code", "name", "personal"}


def _lang(code: str) -> dict:
    return json.loads((ROOT / "lang" / f"{code}.json").read_text(encoding="utf-8"))


def _exists(strings: dict, key: str) -> bool:
    node = strings
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def test_toast_and_dynamic_keys_exist():
    """Clés de langue passées à toast(…) et clés composées du classement (0.2)."""
    keys = set(re.findall(r"""\btoast\(\s*['"]([a-z0-9_]+(?:\.[A-Za-z0-9_]+)+)['"]""", _js_text()))
    assert {"apply.done", "apply.blocked", "plus.created_missing", "downloads.done", "reconcile.updated"} <= keys
    for what in ("added", "moved", "removed", "nothing"):
        for target in ("party", "common"):
            keys.add(f"actions.{what}_{target}")
    keys |= {"deps.needed_by_map", "deps.needed_by_mod", "deps.missing_for", "anomalies.show_in_folder",
             "anomalies.open_folder", "parties.recovered", "parties.lost",
             "parties.write_failed", "parties.running_rename", "parties.running_delete",
             # 0.4 : clés renvoyées par le cœur, et états composés
             "rename.empty", "rename.too_long", "rename.invalid", "rename.same", "rename.taken",
             "rename.not_found", "rename.failed", "rename.running", "delete.running", "delete.nothing",
             "downloads.failed", "downloads.gone", "downloads.unconfigured", "downloads.no_folder",
             "downloads.demo", "downloads.postponed_done", "move.exists", "move.no_space",
             "move.check_failed", "move.failed", "anomalies.A8.title", "anomalies.A8.explain",
             "missing.removed", "missing.restored", "missing.deleted"}
    for st in ("new", "update", "older", "present", "conflict", "unconfigured"):
        keys.add(f"downloads.state.{st}")
    for mode in ("command", "steam", "epic", "unsupported"):
        keys.add(f"settings.paths.args_help_{mode}")
    for plat in ("steam", "epic"):
        keys |= {f"settings.paths.args_{plat}_where", f"settings.paths.args_{plat}_steps"}
    for code in ("fr", "en"):
        strings = _lang(code)
        missing = sorted(k for k in keys if not _exists(strings, k))
        assert missing == [], (code, missing)


def test_party_ui_modules_present():
    """Les listes 2 et 3, la sélection, le glisser-déposer et le bandeau d'actions (0.2)."""
    for name in ("selection.js", "dnd.js", "actions.js", "actionbar.js", "sidelists.js"):
        assert (JS / name).is_file(), name
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'id="actionbar"' in html and 'id="preview"' in html


def test_list1_shows_tiles_without_delay():
    """0.2.0 : pendant un défilement, une tuile qui arrive s'affiche aussitôt
    (plus d'attente de la fin du défilement)."""
    src = (JS / "library.js").read_text(encoding="utf-8")
    assert "if (scrollActive && !el._shown) showNow(el);" in src
    assert "if (!scrollActive) reveal();" not in src


def _root_tokens() -> dict[str, str]:
    css = (CSS / "base.css").read_text(encoding="utf-8")
    block = css[css.index(":root {"): css.index("}", css.index(":root {"))]
    return dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", block))


def test_surfaces_are_neutral():
    """0.2.2 (Fluent / Mica) : les surfaces, voiles et traits sont neutres ;
    seul l'accent porte la couleur claire du thème."""
    tokens = _root_tokens()
    surfaces = [k for k in tokens if k.startswith(("--fill-", "--surface-", "--stroke", "--text-"))]
    surfaces += ["--layer", "--acrylic", "--scrim"]
    assert len(surfaces) > 20
    for k in surfaces:
        assert "--fg" not in tokens[k] and "--accent" not in tokens[k], k
    assert tokens["--accent"] == "var(--fg)"
    # Aucune feuille de style n'utilise plus les anciennes nuances teintées.
    for f in CSS.glob("*.css"):
        text = f.read_text(encoding="utf-8")
        for old in ("var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--raised", "var(--fg-2)", "var(--fg-3)", "var(--fg-4)"):
            assert old not in text, (f.name, old)


def test_themes_have_mica():
    data = json.loads((ROOT / "ui" / "themes.json").read_text(encoding="utf-8"))
    # 0.7.8 : 4 thèmes bicolores + 8 thèmes populaires en sombre et en clair.
    assert len(data["themes"]) == 20
    for th in data["themes"]:
        assert {"id", "name", "dark", "light", "grain", "mica", "effect", "effect_intensity"} <= set(th)
        assert 0 <= th["mica"] <= 100


def test_v04_modules_and_no_more_placeholders():
    """0.4 : renommer, supprimer, téléchargements et réconciliation ont leur
    module ; plus aucun bouton « disponible en 0.4 »."""
    for name in ("modops.js", "downloads.js", "reconcile.js"):
        assert (JS / name).is_file(), name
    text = _js_text()
    assert "'0.4'" not in text


# Notifications retirées (0.5 et 0.6) : un succès que l'interface montre déjà
# n'affiche plus de message. Les erreurs et avertissements restent.
REMOVED_TOASTS = {
    "launch.started", "rename.renamed", "rename.lists_done", "atelier.saved", "atelier.copied",
    "common.copied", "parties.created", "parties.duplicated", "parties.renamed", "parties.deleted",
    "plus.created", "settings.anomalies.reset_done",
}


def test_removed_notifications_stay_removed():
    js = _js_text()
    keys = set(re.findall(r"""\btoast\(\s*['"]([a-z0-9_]+(?:\.[A-Za-z0-9_]+)+)['"]""", js))
    assert keys & REMOVED_TOASTS == set()
    # Ajouter, déplacer ou retirer des mods : plus de message composé.
    assert "toast(`actions." not in js
    # Le lancement réussi ne dit rien ; un échec reste signalé.
    assert "if (!res.ok) toast(res.key" in js
    # Toujours affichés : démonstration, erreurs, suppression de la partie appliquée.
    assert {"demo.started", "demo.stopped", "parties.deleted_applied", "settings.logs.diag_copied"} <= keys


def test_light_dark_themes_and_pairs():
    """0.6.3 : Catppuccin (Mocha, Latte) et Nord (sombre, Snow) : un thème clair et
    un sombre chacun, jumeaux l'un de l'autre, avec 4 couleurs d'accent
    (orange, vert, bleu, violet) des palettes officielles."""
    data = json.loads((ROOT / "ui" / "themes.json").read_text(encoding="utf-8"))
    by_id = {th["id"]: th for th in data["themes"]}
    # 0.7.8 : « dark » = fond de la fenêtre = première surface officielle
    # (Crust pour Mocha, Overlay 0 pour Latte, nord0 et nord4 pour Nord).
    official = {
        "catppuccin-mocha": ("dark", "#11111B", ["#FAB387", "#A6E3A1", "#89B4FA", "#CBA6F7"]),
        "catppuccin-latte": ("light", "#9CA0B0", ["#FE640B", "#40A02B", "#1E66F5", "#8839EF"]),
        "nord": ("dark", "#2E3440", ["#D08770", "#A3BE8C", "#81A1C1", "#B48EAD"]),
        "nord-snow": ("light", "#D8DEE9", ["#D08770", "#A3BE8C", "#5E81AC", "#B48EAD"]),
    }
    for tid, (mode, bg, accents) in official.items():
        th = by_id[tid]
        # 0.7.4 : l'atelier n'écrit « mode » que pour un thème clair ; absent = sombre.
        assert th.get("mode", "dark") == mode and th["dark"] == bg and th["accents"] == accents
        pair = by_id[th["pair"]]
        assert pair["pair"] == tid and pair.get("mode", "dark") != mode
    # Les thèmes bicolores restent sombres, à une seule couleur (0.7.8 : le
    # rouge est remplacé par le blanc sur fond bleu, identifiant « blue »).
    assert "red" not in by_id
    for tid in ("lime", "blue", "jade", "cuivre"):
        assert by_id[tid].get("mode", "dark") == "dark" and "accents" not in by_id[tid]
        assert by_id[tid]["style"] == "duo"


def test_light_mode_and_theme_toggle_exist():
    css = (ROOT / "ui" / "css" / "base.css").read_text(encoding="utf-8")
    assert ':root[data-mode="light"]' in css and "--accent-grad" in css
    js = _js_text()
    assert "buildThemeToggle" in js and "oppositeTheme" in js
    for name in ("sun", "moon"):
        assert (ROOT / "assets" / "icons" / f"{name}.svg").is_file()


def test_two_color_gradient_no_rainbow():
    """0.6.4 : dégradé bicolore (Mocha : Flamingo #F2CDCD → Mauve #CBA6F7) pour
    quelques textes et les boutons Appliquer / Lancer le jeu ; plus de dégradé
    sur les icônes, logos de version, interrupteurs ni repères de sélection ;
    voile des images dans la couleur principale du thème."""
    data = json.loads((ROOT / "ui" / "themes.json").read_text(encoding="utf-8"))
    by_id = {th["id"]: th for th in data["themes"]}
    assert by_id["catppuccin-mocha"]["gradient"] == ["#F2CDCD", "#CBA6F7"]
    for tid in ("catppuccin-latte", "nord", "nord-snow"):
        assert len(by_id[tid]["gradient"]) == 2
    css = (ROOT / "ui" / "css" / "base.css").read_text(encoding="utf-8")
    assert "data-multi] .game-logo" not in css and "data-multi] .switch" not in css
    assert "grad-flow" in css and ".launch-btn.btn-primary" in css and ".apply-btn.btn-primary" in css
    lists = (ROOT / "ui" / "css" / "lists.css").read_text(encoding="utf-8")
    assert lists.count("background: var(--fg); /* couleur principale du thème") == 2
    assert "--tile-tint: .12;" in css
