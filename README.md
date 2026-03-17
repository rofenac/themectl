# themectl

Unified theme switcher for **Alacritty**, **Vim**, **bat**, **vivid**, and **eza**.
One command — all tools update at once.

```
themectl set gruvbox
themectl set dracula
themectl set tokyonight
themectl set onedark
```

---

## Install

Requires Python 3.11+.

```bash
git clone <this-repo> ~/themectl
cd ~/themectl
pip install --user -e .
```

Or without pip:

```bash
alias themectl="python3 ~/themectl/themectl/main.py"
```

### Prerequisites

- **eza**: theme files cloned to `~/eza-themes/` with a symlink at `~/.config/eza/theme.yml` already pointing into that directory
- **vivid**: installed and in PATH
- **bat**: config at `~/.config/bat/config`
- **Vim**: `~/.vimrc` with an existing `colorscheme` line

---

## Usage

```
themectl set <theme>       Apply theme to all tools
themectl list              List available themes
themectl current           Show the currently active theme
themectl preview <theme>   Print a color palette swatch
```
