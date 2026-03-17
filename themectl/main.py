#!/usr/bin/env python3
"""
themectl — unified theme switcher for alacritty, vim, bat, vivid/eza
Usage:
    themectl set <theme>
    themectl list
    themectl current
    themectl preview <theme>   (prints a palette swatch)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
    except ImportError:
        sys.exit(
            "Error: requires Python 3.11+ or `pip install tomli`"
        )

# ──────────────────────────────────────────────
#  Paths  (edit these if yours differ)
# ──────────────────────────────────────────────
ALACRITTY_CONF  = Path("~/.config/alacritty/alacritty.toml").expanduser()
VIMRC           = Path("~/.vimrc").expanduser()
BAT_CONF        = Path("~/.config/bat/config").expanduser()
SHELL_RC        = Path("~/.zshrc").expanduser()   # where LS_COLORS lives
EZA_THEMES_DIR  = Path("~/eza-themes/themes").expanduser()
EZA_THEME_LINK  = Path("~/.config/eza/theme.yml").expanduser()
THEMES_DIR      = Path(__file__).parent.parent / "themes"
STATE_FILE      = Path("~/.config/themectl/current").expanduser()

# ──────────────────────────────────────────────
#  Theme loading
# ──────────────────────────────────────────────

def load_theme(name: str) -> dict:
    path = THEMES_DIR / f"{name}.toml"
    if not path.exists():
        available = [p.stem for p in THEMES_DIR.glob("*.toml")]
        sys.exit(
            f"Error: theme '{name}' not found.\n"
            f"Available: {', '.join(sorted(available))}"
        )
    with open(path, "rb") as f:
        return tomllib.load(f)


def list_themes() -> list[dict]:
    themes = []
    for p in sorted(THEMES_DIR.glob("*.toml")):
        with open(p, "rb") as f:
            data = tomllib.load(f)
        themes.append(data)
    return themes


def get_current() -> str | None:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return None

# ──────────────────────────────────────────────
#  Backup helper
# ──────────────────────────────────────────────

def backup(path: Path):
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".themectl.bak"))


# ──────────────────────────────────────────────
#  Alacritty
# ──────────────────────────────────────────────

def _alacritty_color_block(theme: dict) -> str:
    ac = theme["alacritty"]
    lines = []

    def section(name, mapping):
        lines.append(f"[colors.{name}]")
        for k, v in mapping.items():
            lines.append(f'{k} = "{v}"')

    section("primary",   ac["primary"])
    section("cursor",    ac["cursor"])
    section("selection", ac["selection"])
    section("normal",    ac["normal"])
    section("bright",    ac["bright"])
    return "\n".join(lines)


def apply_alacritty(theme: dict):
    if not ALACRITTY_CONF.exists():
        print(f"  [skip] alacritty config not found: {ALACRITTY_CONF}")
        return

    backup(ALACRITTY_CONF)
    text = ALACRITTY_CONF.read_text()

    # Strip every existing [colors.*] block
    text = re.sub(
        r"(?m)^\[colors(?:\.\w+)?\][^\[]*",
        "",
        text,
    ).rstrip()

    # Also strip the old themectl marker block if present
    text = re.sub(
        r"\n# --- themectl colors start ---.*?# --- themectl colors end ---",
        "",
        text,
        flags=re.DOTALL,
    ).rstrip()

    label  = theme["meta"]["label"]
    block  = _alacritty_color_block(theme)
    text  += (
        f"\n\n# --- themectl colors start --- ({label})\n"
        f"{block}\n"
        f"# --- themectl colors end ---\n"
    )

    ALACRITTY_CONF.write_text(text)
    print(f"  [ok]   alacritty → {ALACRITTY_CONF}")


# ──────────────────────────────────────────────
#  Vim
# ──────────────────────────────────────────────

def apply_vim(theme: dict):
    if not VIMRC.exists():
        print(f"  [skip] vimrc not found: {VIMRC}")
        return

    backup(VIMRC)
    text  = VIMRC.read_text()
    tname = theme["tools"]["vim"]
    extra = theme["tools"].get("vim_extra", {})
    ll    = theme["tools"].get("lightline", {})

    # Remove old vim_extra block (if present from a previous run)
    text = re.sub(
        r'\n" --- themectl vim_extra start ---.*?" --- themectl vim_extra end ---\n',
        "\n",
        text,
        flags=re.DOTALL,
    )

    # Build the replacement for the colorscheme line
    if extra:
        extra_vimlines = []
        for k, v in extra.items():
            varname = "g:" + k[2:]   # g_gruvbox_contrast_dark -> g:gruvbox_contrast_dark
            extra_vimlines.append(f"let {varname} = {v}")
        replacement = (
            '" --- themectl vim_extra start ---\n'
            + "\n".join(extra_vimlines)
            + '\n" --- themectl vim_extra end ---\n'
            + f"colorscheme {tname}"
        )
    else:
        replacement = f"colorscheme {tname}"

    # Single substitution: replace colorscheme line (with vim_extra prepended if needed)
    text = re.sub(r"(?m)^colorscheme\s+\S+", replacement, text)

    # Lightline colorscheme
    if ll.get("colorscheme"):
        text = re.sub(
            r"('colorscheme'\s*:\s*')[^']*(')",
            rf"\g<1>{ll['colorscheme']}\g<2>",
            text,
        )

    VIMRC.write_text(text)
    print(f"  [ok]   vim      → {VIMRC}")


# ──────────────────────────────────────────────
#  bat
# ──────────────────────────────────────────────

def apply_bat(theme: dict):
    BAT_CONF.parent.mkdir(parents=True, exist_ok=True)

    bat_theme = theme["tools"]["bat"]

    if BAT_CONF.exists():
        backup(BAT_CONF)
        text = BAT_CONF.read_text()
        # Replace existing --theme line
        if re.search(r"(?m)^--theme=", text):
            text = re.sub(r"(?m)^--theme=.*", f"--theme={bat_theme}", text)
        else:
            text = text.rstrip() + f"\n--theme={bat_theme}\n"
    else:
        text = f"--theme={bat_theme}\n"

    BAT_CONF.write_text(text)
    print(f"  [ok]   bat      → {BAT_CONF}")


# ──────────────────────────────────────────────
#  vivid / eza
# ──────────────────────────────────────────────

def apply_vivid(theme: dict):
    vivid_theme = theme["tools"]["vivid"]

    # Check vivid is installed
    if not shutil.which("vivid"):
        print("  [skip] vivid not found in PATH — install it to enable eza colors")
        return

    # Check that the theme exists in vivid
    result = subprocess.run(
        ["vivid", "generate", vivid_theme],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [warn] vivid doesn't know theme '{vivid_theme}': {result.stderr.strip()}")
        return

    if not SHELL_RC.exists():
        print(f"  [skip] shell rc not found: {SHELL_RC}")
        return

    backup(SHELL_RC)
    text = SHELL_RC.read_text()
    new_line = f'export LS_COLORS="$(vivid generate {vivid_theme})"'

    if re.search(r"(?m)^export LS_COLORS=", text):
        text = re.sub(r"(?m)^export LS_COLORS=.*", new_line, text)
    else:
        text = text.rstrip() + f"\n{new_line}\n"

    SHELL_RC.write_text(text)
    print(f"  [ok]   vivid    → {SHELL_RC}  (LS_COLORS → {vivid_theme})")


# ──────────────────────────────────────────────
#  eza
# ──────────────────────────────────────────────

def apply_eza(theme: dict):
    eza_theme = theme["tools"]["eza"]
    src = EZA_THEMES_DIR / f"{eza_theme}.yml"

    if not EZA_THEMES_DIR.exists():
        print(f"  [skip] eza themes dir not found: {EZA_THEMES_DIR}")
        return

    if not src.exists():
        print(f"  [warn] eza theme file not found: {src}")
        return

    EZA_THEME_LINK.unlink(missing_ok=True)
    EZA_THEME_LINK.symlink_to(src)
    print(f"  [ok]   eza      → {EZA_THEME_LINK} → {src}")


# ──────────────────────────────────────────────
#  Preview
# ──────────────────────────────────────────────

ANSI_COLORS = {
    "black": 0, "red": 1, "green": 2, "yellow": 3,
    "blue": 4, "magenta": 5, "cyan": 6, "white": 7,
}

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def preview(theme: dict):
    label = theme["meta"]["label"]
    ac    = theme["alacritty"]

    print(f"\n  {label} — color palette\n")

    bg_hex = ac["primary"]["background"]
    fg_hex = ac["primary"]["foreground"]
    bg     = hex_to_rgb(bg_hex)
    fg     = hex_to_rgb(fg_hex)

    bg_code = f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m"
    fg_code = f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]}m"
    reset   = "\x1b[0m"

    for group_name, group in [("normal", ac["normal"]), ("bright", ac["bright"])]:
        row = f"  {group_name:6s}  "
        for name, hex_val in group.items():
            r, g, b = hex_to_rgb(hex_val)
            row += f"\x1b[48;2;{r};{g};{b}m{fg_code}  {name[:3]}  {reset}"
        print(row)

    print(f"\n  bg {bg_hex}   fg {fg_hex}")
    print(f"  accent (cursor) {ac['cursor']['cursor']}\n")


# ──────────────────────────────────────────────
#  Save state
# ──────────────────────────────────────────────

def save_state(name: str):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(name + "\n")


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def cmd_set(args):
    theme = load_theme(args.theme)
    label = theme["meta"]["label"]
    print(f"\nApplying theme: {label}\n")

    apply_alacritty(theme)
    apply_vim(theme)
    apply_bat(theme)
    apply_vivid(theme)
    apply_eza(theme)
    save_state(args.theme)

    print(f"\nDone. Reload your shell and Alacritty to see all changes.")
    print("Vim: run  :source ~/.vimrc  or restart vim.")


def cmd_list(args):
    current = get_current()
    themes  = list_themes()
    print("\nAvailable themes:\n")
    for t in themes:
        name  = t["meta"]["name"]
        label = t["meta"]["label"]
        mark  = " ◀ current" if name == current else ""
        print(f"  {name:<16} {label}{mark}")
    print()


def cmd_current(args):
    current = get_current()
    if current:
        theme = load_theme(current)
        print(f"Current theme: {theme['meta']['label']} ({current})")
    else:
        print("No theme set yet. Run: themectl set <theme>")


def cmd_preview(args):
    theme = load_theme(args.theme)
    preview(theme)


def main():
    parser = argparse.ArgumentParser(
        prog="themectl",
        description="Unified theme switcher for alacritty, vim, bat, vivid/eza",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set",     help="Apply a theme to all tools")
    p_set.add_argument("theme",       help="Theme name (e.g. gruvbox, dracula)")
    p_set.set_defaults(func=cmd_set)

    p_list = sub.add_parser("list",   help="List available themes")
    p_list.set_defaults(func=cmd_list)

    p_cur = sub.add_parser("current", help="Show the currently active theme")
    p_cur.set_defaults(func=cmd_current)

    p_pre = sub.add_parser("preview", help="Print a color swatch for a theme")
    p_pre.add_argument("theme",       help="Theme name")
    p_pre.set_defaults(func=cmd_preview)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
