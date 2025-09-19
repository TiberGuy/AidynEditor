# AidynEditor

A Tkinter-based ROM editor for **Aidyn Chronicles**. It lets you open a `.z64` ROM, make targeted edits (party, enemies, items, shops/trainers, spells, wands/scrolls), and save changes byte-for-byte back into the ROM.

---

## Highlights

- **Backup-first** workflow: optional side-by-side backup created on launch.
- Editors for: Party, Enemies (incl. loot tables), Shops/Trainers, Accessories, Armor, Shields, Weapons, Spells, and Wands/Scrolls.
- Input guards (min/max and signed-byte helpers) to prevent many invalid values.
- Small toast-style **“Saved”** notifications anchored to the Save buttons.

> ⚠️ **New Game Only for some changes:** Party edits (and Becan’s special-case trainer changes) take effect on **new games** only. Existing save files might not reflect those changes.

---

## Requirements

- **Python** 3.9+
- **Tkinter** (bundled with most Python installers; on some Linux distros install `python3-tk`)

Windows example installer: the official python.org Windows installer includes Tkinter by default.  
Linux: `sudo apt install python3 python3-tk` (Debian/Ubuntu) or your distro equivalent.

---

## Quick Start

1. Ensure your Aidyn ROM file has the **`.z64`** extension.
2. Run the editor:
   ```bash
   python "AidynEditor Onefile.py"
   ```
3. Click **Browse** → choose your `.z64` ROM.  
   - **Backup** is on by default; keep it enabled unless you know what you’re doing.
4. The launcher appears with buttons for each editor section (Party, Enemy, Shop/Trainer, etc.). Click the section you want to edit.
5. Make your changes and click **Save** in that window.
6. A small “Saved” toast should appear near the Save button. If you see **“Save Failed”**, check the Troubleshooting section below.

---

## Editors Overview

All editors are opened as separate **Toplevel** windows. Lists are populated from the ROM using the address tables defined at the bottom of the file. Most fields are `Entry`/`Combobox` widgets tied to `StringVar`/`IntVar` with input guards.

### Party Edit
- Edit **name**, **aspect** (Solar/Lunar), **skills**, **attributes**, **level**, **weapons**, **armor**/**shield**, **spells** and **spell levels**, and **resists**.
- Blank skill fields typically mean **cannot learn**.
- Shield skill field treats blank as either `255` (party) or `0` (enemies) depending on the `char_type` logic.
- Applies primarily to **new games**.

### Enemy + Loot Edit
- All character-type fields (similar to Party) plus:
- **EXP** (display shows `75 × EXP`; capped to 19,125) and **loot drop type**.
- Loot editing exposes **gold ranges**, **drop chances**, **item picks**, and **stack sizes** for up to six items (two with min/max + chance; four with chance only).

### Shops / Trainer
- Shows trainer **skills**, **shield skill**, **spells** and **levels**, and the trainer’s **shop inventory** where applicable.
- “**Becan**” is a special case (party character). Blank vs `0` are written differently to preserve the new-game semantics.
- Trainers marked as **NOT_SHOPS** hide the shop panel.

### Accessory / Armor / Shield / Weapon
- Common pattern:
  - **Value** fields are little-endian (`v1, v2`) splits.
  - **Aspect**: None/Solar/Lunar (or numeric byte values).
  - **Attribute/Skill** bonus bytes use signed representation (negatives stored as unsigned by +256).
  - **Spell** and **Magic**: each has a **spell id** + **level**.
  - **Resist** and **Resist Amount** via the defined dictionaries.
- Weapon adds:
  - **Weapon Type**, **Damage Type**, **Range**, and **Animation** selectors.

### Wands & Scrolls
- **Wands**: damage/protection, reqs, aspect, skill bonus, spell + charges/level, resist + amount.
- **Scrolls**: value, spell, and cast level.

### Spell Edit

- Change **school**, **damage**, **stamina**, **wizard requirement**, **range**, **ingredient**, **target count**/**type**, **aspect**, and **EXP to rank**.

---

## Data Model Notes

- Mappings like `EQUIPMENT_STAT`, `SKILL_ATTRIBUTE`, `RESIST`, `RESIST_AMOUNTS`, `WEAPON_TYPE`, `WEAPON_ANIMATIONS`, etc., are defined at the bottom of the file.
- Name lengths and data sizes are fixed per editor (examples):
  - Party names: **9** chars
  - Enemy names: **17** chars
  - Accessory: `data_seek=24`, `data_read=20`, `name_length=20`
  - Armor/Shield: `data_seek=26`, `data_read=25`, `name_length=22`
  - Weapon: `data_seek=23`, `data_read=25`, `name_length=21`
  - Wands/Scrolls: `data_seek=24`, `data_read=20`, `name_length=18`
  - Spells: `data_seek=25`, `data_read=11`, `name_length=22`

- Negative stat fields are encoded as unsigned bytes:
  - Example: a UI value of `-5` is stored as `251` (`-5 + 256`) on write, and decoded back on read (`>127 → value-256`).

---

## Troubleshooting

**“Save Failed” toast**
- The ROM file is read-only or locked by another process.
- A field contains an invalid value after input guards (e.g., empty string where a byte is required).
- Your Python/Tkinter is missing or mismatched; ensure `tkinter` imports work from a REPL.

**Can’t find Browse dialog / UI looks off**
- On Linux, install your distro’s Tk packages (e.g., `python3-tk`). Try a different desktop theme if text is cramped.

**“File is empty / bad extension”**
- The opener enforces `.z64`. Make sure your ROM is correctly dumped and not zero bytes.

**Backups**
- If backup creation fails, the app shows an error and stops. Check write permissions in the ROM directory.
