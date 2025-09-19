# ============================================================================
# Aidyn Editor — Code Walkthrough & Commentary
# ----------------------------------------------------------------------------
# A game editor for the N64 game Aidyn Chronicles
# ============================================================================

# stdlib
import sys
import shutil
from pathlib import Path
from functools import partial

# tkinter
import tkinter as tk
from tkinter import (
    Toplevel, Frame, Label, Button, Radiobutton, StringVar, IntVar,
    LabelFrame, Checkbutton, Entry, filedialog, messagebox
)
from tkinter.ttk import Combobox, Separator

# --- Characters: Base editor for reading/writing character records (party or enemy). Builds common UI and handles byte parsing from the ROM.
class Characters:
    # Init base character editor: prepare dictionaries, Tk variables, and common widgets.
    def __init__(self, f, a, n, r, t):
        self.win = Toplevel()
        self.win.resizable(False, False)
        self.win.geometry('+200+10')
        self.filename = f
        self.addresses = a
        self.name_length = n
        self.data_read = r
        self.char_type = t
        self.data_seek = 44

        # dictionaries and lists
        self.major_dic = get_major_item_dic(self.filename)
        self.inv_major_dic = {v: k for k, v in self.major_dic.items()}
        self.armor_lst = ['NONE'] + [item[8:] for item in self.major_dic.values() if item.startswith('(armor)')]
        self.shield_lst = ['NONE'] + [item[9:] for item in self.major_dic.values() if item.startswith('(shield)')]
        self.weapon_lst = ['NONE'] + [item[9:] for item in self.major_dic.values() if item.startswith('(weapon)')]
        self.spell_dic = get_minor_dic(self.filename, SPELL_DIC, 22)
        self.inv_spell_dic = {v: k for k, v in self.spell_dic.items()}
        self.character_list, self.character_addresses = get_major_name_lists(self.filename, self.addresses,
                                                                             self.name_length)

        # variables
        self.character = StringVar()
        self.character.trace('w', self.set_defaults)
        self.name = StringVar()
        self.name.trace('w', partial(limit_name_size, self.name, self.name_length))
        self.aspect = IntVar()
        self.skills = []
        for _ in SKILLS:
            i = StringVar()
            i.trace('w', partial(limit, i, 10))
            self.skills.append(i)
        self.shield_skill = StringVar()
        self.shield_skill.trace('w', partial(limit, self.shield_skill, 10))
        self.atts = []
        for i in range(6):
            i = StringVar()
            i.trace('w', partial(limit, i, 127))
            self.atts.append(i)
        self.level = StringVar()
        self.level.trace('w', partial(limit, self.level, 40))
        self.weapons = [StringVar() for i in range(3)]
        self.spells = [StringVar() for i in range(5)]
        self.schools = StringVar()
        self.spell_levels = []
        for i in range(5):
            i = StringVar()
            i.trace('w', partial(limit, i, 15))
            self.spell_levels.append(i)
        self.armor = StringVar()
        self.protection = StringVar()
        self.protection.trace('w', partial(limit_127, self.protection))
        self.shield = StringVar()
        self.resist1a = StringVar()
        self.resist1b = StringVar()
        self.resist2a = StringVar()
        self.resist2b = StringVar()

        # build items
        self.box = Frame(self.win)
        self.not_loot_frame = Frame(self.box)
        self.default_name_menu = Combobox()
        self.new_name_frame = LabelFrame(self.not_loot_frame, text="New Name")
        self.new_name_entry = Entry(self.new_name_frame, textvariable=self.name, width=19)
        self.save = Button(self.not_loot_frame, text="Save", command=self.write, width=8)
        self.aspect_frame = LabelFrame(self.not_loot_frame, text='Aspect')
        self.aspect = IntVar(value=2)
        self.solar_radio = Radiobutton(self.aspect_frame, text='Solar', variable=self.aspect, value=2)
        self.lunar_radio = Radiobutton(self.aspect_frame, text='Lunar', variable=self.aspect, value=1)
        self.school_spell_frame = Frame(self.not_loot_frame)
        self.school_frame = LabelFrame(self.school_spell_frame, text='School')
        self.school_box = Combobox(self.school_frame, textvariable=self.schools, width=12, state='readonly',
                                   values=list(SCHOOL.keys()))


        self.spell_frame = LabelFrame(self.school_spell_frame, text='Spells and Spell Level')
        self.spell = []
        self.spell_level = []
        for x in range(5):
            self.spell.append(
                Combobox(self.spell_frame, textvariable=self.spells[x], values=list(self.inv_spell_dic.keys()),
                         width=16, state='readonly'))
            self.spell_level.append(Entry(self.spell_frame, textvariable=self.spell_levels[x], width=4))
        self.resist_frame = LabelFrame(self.not_loot_frame, text='Resists')
        self.resist_menu1 = Combobox(self.resist_frame, textvariable=self.resist1a, values=list(RESIST.keys()),
                                     width=16, state='readonly')
        self.resist_amount_menu1 = Combobox(self.resist_frame, textvariable=self.resist1b, width=5,
                                            values=list(RESIST_AMOUNTS.keys()), state='readonly')
        self.resist_menu2 = Combobox(self.resist_frame, textvariable=self.resist2a, values=list(RESIST.keys()),
                                     width=16, state='readonly')
        self.resist_amount_menu2 = Combobox(self.resist_frame, textvariable=self.resist2b, width=5,
                                            values=list(RESIST_AMOUNTS.keys()), state='readonly')
        self.att_frame = LabelFrame(self.not_loot_frame, text='Attributes')
        self.level_entry = Entry(self.att_frame, textvariable=self.level, width=4)
        self.att_label = []
        self.att_num = []
        for x in range(6):
            self.att_label.append(Label(self.att_frame, text=ATTRIBUTES[x]))
            self.att_num.append(Entry(self.att_frame, textvariable=self.atts[x], width=4))
        self.protection_label = Label(self.att_frame, text='Base Protection')
        self.protection_entry = Entry(self.att_frame, textvariable=self.protection, width=4)
        self.equipment_frame = LabelFrame(self.not_loot_frame, text='Equipment')
        self.weapon_frame = LabelFrame(self.equipment_frame, text='Weapons')
        self.weapon_menu = []
        for x in range(3):
            self.weapon_menu.append(Combobox(self.weapon_frame, textvariable=self.weapons[x], values=self.weapon_lst,
                                             width=16, state='readonly'))
        self.armor_frame = LabelFrame(self.equipment_frame, text='Armor')
        self.armor_menu = Combobox(self.armor_frame, textvariable=self.armor, values=self.armor_lst, width=16,
                                   state='readonly')
        self.shield_frame = LabelFrame(self.equipment_frame, text='Shield')
        self.shield_menu = Combobox(self.shield_frame, textvariable=self.shield, values=self.shield_lst, width=16,
                                    state='readonly')
        self.skill_frame = LabelFrame(self.not_loot_frame)
        self.shield_num = Entry(self.skill_frame, textvariable=self.shield_skill, width=4)
        self.shield_label = Label(self.skill_frame, text='Shield', anchor='e', width=9)

    # Load current character bytes and populate all bound Tk variables.
    def set_defaults(self, *args):
        idx = self.default_name_menu.current()
        if idx < 0 or idx >= len(self.character_addresses):
            return
        with open(self.filename, 'rb') as f:
            address = self.character_addresses[idx]
            f.seek(address)
            self.name.set(f.read(self.name_length).decode("utf-8"))

            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # IntVar
            self.aspect.set(int(d[0:2], 16))

            # skills -> StringVar ('' when 255)
            for i, s in enumerate(self.skills):
                sn = int(d[6 + i * 2: 8 + i * 2], 16)
                s.set('' if sn == 255 else str(sn))

            # shield skill -> StringVar ('' when 255)
            shi = int(d[146:148], 16)
            self.shield_skill.set('' if shi == 255 else str(shi))

            # attributes -> StringVar
            for i, a in enumerate(self.atts):
                a.set(str(int(d[52 + i * 2: 54 + i * 2], 16)))

            # level -> StringVar
            self.level.set(str(int(d[66:68], 16)))

            # set_defaults: weapons
            for idx, w in enumerate(self.weapons):
                code = d[70 + idx * 4: 74 + idx * 4].upper()
                if code == '0000':
                    w.set(self.major_dic.get(code))
                else:
                    w.set(self.major_dic.get(code)[9:])

            # armor -> StringVar
            ar = d[136:140].upper()
            if ar == '0000':
                self.armor.set(self.major_dic[ar])
            else:
                self.armor.set(self.major_dic[ar][8:])

            # base protection -> StringVar
            self.protection.set(str(int(d[140:142], 16)))

            # shield -> StringVar
            sh = d[142:146].upper()
            if sh == '0000':
                self.shield.set(self.major_dic[sh])
            else:
                self.shield.set(self.major_dic[sh][9:])

            # school -> StringVar
            self.schools.set(inv_SCHOOL[d[106:108].upper()])

            # spells -> StringVar
            for i, sv in enumerate(self.spells):
                sv.set(self.spell_dic[d[86 + i * 4: 90 + i * 4].upper()])

            # spell levels -> StringVar
            for i, sv in enumerate(self.spell_levels):
                sv.set(str(int(d[108 + i * 2: 110 + i * 2], 16)))

            # resists -> StringVar
            self.resist1a.set(inv_RESIST[d[148:150].upper()])
            self.resist1b.set(inv_RESIST_AMOUNTS[d[150:152].upper()])
            self.resist2a.set(inv_RESIST[d[152:154].upper()])
            self.resist2b.set(inv_RESIST_AMOUNTS[d[154:156].upper()])

    # Serialize Tk values back to bytes and write to ROM; clamps/normalizes empty cases.
    def write(self):
        try:
            idx = self.default_name_menu.current()
            if idx < 0 or idx >= len(self.character_addresses):
                return
            with open(self.filename, 'rb+') as f:
                address = self.character_addresses[idx]
                new_name = bytearray(self.name.get(), 'utf-8')
                if len(new_name) < self.name_length:
                    while len(new_name) < self.name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                f.seek(address + self.data_seek)
                d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                towrite = [self.aspect.get(), (d[2] + d[3]),
                           (d[4] + d[5])]

                for i in self.skills:
                    j = i.get()
                    if j == '':
                        if self.char_type == 0:
                            j = 255
                        elif self.char_type == 1:
                            j = 0
                    towrite.append(j)

                for i in self.atts:
                    j = i.get()
                    towrite.append(j)

                towrite.append(d[64] + d[65])
                towrite.append(self.level.get())
                towrite.append(d[68] + d[69])

                for i in self.weapons:
                    w = i.get()
                    if w == 'NONE':
                        towrite.append(int((self.inv_major_dic[w])[:2], 16))
                        towrite.append(int((self.inv_major_dic[w])[2:], 16))
                    else:

                        towrite.append(int((self.inv_major_dic['(weapon) ' + w])[:2], 16))
                        towrite.append(int((self.inv_major_dic['(weapon) ' + w])[2:], 16))

                towrite.append(d[82] + d[83])
                towrite.append(d[84] + d[85])

                for i in self.spells:
                    towrite.append(int(self.inv_spell_dic[i.get()][:2], 16))
                    towrite.append(int(self.inv_spell_dic[i.get()][2:], 16))

                towrite.append(SCHOOL[self.schools.get()])

                for i in self.spell_levels:
                    towrite.append(i.get())

                for i in range(118, 136, 2):
                    towrite.append(d[i] + d[i + 1])

                a = self.armor.get()
                if a == 'NONE':
                    towrite.append(int((self.inv_major_dic[a])[:2], 16))
                    towrite.append(int((self.inv_major_dic[a])[2:], 16))
                else:
                    towrite.append(int((self.inv_major_dic['(armor) ' + a])[:2], 16))
                    towrite.append(int((self.inv_major_dic['(armor) ' + a])[2:], 16))

                towrite.append(self.protection.get())

                s = self.shield.get()
                if s == 'NONE':
                    towrite.append(int((self.inv_major_dic[s])[:2], 16))
                    towrite.append(int((self.inv_major_dic[s])[2:], 16))
                else:
                    towrite.append(int((self.inv_major_dic['(shield) ' + s])[:2], 16))
                    towrite.append(int((self.inv_major_dic['(shield) ' + s])[2:], 16))

                shi = self.shield_skill.get()
                if shi == '':
                    if self.char_type == 0:
                        shi = 255
                    elif self.char_type == 1:
                        shi = 0
                towrite.append(shi)

                towrite.append(int(RESIST[self.resist1a.get()], 16))
                towrite.append(int(RESIST_AMOUNTS[self.resist1b.get()], 16))
                towrite.append(int(RESIST[self.resist2a.get()], 16))
                towrite.append(int(RESIST_AMOUNTS[self.resist2b.get()], 16))

                f.seek(address + self.data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                self.reset_character_list()
                self.character.set(self.character_list[self.character_list.index(self.name.get().rstrip('\x00'))])
            self.set_defaults()

            flash_saved(self.save, "Saved")
        except (FileNotFoundError, PermissionError, OSError,
                KeyError, ValueError, UnicodeEncodeError) as e:
            # file missing/locked, bad dict key, bad int/hex, bad encoding
            flash_saved(self.save, "Save Failed")

    # Layout the common character editor widgets.
    def build(self):
        self.box.grid(column=0, row=0, pady=5, padx=5)
        self.not_loot_frame.grid(column=0, row=0, sticky='n')

        self.default_name_menu = Combobox(self.not_loot_frame, width=17,
                                          state='readonly',
                                          textvariable=self.character,
                                          values=self.character_list,
                                          postcommand=self.reset_character_list)
        self.default_name_menu.grid(column=0, row=0)
        if self.character_list:
            self.default_name_menu.current(0)
            self.character.set(self.character_list[0])

        self.new_name_frame.grid(column=0, row=1, ipady=2, ipadx=2)
        self.new_name_entry.grid()

        self.save.grid(column=1, row=0)

        self.aspect_frame.grid(column=1, row=1)
        self.solar_radio.grid(column=0, row=0, sticky='w')
        self.lunar_radio.grid(column=1, row=0, sticky='w')

        self.school_spell_frame.grid(column=1, row=2)

        self.school_frame.grid(column=0, row=0, padx=4, pady=(4, 8))
        self.school_box.grid()

        self.spell_frame.grid(column=0, row=3)
        for x in range(5):
            self.spell[x].grid(column=0, row=x, sticky='e')
            self.spell_level[x].grid(column=1, row=x, sticky='w')

        # inside build(), when you are laying out att_frame

        self.att_frame.grid(column=0, row=2)

        # add Level first
        self.level_label = Label(self.att_frame, text='Level')
        self.level_entry = Entry(self.att_frame, textvariable=self.level, width=4)
        self.level_label.grid(column=0, row=0, sticky='e')
        self.level_entry.grid(column=1, row=0, sticky='w')

        # then the six attributes
        for x in range(6):
            self.att_label[x].grid(column=0, row=x + 1, sticky='e')
            self.att_num[x].grid(column=1, row=x + 1, sticky='w')

        # finally Base Protection
        self.protection_label.grid(column=0, row=7, sticky='e')
        self.protection_entry.grid(column=1, row=7, sticky='w')

        self.resist_frame.grid(column=0, row=4, columnspan=2)
        self.resist_menu1.grid(column=0, row=0)
        self.resist_amount_menu1.grid(column=1, row=0)
        self.resist_menu2.grid(column=0, row=1)
        self.resist_amount_menu2.grid(column=1, row=1)

        self.equipment_frame.grid(column=0, row=5, columnspan=2)

        self.weapon_frame.grid(column=0, rowspan=2)
        for x in range(3):
            self.weapon_menu[x].grid()

        self.armor_frame.grid(column=1, row=0)
        self.armor_menu.grid()

        self.shield_frame.grid(column=1, row=1)
        self.shield_menu.grid()

        self.skill_frame.grid(column=2, row=0, rowspan=24, padx=2)

        for idx, skill in enumerate(SKILLS):
            skill_label = Label(self.skill_frame, text=skill, anchor='e', width=9)
            skill_label.grid(column=0, row=idx)
            skill_num = Entry(self.skill_frame, textvariable=self.skills[idx], width=4)
            skill_num.grid(column=1, row=idx)
        self.shield_label.grid(column=0, row=23)
        self.shield_num.grid(column=1, row=23)

    # Refresh character dropdown by re-reading names from ROM.
    def reset_character_list(self):
        prev = self.default_name_menu.current()
        self.character_list[:] = []
        self.character_addresses[:] = []
        self.character_list, self.character_addresses = get_major_name_lists(self.filename, self.addresses,
                                                                             self.name_length)
        self.default_name_menu['values'] = self.character_list
        if 0 <= prev < len(self.character_list):
            self.default_name_menu.current(prev)
            self.character.set(self.character_list[prev])

# base editor: follows item.py style
# short comments aligned with logic
class PartyEdit(Characters):
    # Init base character editor: prepare dictionaries, Tk variables, and common widgets.
    def __init__(self, f, a, n, r, t):
        super().__init__(f, a, n, r, t)
        self.win.title("Party Edit")

        # build UI
        self.build()

        # select Alaron (index 1) if available
        if len(self.character_list) > 1:
            self.character.set(self.character_list[1])

    # Layout the common character editor widgets.
    def build(self):
        # build the base Characters UI first
        super().build()

        # move the entire Characters layout (self.box) down to make room for the banner
        self.box.grid_configure(row=2)

        # add the warning banner at the very top
        banner = Label(
            self.win,
            text="!!! Edits are NEW GAME only !!!",
            fg="#B00020",
            font=("Segoe UI", 10, "bold")
        )
        banner.grid(column=0, row=0, columnspan=3, sticky="we", pady=(6, 4), padx=6)

        # subtle divider under the banner
        Separator(self.win, orient="horizontal").grid(
            column=0, row=1, columnspan=3, sticky="we", padx=6
        )

        # party-specific tweak to the skills box title
        self.skill_frame.configure(text='Skills\n(blank = cannot learn)')
class EnemyEdit(Characters):
    # Init base character editor: prepare dictionaries, Tk variables, and common widgets.
    def __init__(self, f, a, n, r, t):
        super().__init__(f, a, n, r, t)
        try:
            if isinstance(self.win, Toplevel):
                self.win.title("Enemy and Loot Edit")
        except Exception:
            pass

        self.drop_data_read = 34
        self.loot_name_length = 19

        self.loot_name_list, self.loot_code_list, self.loot_address_list = \
            get_major_loot_lists(self.filename, DROP_CAT, self.loot_name_length)

        # variables
        self.exp = StringVar()
        self.exp.set(0)
        self.exp.trace('w', partial(limit, self.exp, 255))
        self.exp.trace('w', self.update_exp)
        self.enemy_drop_cat = StringVar()
        self.drop_cat = StringVar()
        self.drop_cat.trace('w', self.set_drop_defaults)
        self.loot_name = StringVar()
        self.loot_name.trace('w', partial(limit_name_size, self.loot_name, self.loot_name_length))
        self.gold_min = StringVar()
        self.gold_min.trace('w', partial(limit, self.gold_min, 65535))
        self.gold_max = StringVar()
        self.gold_max.trace('w', partial(limit, self.gold_max, 65535))
        self.armor_chance = StringVar()
        self.armor_chance.trace('w', partial(limit, self.armor_chance, 100))
        self.shield_chance = StringVar()
        self.shield_chance.trace('w', partial(limit, self.shield_chance, 100))
        self.weap1_chance = StringVar()
        self.weap1_chance.trace('w', partial(limit, self.weap1_chance, 100))
        self.weap2_chance = StringVar()
        self.weap2_chance.trace('w', partial(limit, self.weap2_chance, 100))
        self.weap3_chance = StringVar()
        self.weap3_chance.trace('w', partial(limit, self.weap3_chance, 100))
        self.reagent_chance = StringVar()
        self.reagent_chance.trace('w', partial(limit, self.reagent_chance, 100))
        self.reagent_min = StringVar()
        self.reagent_min.trace('w', partial(limit, self.reagent_min, 99))
        self.reagent_max = StringVar()
        self.reagent_max.trace('w', partial(limit, self.reagent_max, 99))

        self.item, self.item_chance, self.item_min, self.item_max = ([] for _ in range(4))
        for _ in range(2):
            i = StringVar()
            self.item.append(i)
            c = StringVar()
            c.trace('w', partial(limit, c, 100))
            self.item_chance.append(c)
            mi = StringVar()
            mi.trace('w', partial(limit, mi, 99))
            self.item_min.append(mi)
            mx = StringVar()
            mx.trace('w', partial(limit, mx, 99))
            self.item_max.append(mx)

        self.other_items, self.other_items_chance = ([] for _ in range(2))
        for _ in range(4):
            i = StringVar()
            self.other_items.append(i)
            c = StringVar()
            c.trace('w', partial(limit, c, 100))
            self.other_items_chance.append(c)

        # build items
        self.enemy_drop_cat_box = Combobox()
        self.exp_total = Entry()
        self.drop_box = Combobox()
        self.save_loot = None

        # run
        self.build()
        self.character.set(self.character_list[0])

    def update_exp(self, *args):
        if self.exp.get() == '':
            self.exp_total.configure(text=' = ')
        else:
            xp = 75 * int(self.exp.get())
            if xp > 19125:
                xp = 19125
            self.exp_total.configure(text=' = ' + str(xp))

    def reset_loot_list(self):
        self.loot_name_list[:] = []
        self.loot_code_list[:] = []
        self.loot_address_list[:] = []
        self.loot_name_list, self.loot_code_list, self.loot_address_list = \
            get_major_loot_lists(self.filename, DROP_CAT, self.loot_name_length)
        self.drop_box['values'] = self.loot_name_list
        self.enemy_drop_cat_box['values'] = self.loot_name_list

    # Load current character bytes and populate all bound Tk variables.
    def set_defaults(self, *args):
        super().set_defaults()
        with open(self.filename, 'rb') as f:
            address = self.character_addresses[self.default_name_menu.current()] + 134
            f.seek(address)
            d = f.read(2).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
            # StringVar
            self.exp.set(str(int(d[0:2], 16)))
            # StringVar
            self.drop_cat.set(self.loot_name_list[self.loot_code_list.index(d[2:4].upper())])
            self.enemy_drop_cat.set(self.drop_cat.get())

    # Serialize Tk values back to bytes and write to ROM; clamps/normalizes empty cases.
    def write(self):
        try:
            with open(self.filename, 'rb+') as f:
                address = self.character_addresses[self.default_name_menu.current()]
                new_name = bytearray(self.name.get(), 'utf-8')
                if len(new_name) < self.name_length:
                    while len(new_name) < self.name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                f.seek(address + self.data_seek)
                d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                towrite = [self.aspect.get(), (d[2] + d[3]), (d[4] + d[5])]

                for i in self.skills:
                    j = i.get()
                    if j == '':
                        j = 255 if self.char_type == 0 else 0
                    towrite.append(j)

                for i in self.atts:
                    towrite.append(i.get())

                towrite.append(d[64] + d[65])
                towrite.append(self.level.get())
                towrite.append(d[68] + d[69])

                for i in self.weapons:
                    w = i.get()
                    if w == 'NONE':
                        towrite.append(int((self.inv_major_dic[w])[:2], 16))
                        towrite.append(int((self.inv_major_dic[w])[2:], 16))
                    else:
                        towrite.append(int((self.inv_major_dic['(weapon) ' + w])[:2], 16))
                        towrite.append(int((self.inv_major_dic['(weapon) ' + w])[2:], 16))

                towrite.append(d[82] + d[83])
                towrite.append(d[84] + d[85])

                for i in self.spells:
                    towrite.append(int(self.inv_spell_dic[i.get()][:2], 16))
                    towrite.append(int(self.inv_spell_dic[i.get()][2:], 16))

                towrite.append(SCHOOL[self.schools.get()])

                for i in self.spell_levels:
                    towrite.append(i.get())

                for i in range(118, 136, 2):
                    towrite.append(d[i] + d[i + 1])

                a = self.armor.get()
                if a == 'NONE':
                    towrite.append(int((self.inv_major_dic[a])[:2], 16))
                    towrite.append(int((self.inv_major_dic[a])[2:], 16))
                else:
                    towrite.append(int((self.inv_major_dic['(armor) ' + a])[:2], 16))
                    towrite.append(int((self.inv_major_dic['(armor) ' + a])[2:], 16))

                towrite.append(self.protection.get())

                s = self.shield.get()
                if s == 'NONE':
                    towrite.append(int((self.inv_major_dic[s])[:2], 16))
                    towrite.append(int((self.inv_major_dic[s])[2:], 16))
                else:
                    towrite.append(int((self.inv_major_dic['(shield) ' + s])[:2], 16))
                    towrite.append(int((self.inv_major_dic['(shield) ' + s])[2:], 16))

                shi = self.shield_skill.get()
                if shi == '':
                    shi = 255 if self.char_type == 0 else 0
                towrite.append(shi)

                towrite.append(int(RESIST[self.resist1a.get()], 16))
                towrite.append(int(RESIST_AMOUNTS[self.resist1b.get()], 16))
                towrite.append(int(RESIST[self.resist2a.get()], 16))
                towrite.append(int(RESIST_AMOUNTS[self.resist2b.get()], 16))

                for i in range(156, 179, 2):
                    towrite.append(d[i] + d[i + 1])
                towrite.append(self.exp.get())
                towrite.append(int(self.loot_code_list[self.loot_name_list.index(self.enemy_drop_cat.get())], 16))

                f.seek(address + self.data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                self.reset_character_list()
                self.character.set(self.character_list[self.character_list.index(self.name.get().rstrip('\x00'))])

            self.set_defaults()
            flash_saved(self.save, "Saved")
        except (FileNotFoundError, PermissionError, OSError,
                KeyError, ValueError, UnicodeEncodeError) as e:
            flash_saved(self.save, "Save Failed")

    def set_drop_defaults(self, *args):
        with open(self.filename, 'rb') as f:
            address = self.loot_address_list[self.drop_box.current()]

            f.seek(address)
            self.loot_name.set(f.read(self.loot_name_length).decode("utf-8"))

            f.seek(address + 22)
            d = f.read(self.drop_data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # StringVars - cast to str
            self.gold_min.set(str(int(d[2:4] + d[0:2], 16)))
            self.gold_max.set(str(int(d[6:8] + d[4:6], 16)))
            self.armor_chance.set(str(int(d[8:10], 16)))
            self.shield_chance.set(str(int(d[10:12], 16)))
            self.weap1_chance.set(str(int(d[12:14], 16)))
            self.weap2_chance.set(str(int(d[14:16], 16)))
            self.weap3_chance.set(str(int(d[16:18], 16)))
            self.reagent_chance.set(str(int(d[18:20], 16)))
            self.reagent_min.set(str(int(d[20:22], 16)))
            self.reagent_max.set(str(int(d[22:24], 16)))

            # items 1–2 using enumerate, no .index()
            for idx, (i_var, c_var, mi_var, mx_var) in enumerate(
                    zip(self.item, self.item_chance, self.item_min, self.item_max)):
                base = 24 + idx * 10
                code = d[base:base + 4].upper()
                if code == '0B10':
                    code = '0000'
                i_var.set(self.major_dic[code])
                c_var.set(str(int(d[base + 4:base + 6], 16)))
                mi_var.set(str(int(d[base + 6:base + 8], 16)))
                mx_var.set(str(int(d[base + 8:base + 10], 16)))

            # other items 3–6 using enumerate
            for idx, (i_var, c_var) in enumerate(zip(self.other_items, self.other_items_chance)):
                base = 44 + idx * 6
                code = d[base:base + 4].upper()
                i_var.set(self.major_dic[code])
                c_var.set(str(int(d[base + 4:base + 6], 16)))

    def write_drop(self):
        try:
            with open(self.filename, 'rb+') as f:
                address = self.loot_address_list[self.drop_box.current()]

                new_loot_name = bytearray(self.loot_name.get(), 'utf-8')
                if len(new_loot_name) < self.loot_name_length:
                    while len(new_loot_name) < self.loot_name_length:
                        new_loot_name.append(0x00)
                f.seek(address)
                f.write(new_loot_name)

                new_value = self.gold_min.get()
                min_v2, min_v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if min_v2 == 256:
                    min_v2 = 255
                    min_v1 = 255

                new_value = self.gold_max.get()
                max_v2, max_v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if max_v2 == 256:
                    max_v2 = 255
                    max_v1 = 255

                towrite = [
                    min_v1, min_v2,
                    max_v1, max_v2,
                    self.armor_chance.get(),
                    self.shield_chance.get(),
                    self.weap1_chance.get(),
                    self.weap2_chance.get(),
                    self.weap3_chance.get(),
                    self.reagent_chance.get(),
                    self.reagent_min.get(),
                    self.reagent_max.get()
                ]

                # items 1–2 with enumerate
                for idx, i_var in enumerate(self.item):
                    code = self.inv_major_dic[i_var.get()]
                    towrite.append(int(code[:2], 16))
                    towrite.append(int(code[2:], 16))
                    towrite.append(self.item_chance[idx].get())
                    towrite.append(self.item_min[idx].get())
                    towrite.append(self.item_max[idx].get())

                # other items 3–6 with enumerate
                for idx, i_var in enumerate(self.other_items):
                    code = self.inv_major_dic[i_var.get()]
                    towrite.append(int(code[:2], 16))
                    towrite.append(int(code[2:], 16))
                    towrite.append(self.other_items_chance[idx].get())

                f.seek(address + 22)
                for t in towrite:
                    t = int_cast(t)
                    f.write(t.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                self.reset_loot_list()
                if self.drop_cat.get() == self.enemy_drop_cat.get():
                    self.drop_cat.set(
                        self.loot_name_list[self.loot_name_list.index(self.loot_name.get().rstrip('\x00'))])
                    self.enemy_drop_cat.set(self.drop_cat.get())
                else:
                    self.drop_cat.set(
                        self.loot_name_list[self.loot_name_list.index(self.loot_name.get().rstrip('\x00'))])

            self.set_drop_defaults()
            flash_saved(self.save_loot, "Saved")
        except (FileNotFoundError, PermissionError, OSError,
                    KeyError, ValueError, UnicodeEncodeError) as e:
            # file missing/locked, bad dict key, bad int/hex, bad encoding
            flash_saved(self.save_loot, "Save Failed")

    # Layout the common character editor widgets.
    def build(self):
        super().build()

        self.skill_frame.configure(text='Skills')

        exp_frame = LabelFrame(self.not_loot_frame, text='EXP given')
        exp_frame.grid(column=0, row=8, columnspan=2)
        exp_label = Label(exp_frame, text='75 x ', width=6)
        exp_label.grid(column=0, row=0, sticky='e')
        exp_entry = Entry(exp_frame, textvariable=self.exp, width=4)
        exp_entry.grid(column=1, row=0, sticky='w')
        self.exp_total = Label(exp_frame, text=(' = ' + str(75 * int(self.exp.get()))), width=9)
        self.exp_total.grid(column=2, row=0, sticky='w')

        enemy_drop_cat_label = LabelFrame(self.not_loot_frame, text='Current Enemy Loot Type')
        enemy_drop_cat_label.grid(column=0, row=7, columnspan=2)
        self.enemy_drop_cat_box = Combobox(enemy_drop_cat_label, state='readonly',
                                           textvariable=self.enemy_drop_cat,
                                           values=self.loot_name_list,
                                           postcommand=self.reset_loot_list)
        self.enemy_drop_cat_box.grid(column=0, row=0)

        drop_frame = LabelFrame(self.box, text='Loot Editing:', bd=4)
        drop_frame.grid(column=1, row=0, ipadx=2)

        drop_box_label = Label(drop_frame, text='Loot Category:')
        drop_box_label.grid(column=0, row=0, sticky='e')
        self.drop_box = Combobox(drop_frame, state='readonly', width=19,
                                 textvariable=self.drop_cat,
                                 values=self.loot_name_list,
                                 postcommand=self.reset_loot_list)
        self.drop_box.grid(column=1, row=0, sticky='w')

        new_loot_name_frame = LabelFrame(drop_frame, text="Change Loot Name")
        new_loot_name_frame.grid(column=0, row=1, columnspan=2)
        new_loot_name_entry = Entry(new_loot_name_frame, textvariable=self.loot_name, width=19)
        new_loot_name_entry.grid()

        self.save_loot = Button(drop_frame, text="Save Loot Changes", width=18, command=self.write_drop)
        self.save_loot.grid(column=0, row=2, columnspan=2, pady=8)

        drop_stats = LabelFrame(drop_frame, text='Loot details\n(editing these affects all enemies\n with the '
                                                 'same loot type)\n')
        drop_stats.grid(column=0, row=3, columnspan=2)

        gold_min_label = Label(drop_stats, text='Random Gold MIN/MAX')
        gold_min_label.grid(column=0, row=0, sticky='e')
        gold_min_entry = Entry(drop_stats, textvariable=self.gold_min, width=5)
        gold_min_entry.grid(column=1, row=0, sticky='e')
        gold_max_entry = Entry(drop_stats, textvariable=self.gold_max, width=5)
        gold_max_entry.grid(column=2, row=0, sticky='w')

        drop_chance_frame = LabelFrame(drop_stats, text='Drop Chance')
        drop_chance_frame.grid(column=0, row=2, columnspan=3)

        armor_chance_label = Label(drop_chance_frame, text='Armor %', anchor='e')
        armor_chance_label.grid(column=0, row=0, sticky='e')
        armor_chance_entry = Entry(drop_chance_frame, textvariable=self.armor_chance, width=5)
        armor_chance_entry.grid(column=1, row=0, sticky='w')

        shield_chance_label = Label(drop_chance_frame, text='Shield %', anchor='e')
        shield_chance_label.grid(column=0, row=1, sticky='e')
        shield_chance_entry = Entry(drop_chance_frame, textvariable=self.shield_chance, width=5)
        shield_chance_entry.grid(column=1, row=1, sticky='w')

        weap1_chance_label = Label(drop_chance_frame, text='Weapon 1 %')
        weap1_chance_label.grid(column=0, row=2, sticky='e')
        weap1_chance_entry = Entry(drop_chance_frame, textvariable=self.weap1_chance, width=5)
        weap1_chance_entry.grid(column=1, row=2, sticky='w')

        weap2_chance_label = Label(drop_chance_frame, text='Weapon 2 %')
        weap2_chance_label.grid(column=0, row=3, sticky='e')
        weap2_chance_entry = Entry(drop_chance_frame, textvariable=self.weap2_chance, width=5)
        weap2_chance_entry.grid(column=1, row=3, sticky='w')

        weap3_chance_label = Label(drop_chance_frame, text='Weapon 3 %')
        weap3_chance_label.grid(column=0, row=4, sticky='e')
        weap3_chance_entry = Entry(drop_chance_frame, textvariable=self.weap3_chance, width=5)
        weap3_chance_entry.grid(column=1, row=4, sticky='w')

        reagent_chance_label = Label(drop_chance_frame, text='Random Reagent %')
        reagent_chance_label.grid(column=0, row=5, sticky='e')
        reagent_chance_entry = Entry(drop_chance_frame, textvariable=self.reagent_chance, width=5)
        reagent_chance_entry.grid(column=1, row=5, sticky='w')

        reagent_min_label = Label(drop_stats, text='Reagent drop MIN/MAX')
        reagent_min_label.grid(column=0, row=4, sticky='e')
        reagent_min_entry = Entry(drop_stats, textvariable=self.reagent_min, width=5)
        reagent_min_entry.grid(column=1, row=4, sticky='e')
        reagent_max_entry = Entry(drop_stats, textvariable=self.reagent_max, width=5)
        reagent_max_entry.grid(column=2, row=4, sticky='w')

        for i in self.item:
            item_frame = LabelFrame(drop_stats, text=('Item ' + str(self.item.index(i) + 1)))
            item_frame.grid(column=0, row=(5 + self.item.index(i)), columnspan=3)
            item_box = Combobox(item_frame, textvariable=i, values=list(self.major_dic.values()),
                                width=28, state='readonly')
            item_box.grid(column=0, row=0, columnspan=3)
            item_chance_label = Label(item_frame, text='Drop Chance')
            item_chance_label.grid(column=0, row=1, sticky='e')
            item_chance_entry = Entry(item_frame, textvariable=self.item_chance[self.item.index(i)], width=4)
            item_chance_entry.grid(column=1, row=1, sticky='e')
            item_min_max = Label(item_frame, text='Item amount MIN/MAX')
            item_min_max.grid(column=0, row=2)
            item_min_entry = Entry(item_frame, textvariable=self.item_min[self.item.index(i)], width=4)
            item_min_entry.grid(column=1, row=2, sticky='e')
            item_max_entry = Entry(item_frame, textvariable=self.item_max[self.item.index(i)], width=4)
            item_max_entry.grid(column=2, row=2, sticky='w')

        for i in self.other_items:
            other_item_frame = LabelFrame(drop_stats, text=('Item ' + str(self.other_items.index(i) + 3)))
            other_item_frame.grid(column=0, row=(7 + self.other_items.index(i)), columnspan=3)
            other_item_box = Combobox(other_item_frame, textvariable=i, values=list(self.major_dic.values()),
                                      width=28, state='readonly')
            other_item_box.grid(column=0, row=0, columnspan=2)
            other_item_chance_label = Label(other_item_frame, text='Drop Chance')
            other_item_chance_label.grid(column=0, row=1, sticky='e')
            other_item_chance_entry = Entry(other_item_frame,
                                            textvariable=self.other_items_chance[self.other_items.index(i)], width=4)
            other_item_chance_entry.grid(column=1, row=1, sticky='w')


# --- Item: Abstract base for item editors. Wires shared widgets and value parsing.
class Item:
    # Build common item widgets (name, value, stats, aspects, resistances, spells).
    def __init__(self, f, a, s, r, n):
        # GUI setup
        self.win = Toplevel()
        self.win.resizable(False, False)

        # ROM file metadata
        self.filename = f               # path to ROM
        self.item_addresses = a         # list of item addresses
        self.data_seek = s              # byte offset into item structure
        self.data_read = r              # how many bytes to read
        self.name_length = n            # max name length

        # dictionaries/lists used for lookups
        self.spell_dic = get_minor_dic(self.filename, SPELL_DIC, 22)
        self.inv_spell_dic = {v: k for k, v in self.spell_dic.items()}
        self.item_list, self.address_list = get_major_name_lists(
            self.filename, self.item_addresses, self.name_length
        )

        # tkinter variables bound to widgets
        self.item = StringVar()   # current item selected
        self.item.trace('w', self.set_defaults)

        self.name = StringVar()   # editable item name
        self.name.trace('w', partial(limit_name_size, self.name, self.name_length))

        self.value = StringVar()  # base value
        self.value.trace('w', partial(limit, self.value, 65535))

        self.aspect = IntVar()    # solar/lunar/none aspect
        self.stats = [StringVar() for i in range(5)]  # up to 5 stats

        self.att = StringVar()           # attribute type
        self.att_amount = StringVar()    # attribute amount
        self.att_amount.trace('w', partial(limit_127, self.att_amount))

        self.skill = StringVar()         # skill type
        self.skill_amount = StringVar()  # skill amount
        self.skill_amount.trace('w', partial(limit_127, self.skill_amount))

        self.spell = StringVar()         # primary spell
        self.spell_level = StringVar()
        self.spell_level.trace('w', partial(limit, self.spell_level, 15))

        self.magic = StringVar()         # secondary spell
        self.magic_level = StringVar()
        self.magic_level.trace('w', partial(limit, self.magic_level, 15))

        self.resist = StringVar()        # resist type
        self.resist_amount = StringVar() # resist amount

        # GUI widget construction
        self.box = Frame(self.win)

        # dropdown for selecting an item
        self.default_item_menu = Combobox(
            self.box, postcommand=self.reset_list,
            state='readonly', width=21,
            textvariable=self.item, values=self.item_list
        )

        # rename item
        self.new_name_label = LabelFrame(self.box, text='New Name')
        self.new_name_entry = Entry(self.new_name_label, textvariable=self.name, width=21)

        # save button
        self.save = Button(self.box, text='Save', width=8, command=self.write)

        # aspect (None/Solar/Lunar)
        self.aspect_frame = LabelFrame(self.box, text='Aspect')
        self.none_radio = Radiobutton(self.aspect_frame, text='NONE', variable=self.aspect, value=0)
        self.solar_radio = Radiobutton(self.aspect_frame, text="Solar", variable=self.aspect, value=2)
        self.lunar_radio = Radiobutton(self.aspect_frame, text='Lunar', variable=self.aspect, value=1)

        # attribute/skill/resist groups
        self.att_frame = LabelFrame(self.box, text='Attribute')
        self.att_menu = Combobox(self.att_frame, state='readonly', width=16,
                                 textvariable=self.att, values=list(EQUIPMENT_STAT.keys()))
        self.att_entry = Entry(self.att_frame, textvariable=self.att_amount, width=4)

        self.ski_att_frame = LabelFrame(self.box, text='Skill/Attribute')
        self.ski_att_menu = Combobox(self.ski_att_frame, width=16, state='readonly',
                                     textvariable=self.skill, values=list(SKILL_ATTRIBUTE.keys()))
        self.ski_att_amo_entry = Entry(self.ski_att_frame, textvariable=self.skill_amount, width=4)

        self.spell_frame = LabelFrame(self.box, text='Spell')
        self.spell_menu = Combobox(self.spell_frame, width=16, state='readonly',
                                   textvariable=self.spell, values=list(self.inv_spell_dic.keys()))
        self.spell_entry = Entry(self.spell_frame, textvariable=self.spell_level, width=4)

        self.magic_frame = LabelFrame(self.box, text='Magic')
        self.magic_menu = Combobox(self.magic_frame, width=16, state='readonly',
                                   textvariable=self.magic, values=list(self.inv_spell_dic.keys()))
        self.magic_entry = Entry(self.magic_frame, textvariable=self.magic_level, width=4)

        self.resist_frame = LabelFrame(self.box, text='Resist')
        self.resist_menu = Combobox(self.resist_frame, width=16, state='readonly',
                                    textvariable=self.resist, values=list(RESIST.keys()))
        self.resist_amount_menu = Combobox(self.resist_frame, width=5, state='readonly',
                                           textvariable=self.resist_amount, values=list(RESIST_AMOUNTS.keys()))

        # stat block
        self.stat_frame = LabelFrame(self.box, text='Stats:')
        self.stat_label = []
        self.stat_entry = []
        for x in range(5):
            self.stat_label.append(Label(self.stat_frame))
            self.stat_entry.append(Entry(self.stat_frame, textvariable=self.stats[x], width=4))

        self.value_label1 = Label(self.stat_frame, text='Base Value:')
        self.value_entry = Entry(self.stat_frame, textvariable=self.value, width=6)
        self.value_label2 = Label(self.stat_frame, text='Max base value: 65535', font=(None, 8))

    # Virtual: subclasses load the record and decode bytes here.
    def set_defaults(self):
        # must be overridden in subclass
        pass

    # Virtual: subclasses convert GUI back to bytes and write here.
    def write(self):
        # must be overridden in subclass
        pass

    # Grid the base item controls; shared across subclasses.
    def build(self):
        # lays out all widgets in a grid
        self.box.grid(column=0, row=0, pady=5, padx=5)
        self.default_item_menu.grid(column=0, row=0)
        self.new_name_label.grid(column=0, row=1)
        self.new_name_entry.grid()

        self.stat_frame.grid(column=0, row=2, rowspan=4)
        for i in range(5):
            self.stat_label[i].grid(column=0, row=i, sticky='e')
            self.stat_entry[i].grid(column=1, row=i, sticky='w')
        self.value_label1.grid(column=0, row=4, sticky='e')
        self.value_entry.grid(column=1, row=4, sticky='w')
        self.value_label2.grid(row=5, columnspan=2)

        self.save.grid(column=1, row=0)

        self.aspect_frame.grid(column=1, row=1)
        self.none_radio.grid(column=0, row=0)
        self.solar_radio.grid(column=1, row=0)
        self.lunar_radio.grid(column=2, row=0)

        self.att_frame.grid(column=1, row=2)
        self.att_menu.grid(column=0, row=0)
        self.att_entry.grid(column=1, row=0, sticky='e')

        self.ski_att_frame.grid(column=1, row=3)
        self.ski_att_menu.grid(column=0, row=0)
        self.ski_att_amo_entry.grid(column=1, row=0)

        self.spell_frame.grid(column=1, row=4)
        self.spell_menu.grid(column=0, row=0)
        self.spell_entry.grid(column=1, row=0)

        self.magic_frame.grid(column=1, row=5)
        self.magic_menu.grid(column=0, row=0)
        self.magic_entry.grid(column=1, row=0)

        self.resist_frame.grid(column=1, row=6)
        self.resist_menu.grid(column=0, row=0)
        self.resist_amount_menu.grid(column=1, row=0)

    # Re-read item names/addresses; keep dropdown fresh after rename.
    def reset_list(self):
        # refresh item list from file
        self.item_list[:] = []
        self.address_list[:] = []
        self.item_list, self.address_list = get_major_name_lists(
            self.filename, self.item_addresses, self.name_length
        )
        self.default_item_menu['values'] = self.item_list
class AccessoryEdit(Item):
    # Build common item widgets (name, value, stats, aspects, resistances, spells).
    def __init__(self, f, a, s, r, n):
        super().__init__(f, a, s, r, n)
        self.win.title("Accessory Edit")

        # label and validation for each stat
        stat_var = ['Damage', 'Protection', 'Strength Required', 'Intelligence Required']
        for s in stat_var:
            self.stats[stat_var.index(s)].trace('w', partial(limit_127, self.stats[stat_var.index(s)]))
            self.stat_label[stat_var.index(s)]['text'] = s

        # run
        self.build()
        self.item.set(self.item_list[0])

    # Virtual: subclasses load the record and decode bytes here.
    def set_defaults(self, *args):
        # load selected accessory from ROM
        with open(self.filename, 'rb') as f:
            address = self.address_list[self.default_item_menu.current()]
            f.seek(address)
            self.name.set(f.read(self.name_length).decode("utf-8"))

            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # stats
            self.stats[0].set(int(d[0] + d[1], 16))
            self.stats[1].set(int(d[2] + d[3], 16))
            self.stats[2].set(int(d[4] + d[5], 16))
            self.stats[3].set(int(d[6] + d[7], 16))

            # value and aspect
            self.value.set((int(d[10] + d[11], 16) * 256) + int(d[8] + d[9], 16))
            self.aspect.set(d[13])

            # attribute and bonus
            self.att.set(inv_EQUIPMENT_STAT[(d[14] + d[15]).upper()])
            at = int(d[16] + d[17], 16)
            if at > 127:
                at = at - 256
            self.att_amount.set(at)

            # skill and bonus
            self.skill.set(inv_SKILL_ATTRIBUTE[(d[18] + d[19]).upper()])
            aa = int(d[20] + d[21], 16)
            if aa > 127:
                aa = aa - 256
            self.skill_amount.set(aa)

            # spell data
            self.spell.set(self.spell_dic[(d[22:26]).upper()])
            self.spell_level.set(int(d[26] + d[27], 16))

            # magic data
            self.magic.set(self.spell_dic[(d[30:34]).upper()])
            self.magic_level.set(int(d[34] + d[35], 16))

            # resistances
            self.resist.set(inv_RESIST[(d[36] + d[37]).upper()])
            self.resist_amount.set(inv_RESIST_AMOUNTS[(d[38] + d[39]).upper()])

    # Virtual: subclasses convert GUI back to bytes and write here.
    def write(self):
        # save edits back into ROM
        try:
            with open(self.filename, 'rb+') as f:
                address = self.address_list[self.default_item_menu.current()]

                # write name
                new_name = bytearray(self.name.get(), 'utf-8')
                if len(new_name) < self.name_length:
                    while len(new_name) < self.name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                # read existing data for preserved fields
                f.seek(address + self.data_seek)
                d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                # value
                new_value = self.value.get() or '0'
                v2, v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if v2 == 256:
                    v2 = 255
                    v1 = 255

                # attribute amount
                st = int(self.att_amount.get() or 0)
                if st < 0:
                    st = st + 256

                # skill amount
                sk = int(self.skill_amount.get() or 0)
                if sk < 0:
                    sk = sk + 256

                # pack new data
                towrite = [
                    self.stats[0].get(),
                    self.stats[1].get(),
                    self.stats[2].get(),
                    self.stats[3].get(),
                    v1, v2,
                    self.aspect.get(),
                    int(EQUIPMENT_STAT[self.att.get()], 16),
                    st,
                    int(SKILL_ATTRIBUTE[self.skill.get()], 16),
                    sk,
                    int(self.inv_spell_dic[self.spell.get()][:2], 16),
                    int(self.inv_spell_dic[self.spell.get()][2:], 16),
                    self.spell_level.get(),
                    (d[28] + d[29]),
                    int(self.inv_spell_dic[self.magic.get()][:2], 16),
                    int(self.inv_spell_dic[self.magic.get()][2:], 16),
                    self.magic_level.get(),
                    int(RESIST[self.resist.get()], 16),
                    int(RESIST_AMOUNTS[self.resist_amount.get()], 16)
                ]

                # write to ROM
                f.seek(address + self.data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                # refresh UI
                self.reset_list()
                self.item.set(self.item_list[self.item_list.index(self.name.get().rstrip('\x00'))])
            self.set_defaults()
            flash_saved(self.save, "Saved")
        except (FileNotFoundError, PermissionError, OSError,
                KeyError, ValueError, UnicodeEncodeError):
            # save failed due to file/encoding/dict/number error
            flash_saved(self.save, "Save Failed")
class ArmorShield(Item):
    # Build common item widgets (name, value, stats, aspects, resistances, spells).
    def __init__(self, f, a, s, r, n, win_type):
        super().__init__(f, a, s, r, n)
        # window title
        if win_type == 5:
            self.win.title("Armor Edit")
        elif win_type == 6:
            self.win.title("Shield Edit")

        # label and validation for each stat
        stat_var = ['Defense', 'Protection', 'Dexterity', 'Stealth']
        for s in stat_var:
            self.stats[stat_var.index(s)].trace('w', partial(limit_127, self.stats[stat_var.index(s)]))
            self.stat_label[stat_var.index(s)]['text'] = s

        # run
        self.build()
        self.item.set(self.item_list[0])

    # Virtual: subclasses load the record and decode bytes here.
    def set_defaults(self, *args):
        # load selected armor/shield from ROM
        with open(self.filename, 'rb') as f:
            address = self.address_list[self.default_item_menu.current()]
            f.seek(address)
            self.name.set(f.read(self.name_length).decode("utf-8"))

            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # stats
            self.stats[0].set(int(d[0] + d[1], 16))
            self.stats[1].set(int(d[2] + d[3], 16))

            dx = int(d[4] + d[5], 16)
            if dx > 127:
                dx -= 256
            self.stats[2].set(dx)

            sneak = int(d[8] + d[9], 16)
            if sneak > 127:
                sneak -= 256
            self.stats[3].set(sneak)

            # value and aspect
            self.value.set((int(d[12] + d[13], 16) * 256) + int(d[10] + d[11], 16))
            self.aspect.set(d[17])

            # attribute and bonus
            self.att.set(inv_EQUIPMENT_STAT[(d[18] + d[19]).upper()])
            at = int(d[20] + d[21], 16)
            if at > 127:
                at -= 256
            self.att_amount.set(at)

            # skill and bonus
            self.skill.set(inv_SKILL_ATTRIBUTE[(d[22] + d[23]).upper()])
            aa = int(d[24] + d[25], 16)
            if aa > 127:
                aa -= 256
            self.skill_amount.set(aa)

            # spells
            self.spell.set(self.spell_dic[(d[26:30]).upper()])
            self.spell_level.set(int(d[30] + d[31], 16))

            self.magic.set(self.spell_dic[(d[34:38]).upper()])
            self.magic_level.set(int(d[38] + d[39], 16))

            # resistances
            self.resist.set(inv_RESIST[(d[40] + d[41]).upper()])
            self.resist_amount.set(inv_RESIST_AMOUNTS[(d[42] + d[43]).upper()])

    # Virtual: subclasses convert GUI back to bytes and write here.
    def write(self):
        # save edits back into ROM
        try:
            with open(self.filename, 'rb+') as f:
                address = self.address_list[self.item_list.index(self.default_item_menu.get())]

                # write name
                new_name = bytearray(self.name.get(), 'utf-8')
                if len(new_name) < self.name_length:
                    while len(new_name) < self.name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                # read existing data for preserved fields
                f.seek(address + self.data_seek)
                d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                # value
                new_value_raw = self.value.get()
                new_value = int(new_value_raw) if new_value_raw != '' else 0
                v2, v1 = divmod(new_value, 256)
                if v2 == 256:
                    v2 = 255
                    v1 = 255

                # signed fields to unsigned byte
                dx = int(self.stats[2].get() or 0)
                if dx < 0:
                    dx += 256

                sneak = int(self.stats[3].get() or 0)
                if sneak < 0:
                    sneak += 256

                st = int(self.att_amount.get() or 0)
                if st < 0:
                    st += 256

                sk = int(self.skill_amount.get() or 0)
                if sk < 0:
                    sk += 256

                # pack new data
                towrite = [
                    self.stats[0].get(),
                    self.stats[1].get(),
                    dx,
                    (d[6] + d[7]),
                    sneak,
                    v1, v2,
                    (d[14] + d[15]),
                    self.aspect.get(),
                    int(EQUIPMENT_STAT[self.att.get()], 16),
                    st,
                    int(SKILL_ATTRIBUTE[self.skill.get()], 16),
                    sk,
                    int(self.inv_spell_dic[self.spell.get()][:2], 16),
                    int(self.inv_spell_dic[self.spell.get()][2:], 16),
                    self.spell_level.get(),
                    (d[32] + d[33]),
                    int(self.inv_spell_dic[self.magic.get()][:2], 16),
                    int(self.inv_spell_dic[self.magic.get()][2:], 16),
                    self.magic_level.get(),
                    int(RESIST[self.resist.get()], 16),
                    int(RESIST_AMOUNTS[self.resist_amount.get()], 16)
                ]

                # write to ROM
                f.seek(address + self.data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                # refresh UI
                self.reset_list()
                self.item.set(self.item_list[self.item_list.index(self.name.get().rstrip('\x00'))])

            # reload UI and show success
            self.set_defaults()
            flash_saved(self.save, "Saved")

        except (FileNotFoundError, PermissionError, OSError,
                KeyError, ValueError, UnicodeEncodeError) as err:
            # save failed due to file/encoding/dict/number error
            flash_saved(self.save, "Save Failed")
            # optional console log for debugging
            print(f"Save failed in ArmorShield: {err}")
class WeaponEdit(Item):
    # Build common item widgets (name, value, stats, aspects, resistances, spells).
    def __init__(self, f, a, s, r, n):
        # base UI + state
        super().__init__(f, a, s, r, n)
        self.win.title('Weapon Edit')

        # stat labels and limits
        stat_var = ['Strength Required', 'Hit', 'Damage', 'Range']
        for s in stat_var:
            self.stats[stat_var.index(s)].trace('w', partial(limit, self.stats[stat_var.index(s)], 255))
            self.stat_label[stat_var.index(s)]['text'] = s

        # weapon-specific fields
        self.damage_type = StringVar()
        self.weapon_type = StringVar()
        self.animation = StringVar()

        # build UI and load first record
        self.build()
        self.item.set(self.item_list[0])

    # Virtual: subclasses load the record and decode bytes here.
    def set_defaults(self, *args):
        # populate UI from ROM for the selected weapon
        with open(self.filename, 'rb') as f:
            address = self.address_list[self.default_item_menu.current()]
            f.seek(address)
            self.name.set(f.read(self.name_length).decode("utf-8"))

            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # weapon type byte
            self.weapon_type.set(inv_WEAPON_TYPE[d[1].upper()])

            # core stats
            self.stats[0].set(int(d[2] + d[3], 16))
            self.stats[1].set(int(d[4] + d[5], 16))
            self.stats[2].set(int(d[6] + d[7], 16))

            # value is little-endian v1,v2
            self.value.set((int(d[10] + d[11], 16) * 256) + int(d[8] + d[9], 16))

            self.stats[3].set(int(d[14] + d[15], 16))

            # animation nibble pair
            # fix: ensure .upper() applies to the two-char token
            self.animation.set(inv_WEAPON_ANIMATIONS[(d[16] + d[17]).upper()])

            # damage type
            self.damage_type.set(inv_RESIST[(d[20] + d[21]).upper()])

            # aspect nibble
            self.aspect.set(d[23])

            # attribute bonus
            self.att.set(inv_EQUIPMENT_STAT[(d[24] + d[25]).upper()])
            at = int(d[26] + d[27], 16)
            if at > 127:
                at -= 256
            self.att_amount.set(at)

            # skill bonus
            self.skill.set(inv_SKILL_ATTRIBUTE[(d[28] + d[29]).upper()])
            aa = int(d[30] + d[31], 16)
            if aa > 127:
                aa -= 256
            self.skill_amount.set(aa)

            # spell
            self.spell.set(self.spell_dic[(d[32:36]).upper()])
            self.spell_level.set(int(d[36] + d[37], 16))

            # magic
            self.magic.set(self.spell_dic[(d[40:44]).upper()])
            self.magic_level.set(int(d[44] + d[45], 16))

            # resist
            self.resist.set(inv_RESIST[(d[46] + d[47]).upper()])
            self.resist_amount.set(inv_RESIST_AMOUNTS[(d[48] + d[49]).upper()])

    # Virtual: subclasses convert GUI back to bytes and write here.
    def write(self):
        # write UI values back to ROM for the selected weapon
        try:
            with open(self.filename, 'rb+') as f:
                address = self.address_list[self.default_item_menu.current()]

                # name field
                new_name = bytearray(self.name.get(), 'utf-8')
                if len(new_name) < self.name_length:
                    while len(new_name) < self.name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                # fetch original block to preserve untouched bytes
                f.seek(address + self.data_seek)
                d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                # value little-endian split
                new_value = self.value.get()
                v2, v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if v2 == 256:
                    v2 = 255
                    v1 = 255

                # convert negative signed bytes to unsigned
                st = int(self.att_amount.get())
                if st < 0:
                    st += 256
                sk = int(self.skill_amount.get())
                if sk < 0:
                    sk += 256

                # pack out bytes in order
                towrite = [
                    WEAPON_TYPE[self.weapon_type.get()],
                    self.stats[0].get(),
                    self.stats[1].get(),
                    self.stats[2].get(),
                    v1, v2,
                    (d[12] + d[13]),                   # padding or reserved
                    self.stats[3].get(),
                    WEAPON_ANIMATIONS[self.animation.get()],
                    (d[18] + d[19]),                   # padding or reserved
                    RESIST[self.damage_type.get()],
                    self.aspect.get(),
                    EQUIPMENT_STAT[self.att.get()],
                    st,
                    SKILL_ATTRIBUTE[self.skill.get()],
                    sk,
                    int(self.inv_spell_dic[self.spell.get()][:2], 16),
                    int(self.inv_spell_dic[self.spell.get()][2:], 16),
                    self.spell_level.get(),
                    (d[38] + d[39]),                   # padding or reserved
                    int(self.inv_spell_dic[self.magic.get()][:2], 16),
                    int(self.inv_spell_dic[self.magic.get()][2:], 16),
                    self.magic_level.get(),
                    RESIST[self.resist.get()],
                    RESIST_AMOUNTS[self.resist_amount.get()]
                ]

                # write byte-by-byte
                f.seek(address + self.data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                # refresh dropdown values and restore selection
                self.reset_list()
                self.item.set(self.item_list[self.item_list.index(self.name.get().rstrip('\x00'))])

            # reload UI and show success
            self.set_defaults()
            flash_saved(self.save, "Saved")

        except (FileNotFoundError, PermissionError, OSError,
                KeyError, ValueError, UnicodeEncodeError) as err:
            # file missing/locked, bad dict key, bad int/hex, bad encoding
            flash_saved(self.save, "Save Failed")
            # optional console log for debugging
            print(f"Save failed in WeaponEdit: {err}")

    # Grid the base item controls; shared across subclasses.
    def build(self):
        # base layout
        super().build()

        # damage type selector
        damage_type_frame = LabelFrame(self.box, text='Damage Type')
        damage_type_box = Combobox(
            damage_type_frame, textvariable=self.damage_type,
            values=list(RESIST.keys())[1:],  # skip NONE
            width=14, state='readonly'
        )

        # weapon type selector
        weapon_type_frame = LabelFrame(self.box, text='Weapon Type')
        weapon_type_menu = Combobox(
            weapon_type_frame, width=14, textvariable=self.weapon_type,
            values=list(WEAPON_TYPE.keys()), state='readonly'
        )

        # animation selector
        animation_frame = LabelFrame(self.box, text='Animation')
        animation_menu = Combobox(
            animation_frame, textvariable=self.animation, width=14,
            values=list(WEAPON_ANIMATIONS.keys()), state='readonly'
        )

        # layout
        damage_type_frame.grid(column=0, row=6)
        damage_type_box.grid()

        weapon_type_frame.grid(column=0, row=7)
        weapon_type_menu.grid()

        animation_frame.grid(column=0, row=8)
        animation_menu.grid()

# --- WandScrollEdit: Small window for editing wands and scrolls. Local functions manage read/write for each.
class WandScrollEdit:
    # Ad-hoc window with local helpers for reading/writing wands and scrolls.
    def __init__(self, filename):
        # window
        win = Toplevel()
        win.resizable(False, False)
        win.title("Wand and Scroll Edit")

        # config
        filename = filename
        data_seek = 24
        data_read = 20
        name_length = 18

        # lists
        self.scroll_list, self.scroll_addresses = get_major_name_lists(filename, SCROLL_ADDRESSES, name_length)
        self.wand_list, self.wand_addresses = get_major_name_lists(filename, WAND_ADDRESSES, name_length)
        self.sc_menu = Combobox()
        self.wa_menu = Combobox()

        # dictionaries
        spell_dic = get_minor_dic(filename, SPELL_DIC, 22)
        inv_spell_dic = {v: k for k, v in spell_dic.items()}

        # load wand -> fields
        def wand_defaults(*args):
            with open(filename, 'rb') as f:
                address = self.wand_addresses[self.wa_menu.current()]
                f.seek(address)
                wa_name.set(f.read(name_length).decode("utf-8"))

                f.seek(address + data_seek)
                d = f.read(data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                wa_damage.set(int(d[0] + d[1], 16))
                wa_protection.set(int(d[2] + d[3], 16))
                wa_str_req.set(int(d[4] + d[5], 16))
                wa_int_req.set(int(d[6] + d[7], 16))
                wa_value.set((int(d[10] + d[11], 16) * 256) + int(d[8] + d[9], 16))
                wa_aspect.set(d[13])
                wa_skill.set(inv_SKILL_ATTRIBUTE[(d[14] + d[15]).upper()])
                att_amount = int(d[16] + d[17], 16)
                if att_amount > 127:
                    att_amount = att_amount - 256
                wa_skill_amount.set(att_amount)
                wa_spell.set(spell_dic[(d[22:26]).upper()])
                wa_charges.set(int(d[26] + d[27], 16))
                wa_spell_level.set(int(d[28] + d[29], 16))
                wa_resist.set(inv_RESIST[(d[36] + d[37]).upper()])
                wa_resist_amount.set(inv_RESIST_AMOUNTS[(d[38] + d[39]).upper()])

        # load scroll -> fields
        def scroll_defaults(*args):
            with open(filename, 'rb') as f:
                address = self.scroll_addresses[self.sc_menu.current()]
                f.seek(address)
                sc_name.set(f.read(name_length).decode("utf-8"))

                f.seek(address + data_seek)
                d = f.read(data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                sc_value.set((int(d[10] + d[11], 16) * 256) + int(d[8] + d[9], 16))
                sc_spell.set(spell_dic[(d[22:26]).upper()])
                sc_cast_level.set(int(d[28] + d[29], 16))

        # write wand <- fields
        def wand_write():
            with open(filename, 'rb+') as f:
                address = self.wand_addresses[self.wa_menu.current()]

                # name
                new_name = bytearray(wa_name.get(), 'utf-8')
                if len(new_name) < name_length:
                    while len(new_name) < name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                # read block (preserve unknowns)
                f.seek(address + data_seek)
                d = f.read(data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                # value split
                new_value = wa_value.get()
                v2, v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if v2 == 256:
                    v2 = 255
                    v1 = 255

                # signed skill amount
                sk = int(wa_skill_amount.get())
                if sk < 0:
                    sk = sk + 256

                towrite = [
                    wa_damage.get(),
                    wa_protection.get(),
                    wa_str_req.get(),
                    wa_int_req.get(),
                    v1, v2,
                    wa_aspect.get(),
                    SKILL_ATTRIBUTE[wa_skill.get()],
                    sk,
                    (d[18] + d[19]),
                    (d[20] + d[21]),
                    int(inv_spell_dic[wa_spell.get()][:2], 16),
                    int(inv_spell_dic[wa_spell.get()][2:], 16),
                    wa_charges.get(),
                    wa_spell_level.get(),
                    (d[30] + d[31]),
                    (d[32] + d[33]),
                    (d[34] + d[35]),
                    RESIST[wa_resist.get()],
                    RESIST_AMOUNTS[wa_resist_amount.get()]
                ]

                f.seek(address + data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                # refresh selection
                wand_reset_list()
                self.wand.set(self.wand_list[self.wand_list.index(wa_name.get().rstrip('\x00'))])
            wand_defaults()
            flash_saved(self.wa_save_btn, "Saved", ms=1200)  # flash at Save Wand button

        # write scroll <- fields
        def scroll_write():
            with open(filename, 'rb+') as f:
                address = self.scroll_addresses[self.sc_menu.current()]

                # name
                new_name = bytearray(sc_name.get(), 'utf-8')
                if len(new_name) < name_length:
                    while len(new_name) < name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                # read block (preserve unknowns)
                f.seek(address + data_seek)
                d = f.read(data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

                # value split
                new_value = sc_value.get()
                v2, v1 = divmod(int(new_value), 256)  # split value → (high, low) bytes for little-endian storage
                if v2 == 256:
                    v2 = 255
                    v1 = 255

                towrite = []
                for i in range(0, 8, 2):
                    towrite.append(d[i] + d[i + 1])
                towrite.append(v1)
                towrite.append(v2)
                for i in range(12, 22, 2):
                    towrite.append(d[i] + d[i + 1])
                towrite.append(int(inv_spell_dic[sc_spell.get()][:2], 16))
                towrite.append(int(inv_spell_dic[sc_spell.get()][2:], 16))
                towrite.append(d[26] + d[27])
                towrite.append(sc_cast_level.get())
                for i in range(30, 40, 2):
                    towrite.append(d[i] + d[i + 1])

                f.seek(address + data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

                # refresh selection
                scroll_reset_list()
                self.scroll.set(self.scroll_list[self.scroll_list.index(sc_name.get().rstrip('\x00'))])
            scroll_defaults()
            flash_saved(self.sc_save_btn, "Saved", ms=1200)  # flash at Save Scroll button

        # layout
        def build():
            box = Frame(win)
            box.grid(padx=5, pady=5)

            # scrolls UI
            sc_box = LabelFrame(box, text='Scrolls:', bd=6)
            sc_box.grid(column=0, row=0, sticky='n')

            self.sc_menu = Combobox(sc_box, textvariable=self.scroll, width=20,
                                    values=self.scroll_list,
                                    postcommand=scroll_reset_list, state='readonly')
            self.sc_menu.grid(column=0, row=0, columnspan=2)

            sc_new_name_label = LabelFrame(sc_box, text='New Name')
            sc_new_name_label.grid(column=0, row=1, columnspan=2)
            sc_new_name_entry = Entry(sc_new_name_label, textvariable=sc_name, width=20)
            sc_new_name_entry.grid(column=0, row=0)

            sc_spell_label = LabelFrame(sc_box, text='Spell learned/cast')
            sc_spell_label.grid(column=0, row=2, columnspan=2)
            sc_spell_menu = Combobox(sc_spell_label, textvariable=sc_spell, width=20,
                                     values=list(inv_spell_dic.keys()), state='readonly')
            sc_spell_menu.grid(column=0, row=0)

            sc_spell_label = Label(sc_box, text='Cast Level')
            sc_spell_label.grid(column=0, row=3, sticky='e')
            sc_spell_entry = Entry(sc_box, textvariable=sc_cast_level, width=4)
            sc_spell_entry.grid(column=1, row=3, sticky='w')

            sc_value_label = Label(sc_box, text='Base Value')
            sc_value_label.grid(column=0, row=4, sticky='e')
            sc_value_entry = Entry(sc_box, textvariable=sc_value, width=6)
            sc_value_entry.grid(column=1, row=4, sticky='w')

            # Save Scroll button (store handle for flash)
            self.sc_save_btn = Button(sc_box, text='Save Scroll Edits', command=scroll_write)
            self.sc_save_btn.grid(column=0, row=5, columnspan=2)

            # wands UI
            wa_box = LabelFrame(box, text='Wands', bd=6)
            wa_box.grid(column=1, row=0)

            self.wa_menu = Combobox(wa_box, textvariable=self.wand, width=20,
                                    values=self.wand_list,
                                    postcommand=wand_reset_list)
            self.wa_menu.grid(column=0, row=0, columnspan=2)

            wa_new_name_label = LabelFrame(wa_box, text='New Name')
            wa_new_name_label.grid(column=0, row=1, columnspan=2)
            wa_new_name_entry = Entry(wa_new_name_label, textvariable=wa_name, width=20)
            wa_new_name_entry.grid(column=0, row=0)

            wa_spell_label = LabelFrame(wa_box, text='Spell Cast')
            wa_spell_label.grid(column=0, row=2, columnspan=2)
            wa_spell_menu = Combobox(wa_spell_label, textvariable=wa_spell, width=20,
                                     values=list(inv_spell_dic.keys()), state='readonly')
            wa_spell_menu.grid(column=0, row=0)

            wa_level_label = Label(wa_box, text='Spell Level')
            wa_level_label.grid(column=0, row=3, sticky='e')
            wa_level_entry = Entry(wa_box, textvariable=wa_spell_level, width=4)
            wa_level_entry.grid(column=1, row=3, sticky='w')

            wa_charges_label = Label(wa_box, text='Charges')
            wa_charges_label.grid(column=0, row=4, sticky='e')
            wa_charges_entry = Entry(wa_box, textvariable=wa_charges, width=4)
            wa_charges_entry.grid(column=1, row=4, sticky='w')

            wa_damage_label = Label(wa_box, text='Damage')
            wa_damage_label.grid(column=0, row=5, sticky='e')
            wa_damage_entry = Entry(wa_box, textvariable=wa_damage, width=4)
            wa_damage_entry.grid(column=1, row=5, sticky='w')

            wa_protection_label = Label(wa_box, text='Protection')
            wa_protection_label.grid(column=0, row=6, sticky='e')
            wa_protection_entry = Entry(wa_box, textvariable=wa_protection, width=4)
            wa_protection_entry.grid(column=1, row=6, sticky='w')

            wa_str_label = Label(wa_box, text='Str Req')
            wa_str_label.grid(column=0, row=7, sticky='e')
            wa_str_entry = Entry(wa_box, textvariable=wa_str_req, width=4)
            wa_str_entry.grid(column=1, row=7, sticky='w')

            wa_int_label = Label(wa_box, text='Int Req')
            wa_int_label.grid(column=0, row=8, sticky='e')
            wa_int_entry = Entry(wa_box, textvariable=wa_int_req, width=4)
            wa_int_entry.grid(column=1, row=8, sticky='w')

            wa_value_label = Label(wa_box, text='Base Value')
            wa_value_label.grid(column=0, row=9, sticky='e')
            wa_value_entry = Entry(wa_box, textvariable=wa_value, width=6)
            wa_value_entry.grid(column=1, row=9, sticky='w')

            aspect_frame = LabelFrame(wa_box, text='Aspect')
            aspect_frame.grid(column=0, row=10, columnspan=2)
            none_radio = Radiobutton(aspect_frame, text='NONE', variable=wa_aspect, value=0)
            none_radio.grid(column=0, row=0)
            solar_radio = Radiobutton(aspect_frame, text="Solar", variable=wa_aspect, value=2)
            solar_radio.grid(column=1, row=0)
            lunar_radio = Radiobutton(aspect_frame, text='Lunar', variable=wa_aspect, value=1)
            lunar_radio.grid(column=2, row=0)

            ski_att_frame = LabelFrame(wa_box, text='Skill/Attribute')
            ski_att_frame.grid(column=0, row=11, columnspan=2)
            ski_att_menu = Combobox(ski_att_frame, textvariable=wa_skill, width=16,
                                    values=list(SKILL_ATTRIBUTE.keys()), state='readonly')
            ski_att_menu.grid(column=0, row=0)
            ski_att_amo_entry = Entry(ski_att_frame, textvariable=wa_skill_amount, width=4)
            ski_att_amo_entry.grid(column=1, row=0)

            resist_frame = LabelFrame(wa_box, text='Resist')
            resist_frame.grid(column=0, row=12, columnspan=2)
            resist_menu = Combobox(resist_frame, textvariable=wa_resist, width=16,
                                   values=list(RESIST.keys()), state='readonly')
            resist_menu.grid(column=0, row=0)
            resist_amount_menu = Combobox(resist_frame, textvariable=wa_resist_amount, width=5,
                                          values=list(RESIST_AMOUNTS.keys()), state='readonly')
            resist_amount_menu.grid(column=1, row=0)

            # Save Wand button (store handle for flash)
            self.wa_save_btn = Button(wa_box, text='Save Wand Edits', command=wand_write)
            self.wa_save_btn.grid(column=0, row=13, columnspan=2)

        # list refreshers
        def scroll_reset_list():
            self.scroll_list[:] = []
            self.scroll_addresses[:] = []
            self.scroll_list, self.scroll_addresses = get_major_name_lists(filename, SCROLL_ADDRESSES, name_length)
            self.sc_menu['values'] = self.scroll_list

        def wand_reset_list():
            self.wand_list[:] = []
            self.wand_addresses[:] = []
            self.wand_list, self.wand_addresses = get_major_name_lists(filename, WAND_ADDRESSES, name_length)
            self.wa_menu['values'] = self.wand_list

        # variables
        self.wand = StringVar()
        self.wand.trace('w', wand_defaults)
        wa_name = StringVar(); wa_name.trace('w', partial(limit_name_size, wa_name, name_length))
        wa_damage = StringVar(); wa_damage.trace('w', partial(limit, wa_damage, 255))
        wa_protection = StringVar(); wa_protection.trace('w', partial(limit, wa_protection, 255))
        wa_str_req = StringVar(); wa_str_req.trace('w', partial(limit, wa_str_req, 30))
        wa_int_req = StringVar(); wa_int_req.trace('w', partial(limit, wa_int_req, 30))
        wa_value = StringVar(); wa_value.trace('w', partial(limit, wa_value, 65535))
        wa_aspect = StringVar()
        wa_skill = StringVar()
        wa_skill_amount = StringVar(); wa_skill_amount.trace('w', partial(limit_127, wa_skill_amount))
        wa_spell = StringVar()
        wa_charges = StringVar(); wa_charges.trace('w', partial(limit, wa_charges, 255))
        wa_spell_level = StringVar(); wa_spell_level.trace('w', partial(limit, wa_spell_level, 15))
        wa_resist = StringVar()
        wa_resist_amount = StringVar()

        self.scroll = StringVar()
        self.scroll.trace('w', scroll_defaults)
        sc_name = StringVar(); sc_name.trace('w', partial(limit_name_size, sc_name, name_length))
        sc_value = StringVar(); sc_value.trace('w', partial(limit, sc_value, 65535))
        sc_spell = StringVar()
        sc_cast_level = StringVar(); sc_cast_level.trace('w', partial(limit, sc_cast_level, 15))

        # build UI and initialize
        build()
        self.wand.set(self.wand_list[0])
        self.scroll.set(self.scroll_list[0])

# --- SpellEdit: Spell editor (name + balance knobs such as damage, stamina, range, school).
class SpellEdit:
    # Spell window: build inputs for balance/targeting knobs; wire save flash.
    def __init__(self, f):
        # window
        self.win = Toplevel()
        self.win.resizable(False, False)
        self.filename = f
        self.win.title("Spell Edit")

        # config
        self.data_seek = 25
        self.data_read = 11
        self.name_length = 22

        # lists
        self.spell_list, self.spell_addresses = get_major_name_lists(self.filename, SPELL_ADDRESSES, self.name_length)

        # variables
        self.spell = StringVar()
        self.spell.trace('w', self.set_defaults)
        self.name = StringVar()
        self.name.trace('w', partial(limit_name_size, self.name, self.name_length))
        self.damage = StringVar(); self.damage.trace('w', partial(limit, self.damage, 255))
        self.stamina = StringVar(); self.stamina.trace('w', partial(limit, self.stamina, 120))
        self.wizard = StringVar(); self.wizard.trace('w', partial(limit, self.wizard, 10))
        self.spell_range = StringVar(); self.spell_range.trace('w', partial(limit, self.spell_range, 255))
        self.exp = StringVar(); self.exp.trace('w', partial(limit, self.exp, 255))
        self.school = StringVar()
        self.target_num = StringVar()
        self.target_type = StringVar()
        # self.target_area = IntVar()
        self.aspect = IntVar()
        self.ingredient = StringVar()

        # build widgets
        self.box = Frame(self.win)
        self.default_spell_menu = Combobox(self.box, textvariable=self.spell, width=22,
                                           values=self.spell_list,
                                           postcommand=self.reset_list, state='readonly')
        self.new_name_label = LabelFrame(self.box, text='New Name')
        self.new_name_entry = Entry(self.new_name_label, textvariable=self.name, width=22)
        self.stats_frame = LabelFrame(self.box, text='Stats')
        self.damage_label = Label(self.stats_frame, text='Damage:')
        self.damage_entry = Entry(self.stats_frame, textvariable=self.damage, width=4)
        self.stamina_label = Label(self.stats_frame, text='Stamina Cost:')
        self.stamina_entry = Entry(self.stats_frame, textvariable=self.stamina, width=4)
        self.wizard_label = Label(self.stats_frame, text='Wizard Required:')
        self.wizard_entry = Entry(self.stats_frame, textvariable=self.wizard, width=4)
        self.range_label = Label(self.stats_frame, text='Range:')
        self.range_entry = Entry(self.stats_frame, textvariable=self.spell_range, width=4)
        self.exp_label1 = Label(self.stats_frame, text='EXP to Rank:')
        self.exp_entry = Entry(self.stats_frame, textvariable=self.exp, width=4)
        self.exp_label2 = Label(self.stats_frame, text='(Higher # = more EXP to rank)', font=(None, 8))

        # save button routed through wrapper for flash
        self.save_btn = Button(self.box, text='Save', command=self._on_save, width=8)

        self.aspect_frame = LabelFrame(self.box, text='Aspect')
        self.aspect_none = Radiobutton(self.aspect_frame, text='NONE', variable=self.aspect, value=0)
        self.aspect_solar = Radiobutton(self.aspect_frame, text='Solar', variable=self.aspect, value=4)
        self.aspect_lunar = Radiobutton(self.aspect_frame, text='Lunar', variable=self.aspect, value=3)

        self.school_frame = LabelFrame(self.box, text='School')
        self.school_box = Combobox(self.school_frame, textvariable=self.school, width=12, state='readonly',
                                   values=(list(SCHOOL.keys())[0:1] + list(SCHOOL.keys())[2:]))

        self.ingredient_frame = LabelFrame(self.box, text='Ingredient')
        self.ingredient_menu = Combobox(self.ingredient_frame, textvariable=self.ingredient, width=12,
                                        values=list(SPELL_INGREDIENTS.keys()), state='readonly')

        self.target_num_frame = LabelFrame(self.box, text='Number of targets:')
        self.target_num_menu = Combobox(self.target_num_frame, textvariable=self.target_num, width=23,
                                        values=list(TARGET_NUM.keys()), state='readonly')

        self.target_type_frame = LabelFrame(self.box, text='Who is targeted:')
        self.target_type_menu = Combobox(self.target_type_frame, textvariable=self.target_type,
                                         values=list(TARGET_TYPE.keys()),
                                         width=23, state='readonly')

        # run
        self.build()
        self.spell.set(self.spell_list[0])

    # load current selection into fields
    # Load selected spell, clamp aspect to allowed set, fill widgets.
    def set_defaults(self, *args):
        with open(self.filename, 'rb') as f:
            address = self.spell_addresses[self.default_spell_menu.current()]
            f.seek(address)
            self.name.set(f.read(self.name_length).decode("utf-8"))

            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            self.school.set(inv_SCHOOL[(d[0] + d[1]).upper()])
            self.damage.set(int(d[2] + d[3], 16))
            self.stamina.set(int(d[4] + d[5], 16))
            self.target_num.set(inv_TARGET_NUM[d[7]])
            self.target_type.set(inv_TARGET_TYPE[d[9]])
            self.wizard.set(int(d[12] + d[13], 16))

            # aspect byte is a single value, clamp to valid range
            asp = int(d[15], 16)
            if asp not in (0, 3, 4):
                asp = 0
            self.aspect.set(asp)

            self.spell_range.set(int(d[16] + d[17], 16))
            self.ingredient.set(inv_SPELL_INGREDIENTS[d[19]])
            self.exp.set(int(d[20] + d[21], 16))

    # write current fields back to ROM
    # Write spell fields back; preserve unknown bytes between known offsets.
    def write(self):
        with open(self.filename, 'rb+') as f:
            address = self.spell_addresses[self.default_spell_menu.current()]

            # write name
            new_name = bytearray(self.name.get(), 'utf-8')
            if len(new_name) < self.name_length:
                while len(new_name) < self.name_length:
                    new_name.append(0x00)
            f.seek(address)
            f.write(new_name)

            # read existing bytes to preserve unknowns
            f.seek(address + self.data_seek)
            d = f.read(self.data_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs

            # assemble bytes to write
            towrite = [
                SCHOOL[self.school.get()],
                self.damage.get(),
                self.stamina.get(),
                TARGET_NUM[self.target_num.get()],
                TARGET_TYPE[self.target_type.get()],
                (d[10] + d[11]),
                self.wizard.get(),
                self.aspect.get(),
                self.spell_range.get(),
                SPELL_INGREDIENTS[self.ingredient.get()],
                self.exp.get()
            ]

            # write block
            f.seek(address + self.data_seek)
            for item in towrite:
                item = int_cast(item)
                f.write(item.to_bytes(1, byteorder='big'))  # write one unsigned byte)

            # refresh list and keep selection on renamed item
            self.reset_list()
            self.spell.set(self.spell_list[self.spell_list.index(self.name.get().rstrip('\x00'))])
        self.set_defaults()

    # save wrapper to show flash near the Save button
    # Save wrapper to show a toast and re-enable the button on exit.
    def _on_save(self):
        try:
            self.save_btn.configure(state='disabled')
            self.write()
            flash_saved(self.save_btn, "Saved", ms=1200)
        finally:
            self.save_btn.configure(state='normal')

    # layout
    # Lay out the spell editor controls.
    def build(self):
        self.box.grid(column=0, row=0, pady=5, padx=5)

        self.default_spell_menu.grid(column=0, row=0)

        self.new_name_label.grid(column=0, row=1)
        self.new_name_entry.grid()

        self.stats_frame.grid(column=0, row=2, rowspan=4)
        self.damage_label.grid(column=0, row=0, sticky='e')
        self.damage_entry.grid(column=1, row=0, sticky='w')

        self.stamina_label.grid(column=0, row=1, sticky='e')
        self.stamina_entry.grid(column=1, row=1, sticky='w')

        self.wizard_label.grid(column=0, row=2, sticky='e')
        self.wizard_entry.grid(column=1, row=2, sticky='w')

        self.range_label.grid(column=0, row=3, sticky='e')
        self.range_entry.grid(column=1, row=3, sticky='w')

        self.exp_label1.grid(column=0, row=4, sticky='e')
        self.exp_entry.grid(column=1, row=4, sticky='w')
        self.exp_label2.grid(row=5, columnspan=3, rowspan=2, sticky='ew')

        self.save_btn.grid(column=1, row=0)

        self.aspect_frame.grid(column=1, row=1)
        self.aspect_none.grid(column=0, row=0)
        self.aspect_solar.grid(column=1, row=0)
        self.aspect_lunar.grid(column=2, row=0)

        self.school_frame.grid(column=1, row=2)
        self.school_box.grid()

        self.ingredient_frame.grid(column=1, row=3)
        self.ingredient_menu.grid(column=0, row=0)

        self.target_num_frame.grid(column=1, row=4)
        self.target_num_menu.grid()

        self.target_type_frame.grid(column=1, row=5)
        self.target_type_menu.grid()

    # refresh dropdown values from ROM
    # Refresh combobox values from ROM after rename.
    def reset_list(self):
        self.spell_list[:] = []
        self.spell_addresses[:] = []
        self.spell_list, self.spell_addresses = get_major_name_lists(self.filename, SPELL_ADDRESSES, self.name_length)
        self.default_spell_menu['values'] = self.spell_list
# --- TrainerEdit: Trainer/shop editor. Left pane teaches skills/spells; right pane manages shop inventory.
class TrainerEdit:
    # Trainer/shop window: init data tables + left (skills/spells) and right (shop) panes.
    def __init__(self, f):
        # window init
        self.win = Toplevel()
        self.win.resizable(False, False)
        self.filename = f
        self.win.title("Shops and Trainer Edit")
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_columnconfigure(1, weight=1)

        # read sizes
        self.skill_read = 23
        self.shield_read = 1
        self.spell_read = 16

        # trainers without shops
        self.NOT_SHOPS = [
            "Talewok : Dryad",
            "Talewok : Professor 1",
            "Talewok : Professor 2",
            "Talewok : Professor 3",
        ]

        # build shops list with Becan name from rom
        self.shops = []
        with open(self.filename, "rb") as fobj:
            fobj.seek(0x01FC7EA4)
            self.becan = "Erromon : " + fobj.read(9).decode("utf-8").rstrip("\x00")
            self.shops = [self.becan] + SHOPS

        # dictionaries
        self.items = get_major_item_dic(self.filename)
        self.inv_items = {v: k for k, v in self.items.items()}
        self.spell_dic = get_minor_dic(self.filename, SPELL_DIC, 22)
        self.inv_spell_dic = {v: k for k, v in self.spell_dic.items()}

        # trainer var
        self.trainer = StringVar()
        self.trainer.trace("w", self.defaults)
        self.trainer.trace("w", self.skill_frame_text)

        # skill vars
        self.skills = []
        for _ in SKILLS:
            v = StringVar()
            v.trace("w", partial(limit, v, 10))
            self.skills.append(v)
        self.shield_skill = StringVar()
        self.shield_skill.trace("w", partial(limit, self.shield_skill, 10))

        # spell vars
        self.spells = []
        for _ in range(5):
            self.spells.append(StringVar())

        self.spell_levels = []
        for _ in range(5):
            v = StringVar()
            v.trace("w", partial(limit, v, 15))
            self.spell_levels.append(v)

        # shop item vars
        self.shop_item = []
        for _ in range(23):
            self.shop_item.append(StringVar())

        # top Becan banners
        self.becan_warning = Label(
            self.win,
            text="Skill changes here for Becan affect his party character. These changes are new game only",
            fg="red",
            font=(None, 9, "bold"),
            anchor="w",
            justify="left",
        )
        self.becan_warning2 = Label(
            self.win,
            text="Blank skill level means Becan cannot learn this skill",
            fg="red",
            font=(None, 9, "bold"),
            anchor="center",
            justify="center",
        )

        # left and right panes
        self.main_win = Frame(self.win)
        self.main_win.grid(column=0, row=2, pady=5, padx=(5, 0))

        self.shop_win = LabelFrame(self.win, text="Shop Items")
        self.shop_win.grid(column=1, row=2, pady=5, padx=(0, 5), sticky="n")

        # trainer selector and save button
        self.default_name_menu = Combobox(
            self.main_win,
            textvariable=self.trainer,
            values=self.shops,
            width=26,
            state="readonly",
        )
        self.save = Button(self.main_win, text="Save", command=self.write, width=8)

        # spells frame
        self.spell_frame = LabelFrame(self.main_win, text="Spells and Spell Level")
        self.spell = []
        self.spell_level = []
        for i in range(5):
            self.spell.append(
                Combobox(
                    self.spell_frame,
                    textvariable=self.spells[i],
                    values=list(self.inv_spell_dic.keys()),
                    state="readonly",
                    width=16,
                )
            )
            self.spell_level.append(
                Entry(self.spell_frame, textvariable=self.spell_levels[i], width=4)
            )

        # skills frame
        self.skill_frame = LabelFrame(self.main_win, text="Skills", labelanchor="n")
        self.shield_label = Label(self.skill_frame, text="Shield", anchor="e", width=9)
        self.shield_num = Entry(self.skill_frame, textvariable=self.shield_skill, width=4)

        # notes box with single note
        self.note_box = LabelFrame(self.main_win, text="Notes on skills")
        self.note = Label(
            self.note_box,
            anchor="w",
            width=30,
            font=(None, 8),
            text="* Blank and 0 mean those particular\nskills are not taught",
        )

        # shop item widgets
        self.item_box = []
        for i in range(23):
            self.item_box.append(
                Combobox(
                    self.shop_win,
                    width=28,
                    state="readonly",
                    textvariable=self.shop_item[i],
                    values=list(self.inv_items.keys()),
                )
            )

        # initial selection
        self.trainer.set(self.shops[0])
        self.build()

    # Populate all widgets from ROM for the selected trainer; hides shop when N/A.
    def defaults(self, *args):
        # refresh all widgets from rom for selected trainer
        with open(self.filename, "rb") as fobj:
            # skills
            address = SHOP_TRAINERS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            d = fobj.read(self.skill_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
            for s in self.skills:
                x = self.skills.index(s) * 2
                sn = int(d[x] + d[x + 1], 16)
                if sn == 255:
                    sn = ""
                s.set(sn)

            # shield
            address = SHOP_SHIELDS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            d = fobj.read(self.shield_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
            shi = int(d[0] + d[1], 16)
            if shi == 255:
                shi = ""
            self.shield_skill.set(shi)

            # spells and levels
            address = SHOP_SPELLS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            d = fobj.read(self.spell_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
            for s in self.spells:
                x = self.spells.index(s) * 4
                y = x + 4
                s.set(self.spell_dic[d[x:y].upper()])
            for s in self.spell_levels:
                x = (self.spell_levels.index(s) * 2) + 22
                s.set(int(d[x] + d[x + 1], 16))

            # shop inventory
            if self.trainer.get() in self.NOT_SHOPS:
                self.shop_win.grid_forget()
                for item in self.shop_item:
                    item.set("")
            else:
                self.shop_win.grid(column=1, row=2, pady=5, padx=(0, 5), sticky="n")
                address = SHOP_ITEMS[self.shops.index(self.trainer.get())]
                fobj.seek(address)
                for item in self.shop_item:
                    d = fobj.read(2).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
                    item.set(self.items[d[0:4].upper()])
                    if self.shop_item.index(item) < 20:
                        address += 5
                        fobj.seek(address)
                    else:
                        address += 2
                        fobj.seek(address)

    # Write skills, shield, spells, and inventory back to ROM; preserve delimiters.
    def write(self):
        # write current values to rom for selected trainer
        with open(self.filename, "rb+") as fobj:
            # skills
            address = SHOP_TRAINERS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            towrite = []
            for v in self.skills:
                j = v.get()
                if j == "":
                    j = "255"
                towrite.append(j)
            fobj.seek(address)
            if self.trainer.get() == self.becan:
                for b in towrite:
                    b = int_cast(b)
                    fobj.write(b.to_bytes(1, byteorder="big"))
            else:
                for b in towrite:
                    if b == "255":
                        b = "0"
                    b = int_cast(b)
                    fobj.write(b.to_bytes(1, byteorder="big"))

            # shield
            towrite[:] = []
            address = SHOP_SHIELDS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            shi = self.shield_skill.get()
            if shi == "":
                shi = 255
            towrite.append(shi)
            if self.trainer.get() == self.becan:
                for b in towrite:
                    b = int_cast(b)
                    fobj.write(b.to_bytes(1, byteorder="big"))
            else:
                for b in towrite:
                    if b == "255":
                        b = "0"
                    b = int_cast(b)
                    fobj.write(b.to_bytes(1, byteorder="big"))

            # spells
            towrite[:] = []
            address = SHOP_SPELLS[self.shops.index(self.trainer.get())]
            fobj.seek(address)
            d = fobj.read(self.spell_read).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
            for v in self.spells:
                towrite.append(int(self.inv_spell_dic[v.get()][:2], 16))
                towrite.append(int(self.inv_spell_dic[v.get()][2:], 16))
            towrite.append(d[9] + d[10])  # preserve delimiter
            for v in self.spell_levels:
                towrite.append(v.get())
            fobj.seek(address)
            for b in towrite:
                b = int_cast(b)
                fobj.write(b.to_bytes(1, byteorder="big"))

            # shop inventory
            towrite[:] = []
            if self.trainer.get() not in self.NOT_SHOPS:
                address = SHOP_ITEMS[self.shops.index(self.trainer.get())]
                fobj.seek(address)
                d = fobj.read(106).hex()  # hex-encoded bytes from ROM; indexes below use big-endian pairs
                for item in self.shop_item:
                    towrite.append(int((self.inv_items[item.get()])[:2], 16))
                    towrite.append(int((self.inv_items[item.get()])[2:4], 16))
                    if self.shop_item.index(item) < 20:
                        for x in range(5, 11, 2):
                            towrite.append(
                                int(
                                    d[((self.shop_item.index(item) * 10) + (x - 1))]
                                    + d[((self.shop_item.index(item) * 10) + x)],
                                    16,
                                )
                            )
                fobj.seek(address)
                for b in towrite:
                    fobj.write(b.to_bytes(1, byteorder="big"))

        self.defaults()
        flash_saved(self.save)  # toast at save button

    # Grid banner + panes; create rows of skill entries and shop items.
    def build(self):
        # banners across top then controls
        self.becan_warning.grid(column=0, row=0, columnspan=2, sticky="we", padx=5, pady=(5, 0))
        self.becan_warning2.grid(column=0, row=1, columnspan=2, sticky="we", padx=5, pady=(0, 6))
        self.becan_warning.grid_remove()
        self.becan_warning2.grid_remove()

        self.default_name_menu.grid(column=0, row=0)
        self.save.grid(column=0, row=1)

        # spells layout
        self.spell_frame.grid(column=0, row=2)
        for x in range(5):
            self.spell[x].grid(column=0, row=x, sticky="e")
            self.spell_level[x].grid(column=1, row=x, sticky="w")

        # skills layout
        self.skill_frame.grid(column=1, row=0, rowspan=24, padx=(2, 5))
        for idx, skill in enumerate(SKILLS):
            Label(self.skill_frame, text=skill, anchor="e", width=9).grid(
                column=0, row=idx
            )
            Entry(self.skill_frame, textvariable=self.skills[idx], width=4).grid(
                column=1, row=idx
            )
        self.shield_label.grid(column=0, row=23)
        self.shield_num.grid(column=1, row=23)

        # notes layout
        self.note_box.grid(column=0, row=3)
        self.note.grid()
        self.note.configure(relief="flat")

        # shop items layout
        for item in self.item_box:
            item.grid()

        # finalize banner visibility
        self.skill_frame_text()

    # Toggle red warning banners and padding for Becan (special case).
    def skill_frame_text(self, *args):
        # show or hide Becan banners and adjust padding
        if self.trainer.get() == self.becan:
            self.skill_frame["text"] = "Skills"
            self.skill_frame.grid(ipadx=0)
            self.becan_warning.grid()
            self.becan_warning2.grid()
        else:
            self.skill_frame["text"] = "Skills"
            self.skill_frame.grid(ipadx=15)
            self.becan_warning.grid_remove()
            self.becan_warning2.grid_remove()

# functions.py
# Read a sequence of fixed-length names from the ROM and return a Python list.
def build_lst(filename, addresses, name_length):
    """Build a list of decoded strings read from `filename` at each address in `addresses`."""
    lst = []
    with open(filename, 'rb') as f:
        for a in addresses:
            f.seek(a)
            lst.append(f.read(name_length).decode("utf-8").rstrip('\x00'))
    return lst


# Build an ID→name mapping for minor tables (e.g., spells). Injects '0000'→'NONE'.
def get_minor_dic(filename, dic, name_length):
    """
    Create an ID/Name dictionary using ROM addresses as keys.

    Returns: {'0000': 'NONE', <hex_code>: <name>, ...}
    """
    name = []
    code = []
    with open(filename, 'rb') as f:
        for a in dic.keys():
            f.seek(a)
            name.append(f.read(name_length).decode("utf-8").rstrip('\x00'))
        for b in dic.values():
            code.append(b)
        name, code = (list(t) for t in zip(*sorted(zip(name, code))))
    return {**{'0000': 'NONE'}, **dict(zip(code, name))}


# Build an ID→'(type) name' dict for items; handles potion endian quirk.
def get_major_item_dic(filename):
    """
    Build an ID/Name dictionary for items with a (type) prefix.
    Potions are handled via INV_POTIONS because their id/type bytes are stored in reversed order.
    """
    lst = []
    val = []

    with open(filename, 'rb') as f:
        for code in ITEM_DIC.values():
            suffix = code[2:]           # last 2 hex chars = type
            addr = inv_ITEM_DIC.get(code)

            # Potions: ITEM_DIC uses little-endian "id|type"; POTIONS/INV_POTIONS use "type|id".
            if suffix == '10':
                swapped = code[2:] + code[:2]   # e.g. "0310" -> "1003"
                potion_name = INV_POTIONS.get(swapped)
                if potion_name:
                    lst.append(potion_name)
                    val.append(code)
                continue

            label = None
            if   suffix == '01': label = '(misc)'
            elif suffix == '05': label = '(armor)'
            elif suffix == '06': label = '(shield)'
            elif suffix == '07': label = '(weapon)'
            elif suffix == '09': label = '(helmet)'
            elif suffix == '0A': label = '(cloak)'
            elif suffix == '0B': label = '(glove)'
            elif suffix == '0C': label = '(ring)'
            elif suffix == '0D': label = '(wand)'
            elif suffix == '0E': label = '(belt)'
            elif suffix == '0F': label = '(boots)'
            elif suffix == '11': label = '(scroll)'
            elif suffix == '12': label = '(key)'
            elif suffix == '13': label = '(amulet)'

            if label:
                f.seek(addr)
                word = f.read(18).decode("utf-8").rstrip('\x00')
                lst.append(f"{label} {word}")
                val.append(code)

    lst, val = (list(t) for t in zip(*sorted(zip(lst, val))))
    return {**{'0000': 'NONE'}, **dict(zip(val, lst))}


# Return parallel lists of names, codes, and addresses for loot tables (sorted by name).
def get_major_loot_lists(filename, addresses, name_length):
    """Return parallel lists of (names, codes, addresses) for loot drop tables."""
    name = []
    code = []
    address = []
    with open(filename, 'rb') as f:
        for a in addresses:
            f.seek(a)
            name.append(f.read(name_length).decode("utf-8").rstrip('\x00'))
            code.append(addresses.get(a))
            address.append(a)
    name, code, address = (list(t) for t in zip(*sorted(zip(name, code, address))))
    return name, code, address


# Return parallel lists of (name, address) for a set of records (sorted by name).
def get_major_name_lists(filename, addresses, name_length):
    """Return parallel lists of (names, addresses), sorted by name."""
    name = []
    address = []
    with open(filename, 'rb') as f:
        for a in addresses:
            f.seek(a)
            name.append(f.read(name_length).decode("utf-8").rstrip('\x00'))
            address.append(a)
    name, address = (list(t) for t in zip(*sorted(zip(name, address))))
    return name, address


# Best-effort cast of GUI strings to int (supports decimal and hex); blanks → 0.
def int_cast(val):
    """
    Convert numeric strings (decimal or hex) to int.
    Returns 0 for blanks/invalid values.
    """
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    try:
        return int(val, 16)
    except (ValueError, TypeError):
        return 0


# Tk helper: limit text to the ROM’s fixed-length field.
def limit_name_size(name, name_length, *args):
    """Tk variable helper: trim text to `name_length` characters."""
    n = name.get()
    if len(n) > name_length:
        name.set(n[:name_length])


# Tk helper: clamp numeric string to [0, max]; strips non-digits, normalizes '00'→'0'.
def limit(i, x, *args):
    """
    Tk variable helper: constrain numeric value to [0, x].
    - Strips non-digits
    - Converts '00' to '0'
    """
    if i.get() == '00':
        i.set('0')
    if not i.get().isnumeric():
        val = ''.join(filter(str.isnumeric, i.get()))
        i.set(val)
    elif i.get().isnumeric():
        if int(i.get()) > x:
            i.set(x)
        else:
            i.set(i.get())


# Tk helper: clamp to signed byte [-128, 127]; keeps a leading '-'.
def limit_127(i, *args):
    """
    Tk variable helper: constrain value to a signed byte range [-128, 127].
    Accepts leading '-'. Strips non-digits.
    """
    if i.get() == '00':
        i.set('0')
    val = i.get()
    if len(val) > 0 and val[0] == '-':
        if val == '-':
            return
        else:
            val = val[1:]
        if not val.isnumeric():
            val = ''.join(filter(str.isnumeric, val))
            i.set(int(val) * -1)
        elif val.isnumeric():
            if int(val) > 127:
                i.set('-128')
            else:
                i.set(int(val) * -1)
    else:
        if not val.isnumeric():
            val = ''.join(filter(str.isnumeric, val))
            i.set(val)
        elif val.isnumeric():
            if int(val) > 127:
                i.set(127)
            else:
                i.set(val)

# views/notifications.py
# Tiny anchored toast near the triggering widget; used after saves/backups.
def flash_saved(anchor, msg="Saved", ms=1200):
    top = anchor.winfo_toplevel()
    tip = tk.Toplevel(top)
    tip.overrideredirect(True)
    tip.attributes("-topmost", True)
    lbl = tk.Label(tip, text=msg, bd=1, relief="solid", padx=8, pady=2)
    lbl.pack()
    tip.update_idletasks()

    ax = anchor.winfo_rootx()
    ay = anchor.winfo_rooty()
    aw = anchor.winfo_width()
    tw = tip.winfo_width()
    th = tip.winfo_height()
    x = ax + aw - tw - 6
    y = ay - th - 6

    tip.geometry(f"+{x}+{y}")
    tip.after(ms, tip.destroy)
# pyinstaller-compatible resource resolver
# Resolve resource paths for PyInstaller bundles or dev runs.
def resource_path(rel: str) -> str:
    # resolves bundled path at runtime (PyInstaller) or cwd during dev
    base = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return str(base / rel)


# app identity + asset paths
APP_TITLE = "Aidyn Editor"


# Open file picker and validate the chosen ROM path; show message boxes for errors.
def choose_rom(parent: tk.Tk) -> Path | None:
    # open file picker and validate basic ROM assumptions
    f = filedialog.askopenfilename(
        parent=parent,
        initialdir=str(Path.cwd()),
        title="Select A File",
        filetypes=[("z64", "*.z64")]
    )
    if not f:
        return None
    p = Path(f)
    if not p.exists() or not p.is_file():
        messagebox.showerror(APP_TITLE, "File not found or not a regular file.")
        return None
    if p.suffix.lower() != ".z64":
        messagebox.showerror(APP_TITLE, "Only .z64 files are supported.")
        return None
    if p.stat().st_size == 0:
        messagebox.showerror(APP_TITLE, "File is empty.")
        return None
    try:
        with p.open("rb"):
            pass
    except OSError as e:
        messagebox.showerror(APP_TITLE, f"Cannot open file:\n{e}")
        return None
    return p


# Create a sibling '(backup).z64' file next to the ROM; show error on failure.
def make_backup(rom: Path) -> Path | None:
    # create side-by-side backup file next to the selected ROM
    target = rom.with_name(f"{rom.stem} (backup){rom.suffix}")
    try:
        shutil.copy2(rom, target)
        return target
    except OSError as e:
        messagebox.showerror(APP_TITLE, f"Backup failed:\n{e}")
        return None


# Build the main launcher: logo + buttons that open each editor window.
def launchers(root: tk.Tk, rom_path: Path) -> None:
    # main launcher UI (left: logo, right: section buttons)
    root.configure(background="white")

    left = Frame(root)
    left.grid(column=0, row=0, padx=8, pady=8, sticky="n")
    right = Frame(root)
    right.grid(column=1, row=0, padx=(0, 8), pady=8, sticky="n")

    # logo (or text fallback)
    Label(left, text="Aidyn Editor", background="white").grid(sticky="n")

    # helpers
    btn_w = 16
    add = lambda r, txt, cmd: Button(right, text=txt, width=btn_w, command=cmd).grid(column=0, row=r, pady=2, sticky="ew")

    # route to editors (pass ROM filename)
    filename = str(rom_path)
    add(0, "Party", lambda: PartyEdit(filename, PARTY_ADDRESSES, 9, 78, 0))
    add(1, "Enemy", lambda: EnemyEdit(filename, ENEMY_ADDRESSES, 17, 92, 1))
    add(2, "Shop / Trainer", lambda: TrainerEdit(filename))
    add(3, "Accessory", lambda: AccessoryEdit(filename, ACCESSORY_ADDRESSES, 24, 20, 20))
    add(4, "Armor", lambda: ArmorShield(filename, ARMOR_ADDRESSES, 26, 25, 22, 5))
    add(5, "Shield", lambda: ArmorShield(filename, SHIELD_ADDRESSES, 26, 25, 22, 6))
    add(6, "Spell", lambda: SpellEdit(filename))
    add(7, "Wand / Scroll", lambda: WandScrollEdit(filename))
    add(8, "Weapon", lambda: WeaponEdit(filename, WEAPON_ADDRESSES, 23, 25, 21))


# Application entrypoint: creates root window, browse+backup bar, and event loop.
def main():
    # bootstrap root window
    root = tk.Tk()
    root.geometry("+300+150")
    root.resizable(False, False)
    root.title(APP_TITLE)

    # top strip: ROM selection + backup toggle
    browse = LabelFrame(root, text="Aidyn Chronicles ROM")
    browse.grid(column=0, row=0, padx=8, pady=8)

    backup_var = tk.BooleanVar(value=True)  # default: create backup

    # keep a reference to the Browse button to anchor flash popups
    browse_btn = Button(browse, text="Browse", width=12)
    browse_btn.grid(column=0, row=0, padx=6, pady=6)
    Checkbutton(browse, text="Backup", variable=backup_var).grid(column=1, row=0, padx=6, pady=6)

    def on_browse():
        # pick file, optionally back it up, then mount launchers
        rom = choose_rom(root)
        if not rom:
            return
        if backup_var.get():
            # attempt backup; show anchored success flash if created
            bk = make_backup(rom)
            if bk is None:
                return
            flash_saved(browse_btn, "Backup Created")
        # rebuild window with launcher grid
        for w in root.winfo_children():
            w.destroy()
        launchers(root, rom)

    # wire command after defining handler
    browse_btn.configure(command=on_browse)

    # event loop
    root.mainloop()

PARTY_ADDRESSES = [
    0x01FC7C84,  # Abrecan
    0x01FC7D0C,  # Alaron
    0x01FC7D94,  # Arturo
    0x01FC7E1C,  # Baird
    0x01FC7EA4,  # Becan
    0x01FC7F2C,  # Brenna
    0x01FC7FB4,  # Donovan
    0x01FC803C,  # Dougal
    0x01FC7BFC,  # Farris
    0x01FC80C4,  # Godric
    0x01FC814C,  # Keelin
    0x01FC81D4,  # Niesen
    0x01FC825C,  # Rheda
    0x01FC82E4   # Sholeh
]

ENEMY_ADDRESSES = [
    0x01FC92DC,  # Air Elemental
    0x01FC8BF4,  # Assim
    0x01FC6C8C,  # Bandit Boss 1
    0x01FC5E34,  # Bandit Boss 2
    0x01FC5DAC,  # Bandit Boss 3
    0x01FC5B04,  # Bandit Boss 4
    0x01FC5A7C,  # Bandit Boss 5
    0x01FC59F4,  # Bandit Boss 6
    0x01FC651C,  # Bandit Woodsman 1
    0x01FC5D24,  # Bandit Woodsman 2
    0x01FC5C9C,  # Bandit Woodsman 3
    0x01FC9A50,  # Bear
    0x01FC8B6C,  # Behrooz
    0x01FC9AD8,  # Boar
    0x01FC98B8,  # Cave Bear
    0x01FC83FC,  # Chaos Lieutenant
    0x01FC8484,  # Chaos Major
    0x01FC684C,  # Chaos Mauler
    0x01FC66B4,  # Chaos Scout
    0x01FC5FCC,  # Chaos Slayer
    0x01FC662C,  # Chaos Sorceror
    0x01FC6054,  # Chaos Spellweaver
    0x01FC60DC,  # Chaos Stormer
    0x01FC67C4,  # Chaos Trooper
    0x01FC673C,  # Chaos Warrior
    0x01FC6AF4,  # Cyclops
    0x01FC99C8,  # Darkenbat
    0x01FC97A8,  # Dire Wolf
    0x01FCA0B0,  # Dracovern
    0x01FC9364,  # Dust Devil
    0x01FC93EC,  # Earth Elemental
    0x01FC5C14,  # Female Dryad
    0x01FC9474,  # Fire Elemental
    0x01FC9144,  # Firelord
    0x01FC9B60,  # Giant Bat
    0x01FC9610,  # Giant Boar
    0x01FC9254,  # Giant Golem
    0x01FC9BE8,  # Giant Rat
    0x01FC9C70,  # Giant Scorpion
    0x01FC8D04,  # Giant Skeleton
    0x01FC9CF8,  # Giant Squid
    0x01FC68D4,  # Goblin
    0x01FC61EC,  # Goblin 2
    0x01FC640C,  # Goblin Poisoner 1
    0x01FC62FC,  # Goblin Poisoner 2
    0x01FC65A4,  # Goblin Scout 1
    0x01FC6384,  # Goblin Scout 2
    0x01FC695C,  # Goblin Sergeant 1
    0x01FC6274,  # Goblin Sergeant 2
    0x01FC8A5C,  # Golnar
    0x01FC69E4,  # Gorgon
    0x01FC9D80,  # Gryphon
    0x01FC6A6C,  # Harpy
    0x01FC9E08,  # Hellhound
    0x01FC6B7C,  # Hobgoblin 1
    0x01FC6164,  # Hobgoblin 2
    0x01FC6C04,  # Human Bandit 1
    0x01FC5F44,  # Human Bandit 2
    0x01FC5EBC,  # Human Bandit 3
    0x01FC850C,  # Kitarak
    0x01FC88C4,  # Ksathra
    0x01FC9940,  # Large Scorpion
    0x01FC9698,  # Lava Hound
    0x01FC6D14,  # Lizard Man
    0x01FC8594,  # Lizard Man Boss
    0x01FC6D9C,  # Lizard Man Sgt
    0x01FC8E9C,  # Lugash
    0x01FC5B8C,  # Male Dryad
    0x01FC9E90,  # Manticore
    0x01FC861C,  # Marquis
    0x01FC89D4,  # Mehrdad
    0x01FC6FBC,  # Minotaur
    0x01FC8374,  # Minotaur Lord
    0x01FC8AE4,  # Nasim
    0x01FC6E24,  # Ogre 1
    0x01FC6494,  # Ogre 2
    0x01FC6EAC,  # Ogre Boss
    0x01FC8C7C,  # Plague Zombie
    0x01FC86A4,  # Pochanargat
    0x01FC9F18,  # Salamander
    0x01FC9FA0,  # Sand Worm
    0x01FC872C,  # Shadow
    0x01FC87B4,  # Shamsuk
    0x01FC894C,  # Shatrevar
    0x01FC883C,  # Sheridan
    0x01FC8D8C,  # Skeleton 1
    0x01FC8F24,  # Skeleton 2
    0x01FC8E14,  # Skeleton Archer
    0x01FC91CC,  # Spirit Wolf
    0x01FC94FC,  # Stone Golem
    0x01FC9830,  # Tomb Rat
    0x01FC6F34,  # Troll
    0x01FC9584,  # Water Elemental
    0x01FC8FAC,  # Wight
    0x01FCA028,  # Wolf
    0x01FC9034,  # Wraith
    0x01FC9720,  # Wyvern
    0x01FC90BC   # Zombie
]

ACCESSORY_ADDRESSES = [
    0x01FCEB0C,  # Amulet of Pork
    0x01FCD918,  # Banner of Gwernia
    0x01FCD2E0,  # Bardic Gloves
    0x01FCDA7C,  # Belt of Life
    0x01FCDA50,  # Belt of Teleport
    0x01FCDAD8,  # Boots of Adamant
    0x01FCDB30,  # Boots of Speed
    0x01FCDB88,  # Boots of Striding
    0x01FCD49C,  # Etherial Ring
    0x01FCD4F8,  # Gem of Aspect
    0x01FCD524,  # Gem of Sensing
    0x01FCD338,  # Gloves of Healing
    0x01FCD9F4,  # Harp of Igone
    0x01FCEB90,  # Haste Amulet
    0x01FCEC14,  # Heart of Elisheva
    0x01FCD0C8,  # Helm of Charisma
    0x01FCD120,  # Helm of Defense
    0x01FCD14C,  # Helm of Tempests
    0x01FCD0F4,  # Helm of Wisdom
    0x01FCD9C8,  # Horn of Kynon
    0x01FCD390,  # Jundar Gauntlets
    0x01FCD178,  # Kendall's Hat
    0x01FCDB5C,  # Leather Boots
    0x01FCD22C,  # Leather Cloak
    0x01FCD444,  # Lunar Ring
    0x01FCD3EC,  # Magedrake Ring
    0x01FCEAE0,  # Marquis' Amulet
    0x01FCDAA8,  # Mercenary Belt
    0x01FCD284,  # Mirari Cloak
    0x01FCEB38,  # Mirror Amulet
    0x01FCD944,  # Moon Gem
    0x01FCD418,  # Namers Ring
    0x01FCD200,  # Nightdrake Mantle
    0x01FCEBE8,  # Pandara's Amulet
    0x01FCD258,  # Phantom Cloak
    0x01FCD2B4,  # Plate Gauntlets
    0x01FCDA24,  # Reflection Belt
    0x01FCD3C0,  # Ring of Healing
    0x01FCD4CC,  # Rope
    0x01FCEC40,  # Shamsuk Amulet
    0x01FCEB64,  # Shield Amulet
    0x01FCD1A4,  # Spiritdrake Helm
    0x01FCEBBC,  # ST Gem
    0x01FCD970,  # Stormbreaker
    0x01FCD364,  # Stormdrake Claws
    0x01FCD30C,  # Tinker's Gloves
    0x01FCD470,  # Witch Ring
    0x01FCD1D0,  # Wizard Hat
    0x01FCD99C,  # Wizard's Wand
    0x01FCDB04   # Woodsman's Boots
]

ARMOR_ADDRESSES = [
    0x01FCBA98,  # Beast Hide
    0x01FCBB88,  # Chainmail
    0x01FCBDF8,  # Chaos Armor
    0x01FCB528,  # Chaos Robes
    0x01FCBAF8,  # Cloth Armor
    0x01FCBA38,  # Darkenbat Hide
    0x01FCBC78,  # Dragon Leather
    0x01FCBC48,  # Enchanted Hide
    0x01FCBD98,  # Enchanted Plate
    0x01FCBA08,  # exp 1
    0x01FCB858,  # exp 10
    0x01FCB828,  # exp 11
    0x01FCB7F8,  # exp 12
    0x01FCB7C8,  # exp 13
    0x01FCB798,  # exp 14
    0x01FCB768,  # exp 15
    0x01FCB738,  # exp 16
    0x01FCB708,  # exp 17
    0x01FCB6D8,  # exp 18
    0x01FCB6A8,  # exp 19
    0x01FCB9D8,  # exp 2
    0x01FCB678,  # exp 20
    0x01FCB648,  # exp 21
    0x01FCB618,  # exp 22
    0x01FCB9A8,  # exp 3
    0x01FCB978,  # exp 4
    0x01FCB948,  # exp 5
    0x01FCB918,  # exp 6
    0x01FCB8E8,  # exp 7
    0x01FCB8B8,  # exp 8
    0x01FCB888,  # exp 9
    0x01FCB5E8,  # exp23
    0x01FCB5B8,  # exp24
    0x01FCBBE8,  # Full Platemail
    0x01FCBA68,  # Hellhound Hide
    0x01FCBD38,  # Iden Scale
    0x01FCBC18,  # Improved Plate
    0x01FCB588,  # Irondrake Plate
    0x01FCBCA8,  # Jundar Leather
    0x01FCBB28,  # Leather Armor
    0x01FCBBB8,  # Partial Platemail
    0x01FCBD68,  # Pome Scale
    0x01FCBDC8,  # Royal Platemail
    0x01FCBB58,  # Scale Armor
    0x01FCBAC8,  # Scorpion scale
    0x01FCB558,  # Sheridans Armor
    0x01FCBCD8,  # Talewok Mail
    0x01FCBD08   # Terminor Mail
]

SCROLL_ADDRESSES = [
    0x01FCE3A0,  # Detect Chaos
    0x01FCE374,  # Detect Traps
    0x01FCE608,  # Acid Bolt
    0x01FCDBB8,  # Air Shield
    0x01FCE5DC,  # Aura of Death
    0x01FCE584,  # Banishing
    0x01FCE558,  # Brilliance
    0x01FCE52C,  # Charming
    0x01FCE500,  # Cheat Death
    0x01FCE26C,  # Clumsiness
    0x01FCE4D4,  # Command
    0x01FCDBE4,  # Control Elem
    0x01FCE450,  # Crushing Death
    0x01FCE4A8,  # Ctrl Marquis
    0x01FCE47C,  # Ctrl Zombie
    0x01FCE424,  # Darkness
    0x01FCDC10,  # Debilitation
    0x01FCE3A0,  # Detect Chaos
    0x01FCE374,  # Detect Traps
    0x01FCE348,  # Dexterity
    0x01FCE31C,  # Dispel Elem
    0x01FCE2F0,  # Dispel Naming
    0x01FCE2C4,  # Dispel Necro
    0x01FCE298,  # Dispel Star
    0x01FCDC3C,  # Dragon Flames
    0x01FCE3F8,  # Dt Moon Phase
    0x01FCE3CC,  # Dt Sun Phase
    0x01FCDC68,  # Earth Smite
    0x01FCDDC8,  # Endurance
    0x01FCDC94,  # Escape
    0x01FCE0B4,  # Exhaustion
    0x01FCE634,  # Fireball
    0x01FCE240,  # Frozen Doom
    0x01FCE214,  # Haste
    0x01FCDCC0,  # Immolation
    0x01FCE1E8,  # Know Aspect
    0x01FCE1BC,  # Light
    0x01FCDCEC,  # Lightning
    0x01FCE190,  # Mirror
    0x01FCE138,  # Opening
    0x01FCDE20,  # Oriana's Scroll
    0x01FCE10C,  # Photosynth
    0x01FCDD18,  # Remove Poison
    0x01FCDE4C,  # Sense Aura
    0x01FCE0E0,  # Shield of Starlight
    0x01FCE5B0,  # Solar Wrath
    0x01FCE088,  # Spirit Shield
    0x01FCE05C,  # Stamina
    0x01FCE030,  # Stealth
    0x01FCE004,  # Stellar Grav
    0x01FCDD44,  # Strength
    0x01FCE164,  # Stupidity
    0x01FCDFD8,  # Tap Stamina
    0x01FCDD70,  # Teleport (Wraith Touch)
    0x01FCDFAC,  # Teleport (Teleport)
    0x01FCDF80,  # vs Elemental
    0x01FCDF54,  # vs Naming
    0x01FCDF28,  # vs Necromancy
    0x01FCDEFC,  # vs Star
    0x01FCDED0,  # Wall of Bones
    0x01FCDD9C,  # Weakness
    0x01FCDEA4,  # Web of Starlight
    0x01FCDE78,  # Whitefire
    0x01FCDDF4   # Wind
]

SHIELD_ADDRESSES = [
    0x01FCC0FC,  # Bronze Shield
    0x01FCBFDC,  # Buckler
    0x01FCC1BC,  # Chaos Shield
    0x01FCBE2C,  # Crab Shield
    0x01FCBE8C,  # Dryad Shield
    0x01FCC0CC,  # Heater Shield
    0x01FCC18C,  # Hoplite Shield
    0x01FCC12C,  # Jundar Shield
    0x01FCC06C,  # Kite Shield
    0x01FCC03C,  # Large Shield
    0x01FCBF4C,  # Moon Shield
    0x01FCBFAC,  # Scorpion Shield
    0x01FCBEBC,  # Sheridans Shield
    0x01FCC00C,  # Small Shield
    0x01FCC15C,  # Spirit Shield
    0x01FCBEEC,  # Stardrake Aegis
    0x01FCBF7C,  # Sun Shield
    0x01FCC09C,  # Tower Shield
    0x01FCBF1C,  # Turtleshell Shield
    0x01FCBE5C   # Wight Shield
]

SPELL_ADDRESSES = [
    0x01FCC564,  # Acid Bolt
    0x01FCC268,  # Air Shield
    0x01FCC588,  # Aura of Death
    0x01FCC41C,  # Banishing
    0x01FCC3D4,  # Brilliance
    0x01FCC440,  # Charming
    0x01FCC540,  # Cheat Death
    0x01FCC95C,  # Clumsiness
    0x01FCC28C,  # Control Elem
    0x01FCC464,  # Control Marquis
    0x01FCC5D0,  # Control Zombies
    0x01FCC5F4,  # Crushing Death
    0x01FCC618,  # Darkness
    0x01FCC2B0,  # Debilitation
    0x01FCC8F0,  # Detect Moon Phase
    0x01FCC914,  # Detect Sun Phase
    0x01FCC488,  # Detecting Traps
    0x01FCC938,  # Dexterity
    0x01FCC7F0,  # Dispel Elemental
    0x01FCC814,  # Dispel Naming
    0x01FCC838,  # Dispel Necro
    0x01FCC85C,  # Dispel Star
    0x01FCC2D4,  # Dragon Flames
    0x01FCC2F8,  # Earth Smite
    0x01FCC4AC,  # Endurance
    0x01FCC220,  # Escape
    0x01FCC660,  # Exhaustion
    0x01FCC31C,  # Fireball
    0x01FCC980,  # Frozen Doom
    0x01FCC63C,  # Haste
    0x01FCC1FC,  # Immolation
    0x01FCC9A4,  # Light
    0x01FCC340,  # Lightning
    0x01FCC73C,  # Mirror
    0x01FCC4D0,  # Opening
    0x01FCC884,  # Photosynthesis
    0x01FCC718,  # Poison
    0x01FCC244,  # Remove Poison
    0x01FCC4F4,  # Sense Aura
    0x01FCC8A8,  # Solar Wrath
    0x01FCC6F0,  # Spirit Shield
    0x01FCC684,  # Stamina
    0x01FCC8CC,  # Starlight Shield
    0x01FCC9C8,  # Stealth
    0x01FCC9EC,  # Stellar Gravity
    0x01FCC364,  # Strength
    0x01FCC3F8,  # Stupidity
    0x01FCC6A8,  # Tap Stamina
    0x01FCC3B0,  # Teleportation
    0x01FCC760,  # vs. Elemental
    0x01FCC784,  # vs. Naming
    0x01FCC7A8,  # vs. Necromancy
    0x01FCC7CC,  # vs. Star
    0x01FCC6CC,  # Wall Of Bones
    0x01FCC518,  # Weakness
    0x01FCCA10,  # Web Of Starlight
    0x01FCCA34,  # Whitefire
    0x01FCC388,  # Wind
    0x01FCC5AC   # Wraith Touch
]

WAND_ADDRESSES = [
    0x01FCD5D4,  # Acid
    0x01FCD57C,  # Banishing
    0x01FCD6B0,  # Crushing Death
    0x01FCD708,  # Darkness
    0x01FCD7E4,  # Fireball
    0x01FCD6DC,  # Frozen Doom
    0x01FCD7B8,  # Gravity
    0x01FCD5A8,  # Immolation
    0x01FCD734,  # Light
    0x01FCD600,  # Lightning
    0x01FCD78C,  # Persuasion
    0x01FCD550,  # Revival
    0x01FCD760,  # Shielding
    0x01FCD658,  # Starfire
    0x01FCD810,  # Tap Stamina
    0x01FCD83C,  # vs Elemental
    0x01FCD868,  # vs Naming
    0x01FCD894,  # vs Necromancy
    0x01FCD8C0,  # vs Star
    0x01FCD8EC,  # Wall of Bones
    0x01FCD684,  # Web of Starlight
    0x01FCD62C   # Wraith Touch
]

WEAPON_ADDRESSES = [
    0x01FCA5A0,  # Air Fist
    0x01FCADBC,  # Archmage's Staff
    0x01FCA904,  # Battle Axe
    0x01FCA3B8,  # Bear Bite
    0x01FCA934,  # Blood Axe
    0x01FCB4C0,  # Boar Tusk
    0x01FCAB48,  # Bow of Accuracy
    0x01FCAB78,  # Bow of Shielding
    0x01FCABA8,  # Bow of Thunder
    0x01FCAD2C,  # Breklor's Firestaff
    0x01FCB158,  # Broadsword
    0x01FCA3E8,  # Buzzard Bite
    0x01FCAAE4,  # Chaos Deathwing
    0x01FCA814,  # Chaos Flameblade
    0x01FCA844,  # Chaos Maul
    0x01FCAAB4,  # Chaos Scythe
    0x01FCACFC,  # Chaos Staff
    0x01FCB1B8,  # Chaos Sword
    0x01FCAEB4,  # Chaos Tail
    0x01FCA964,  # Club
    0x01FCA754,  # Cyclops Club
    0x01FCB39C,  # Cyclops Hurlstar
    0x01FCB188,  # Dagger
    0x01FCB3CC,  # Dart of Distance
    0x01FCA4AC,  # Dragon Breath
    0x01FCA5D0,  # Dragon Claws
    0x01FCB30C,  # Dragon Fang
    0x01FCA600,  # Earth Fist
    0x01FCAD8C,  # Ehud's Staff
    0x01FCA8A4,  # Elisheva's Scythe
    0x01FCB038,  # Enchanted Blade
    0x01FCA268,  # expansion 10
    0x01FCA238,  # expansion 11
    0x01FCA208,  # expansion 12
    0x01FCA1D8,  # expansion 13
    0x01FCA1A8,  # expansion 14
    0x01FCA178,  # expansion 15
    0x01FCA388,  # expansion 4
    0x01FCA358,  # expansion 5
    0x01FCA328,  # expansion 6
    0x01FCA2F8,  # expansion 7
    0x01FCA2C8,  # expansion 8
    0x01FCA298,  # expansion 9
    0x01FCA630,  # Fire Touch
    0x01FCB068,  # Firedrake Fang
    0x01FCA4DC,  # Gaze
    0x01FCA8D4,  # Giant Axe
    0x01FCB248,  # Gladius
    0x01FCA9C4,  # Great Axe
    0x01FCAC08,  # Great Bow
    0x01FCB1E8,  # Great Sword
    0x01FCB45C,  # Hatchet
    0x01FCABD8,  # Heartseeker Bow
    0x01FCA724,  # Hockey Stick
    0x01FCAC38,  # Hunter's Bow
    0x01FCB098,  # Ice Stiletto
    0x01FCACCC,  # Ironwood Staff
    0x01FCB48C,  # Javelin
    0x01FCA7E4,  # Jester's Mace
    0x01FCAF78,  # Lightreaver
    0x01FCA874,  # Lizard King's Axe
    0x01FCB128,  # Lodin's Sword
    0x01FCAC68,  # Long Bow
    0x01FCB218,  # Longsword
    0x01FCA9F4,  # Mace
    0x01FCA7B4,  # Mace of Glory
    0x01FCA510,  # Marquis Touch
    0x01FCAA24,  # Maul
    0x01FCB4F0,  # Minotaur Butt
    0x01FCAA54,  # Morningstar
    0x01FCADEC,  # Pike
    0x01FCA540,  # Plague Claw
    0x01FCB3FC,  # Poison Dart
    0x01FCAB14,  # Poleaxe
    0x01FCAEE4,  # Pseudodragon Sting
    0x01FCA47C,  # Pseudopod
    0x01FCA418,  # Rat Bite
    0x01FCB278,  # Sabre
    0x01FCAF14,  # Scorpion Sting
    0x01FCA994,  # Scythe
    0x01FCB008,  # Sheridans Sword
    0x01FCAC98,  # Short Bow
    0x01FCB2A8,  # Short Sword
    0x01FCAE1C,  # Spear
    0x01FCA784,  # Spellbreaker Axe
    0x01FCB42C,  # Spikes
    0x01FCA148,  # Spirit Bite
    0x01FCAE4C,  # Staff
    0x01FCAD5C,  # Staff of Lugash
    0x01FCAFD8,  # Stealthblade
    0x01FCAFA8,  # Sword of Might
    0x01FCB2D8,  # Tanto
    0x01FCA660,  # Tentacle Slap
    0x01FCB33C,  # Throwing Iron
    0x01FCB36C,  # Throwing Knife
    0x01FCB0C8,  # Trahern's Sword
    0x01FCA690,  # Troll Claw
    0x01FCA570,  # Unarmed
    0x01FCAE80,  # Venom Spit
    0x01FCAA84,  # War Hammer
    0x01FCB0F8,  # Warfang
    0x01FCA448,  # Wolf Bite
    0x01FCA6C0,  # Wraith Touch
    0x01FCAF44,  # Wyvern Sting
    0x01FCA6F0   # Zombie Fist
]

SKILLS = [
    "Alchemist",
    "Diplomat",
    "Healer",
    "Loremaster",
    "Mechanic",
    "Merchant",
    "Ranger",
    "Stealth",
    "Thief",
    "Troubadour",
    "Warrior",
    "Wizard",
    "Bite",
    "Breath",
    "Claw",
    "Hafted",
    "Missile",
    "Pole",
    "Spit",
    "Sting",
    "Sword",
    "Throw",
    "Tusk",
]

ATTRIBUTES = ["Intelligence", "Willpower", "Dexterity", "Endurance", "Strength", "Stamina"]

SPELL_INGREDIENTS = {
    "NONE": "0",
    "Herb": "2",
    "Gemstone": "3",
    "Spice": "1"
}

inv_SPELL_INGREDIENTS = {v: k for k, v in SPELL_INGREDIENTS.items()}

TARGET_NUM = {
    "Increases by rank": "3",
    "Unlimited": "2",
    "One": "1",
    "Self": "0"
}

inv_TARGET_NUM = {v: k for k, v in TARGET_NUM.items()}

TARGET_TYPE = {
    "Everyone": "4",
    "Anyone in target area": "3",
    "Enemy only in target area": "2",
    "Party only in target area": "1",
    "Outside of combat (Useless)": "0"
}

inv_TARGET_TYPE = {v: k for k, v in TARGET_TYPE.items()}

WEAPON_TYPE = {
    "Bite": "0",
    "Breath": "1",
    "Claw": "2",
    "Hafted": "3",
    "Missile": "4",
    "Pole": "5",
    "Spit": "6",
    "Sting": "7",
    "Sword": "8",
    "Thrown": "9",
    "Tusk": "A"
}

inv_WEAPON_TYPE = {v: k for k, v in WEAPON_TYPE.items()}

EQUIPMENT_STAT = {
    "NONE": "FF",
    "Intelligence": "00",
    "Willpower": "01",
    "Dexterity": "02",
    "Endurance": "03",
    "Strength": "04",
    "Spell Battery": "05"
}

inv_EQUIPMENT_STAT = {v: k for k, v in EQUIPMENT_STAT.items()}

SKILL_ATTRIBUTE = {
    "NONE": "FF",
    "Alchemist": "00",
    "Diplomat": "01",
    "Healer": "02",
    "Loremaster": "03",
    "Mechanic": "04",
    "Merchant": "05",
    "Ranger": "06",
    "Stealth": "07",
    "Thief": "08",
    "Troubadour": "09",
    "Warrior": "0A",
    "Wizard": "0B",
    "Bite": "0C",
    "Breath": "0D",
    "Claw": "0E",
    "Hafted": "0F",
    "Missile": "10",
    "Pole": "11",
    "Spit": "12",
    "Sting": "13",
    "Sword": "14",
    "Thrown": "15",
    "Tusk": "16",
    "Intelligence": "20",
    "Willpower": "21",
    "Dexterity": "22",
    "Endurance": "23",
    "Strength": "24",
    "Stamina": "25"
}

inv_SKILL_ATTRIBUTE = {v: k for k, v in SKILL_ATTRIBUTE.items()}

RESIST = {
    "NONE": "00",
    "Air": "0A",
    "Chaos": "0D",
    "Cutting": "0E",
    "Earth": "01",
    "Elemental": "0C",
    "Fire": "05",
    "Holy": "10",
    "Lunar": "06",
    "Magic": "09",
    "Naming": "07",
    "Necromancy": "04",
    "Physical": "03",
    "Smashing": "0F",
    "Solar": "02",
    "Star": "0B",
    "Water": "08"
}

inv_RESIST = {v: k for k, v in RESIST.items()}

RESIST_AMOUNTS = {
    "100": "00",
    "75": "01",
    "50": "02",
    "25": "03",
    "0": "04",
    "-25": "05",
    "-50": "06",
    "-75": "07",
    "-100": "08",
    "-6275": "FF"
}

inv_RESIST_AMOUNTS = {v: k for k, v in RESIST_AMOUNTS.items()}

WEAPON_ANIMATIONS = {
    "Bite": "00",
    "Other": "01",
    "Stabbing": "02",
    "Slashing": "03",
    "Thrown": "04",
    "Missile": "05"
}

inv_WEAPON_ANIMATIONS = {v: k for k, v in WEAPON_ANIMATIONS.items()}

SHOPS = [
    "Erromon : Cavern Female",
    "Erromon : Cavern Male",
    "Erromon : Shop-A Male",
    "Erromon : Shop-B Female",
    "Erromon : Shop-B Female",
    "Erromon : Shop-B Male",
    "Erromon : Shop-C Female 1",
    "Erromon : Shop-C Female 2 ",
    "Erromon : Shop-C Female 3",
    "Erromon : Shop-C Female 4",
    "Erromon : Shop-D Female",
    "Erromon : Shop-D Male",
    "Erromon : Shop-E Female",
    "Erromon : Shop-E Male",

    "Gwernia : Shop-A",
    "Gwernia : Shop-B",

    "Port Saiid : Shop-A Bandit",
    "Port Saiid : Shop-A Female",
    "Port Saiid : Shop-B",
    "Port Saiid : Shop-C",
    "Port Saiid : Shop-D",
    "Port Saiid : Shop-E",
    "Port Saiid : Shop-F",

    "Talewok : Dryad",
    "Talewok : Professor 1",
    "Talewok : Professor 2",
    "Talewok : Professor 3",
    "Talewok : Shop-A Female",
    "Talewok : Shop-A Male",
    "Talewok : Shop-B",
    "Talewok : Shop-C",
    "Talewok : Shop-D",
    "Talewok : Shop-E",
    "Talewok : Shop-F",

    "Terminor : Mago's House",
    "Terminor : Shop-A",
    "Terminor : Shop-B",
    "Terminor : Shop-C",
    "Terminor : Shop-D",
    "Terminor : Shop-E",
    "Terminor : Shop-F",
    "Terminor : Tamberlain",

    "Ugarit : Frysil",
    "Ugarit : Library",
    "Ugarit : Shop-A",
    "Ugarit : Shop-B",
    "Ugarit : Shop-C",
    "Ugarit : Shop-D",
    "Ugarit : Shop-E",
    "Ugarit : Shop-F",
    "Ugarit : Shop-G",
    "Ugarit : Shop-H",
]

SHOP_TRAINERS = [
    0x01FC7ED3,  # Erromon : Becan
    0x01FC5007,  # Erromon : Cavern Female
    0x01FC508F,  # Erromon : Cavern Male
    0x01FC2C6F,  # Erromon : Shop-A Male
    0x01FC2BE7,  # Erromon : Shop-B Female
    0x01FC3027,  # Erromon : Shop-B Female
    0x01FC2F9F,  # Erromon : Shop-B Male
    0x01FC2CF7,  # Erromon : Shop-C Female 1
    0x01FC2D7F,  # Erromon : Shop-C Female 2
    0x01FC2E07,  # Erromon : Shop-C Female 3
    0x01FC2E8F,  # Erromon : Shop-C Female 4
    0x01FC2F17,  # Erromon : Shop-D Female
    0x01FC30AF,  # Erromon : Shop-D Male
    0x01FC3247,  # Erromon : Shop-E Female
    0x01FC31BF,  # Erromon : Shop-E Male

    0x01FC519F,  # Gwernia : Shop-A
    0x01FC5117,  # Gwernia : Shop-B

    0x01FC491F,  # Port Saiid : Shop-A Bandit
    0x01FC49A7,  # Port Saiid : Shop-A Female
    0x01FC4B3F,  # Port Saiid : Shop-B
    0x01FC4A2F,  # Port Saiid : Shop-C
    0x01FC4BC7,  # Port Saiid : Shop-D
    0x01FC4C4F,  # Port Saiid : Shop-E
    0x01FC4AB7,  # Port Saiid : Shop-F

    0x01FC5C43,  # Talewok : Dryad
    0x01FC4DE7,  # Talewok : Professor 1
    0x01FC4F7F,  # Talewok : Professor 2
    0x01FC4EF7,  # Talewok : Professor 3
    0x01FC4457,  # Talewok : Shop-A Female
    0x01FC44DF,  # Talewok : Shop-A Male
    0x01FC4787,  # Talewok : Shop-B
    0x01FC4677,  # Talewok : Shop-C
    0x01FC46FF,  # Talewok : Shop-D
    0x01FC4567,  # Talewok : Shop-E
    0x01FC45EF,  # Talewok : Shop-F

    0x01FC3D6F,  # Terminor : Mago's House
    0x01FC3C5F,  # Terminor : Shop-A
    0x01FC3E7F,  # Terminor : Shop-B
    0x01FC3F07,  # Terminor : Shop-C
    0x01FC3F8F,  # Terminor : Shop-D
    0x01FC3BD7,  # Terminor : Shop-E
    0x01FC4017,  # Terminor : Shop-F
    0x01FC7297,  # Terminor : Tamberlain

    0x01FC3AC7,  # Ugarit : Frysil
    0x01FC3467,  # Ugarit : Library
    0x01FC3797,  # Ugarit : Shop-A
    0x01FC35FF,  # Ugarit : Shop-B
    0x01FC3687,  # Ugarit : Shop-C
    0x01FC3A3F,  # Ugarit : Shop-D
    0x01FC34EF,  # Ugarit : Shop-E
    0x01FC33DF,  # Ugarit : Shop-F
    0x01FC381F,  # Ugarit : Shop-G
    0x01FC3B4F,  # Ugarit : Shop-H

    0x01FC3137,  # unused Erromon
    0x01FC480F,  # unused Port Saiid
    0x01FC4897,  # unused Port Saiid
    0x01FC4CD7,  # unused Port Saiid
    0x01FC4127,  # unused Talewok
    0x01FC41AF,  # unused Talewok
    0x01FC4237,  # unused Talewok
    0x01FC42BF,  # unused Talewok
    0x01FC4347,  # unused Talewok
    0x01FC43CF,  # unused Talewok
    0x01FC3CE7,  # unused Terminor
    0x01FC3DF7,  # unused Terminor
    0x01FC409F,  # unused Terminor
    0x01FC32CF,  # unused Ugarit
    0x01FC3357,  # unused Ugarit
    0x01FC3577,  # unused Ugarit
    0x01FC370F,  # unused Ugarit
    0x01FC38A7,  # unused Ugarit
    0x01FC392F,  # unused Ugarit
    0x01FC39B7,  # unused Ugarit
    0x01FC4D5F,  # unused/university Talewok
    0x01FC4E6F,  # unused/university Talewok
]

SHOP_SPELLS = [
    0x1FC7EFB,  # Erromon : Becan
    0x1FC502F,  # Erromon : Cavern Female
    0x1FC50B7,  # Erromon : Cavern Male
    0x1FC2C97,  # Erromon : Shop-A Male
    0x1FC2C0F,  # Erromon : Shop-B Female
    0x1FC304F,  # Erromon : Shop-B Female
    0x1FC2FC7,  # Erromon : Shop-B Male
    0x1FC2D1F,  # Erromon : Shop-C Female 1
    0x1FC2DA7,  # Erromon : Shop-C Female 2
    0x1FC2E2F,  # Erromon : Shop-C Female 3
    0x1FC2EB7,  # Erromon : Shop-C Female 4
    0x1FC2F3F,  # Erromon : Shop-D Female
    0x1FC30D7,  # Erromon : Shop-D Male
    0x1FC326F,  # Erromon : Shop-E Female
    0x1FC31E7,  # Erromon : Shop-E Male

    0x1FC51C7,  # Gwernia : Shop-A
    0x1FC513F,  # Gwernia : Shop-B

    0x1FC4947,  # Port Saiid : Shop-A Bandit
    0x1FC49CF,  # Port Saiid : Shop-A Female
    0x1FC4B67,  # Port Saiid : Shop-B
    0x1FC4A57,  # Port Saiid : Shop-C
    0x1FC4BEF,  # Port Saiid : Shop-D
    0x1FC4C77,  # Port Saiid : Shop-E
    0x1FC4ADF,  # Port Saiid : Shop-F

    0x1FC5C6B,  # Talewok : Dryad
    0x1FC4E0F,  # Talewok : Professor 1
    0x1FC4FA7,  # Talewok : Professor 2
    0x1FC4F1F,  # Talewok : Professor 3
    0x1FC447F,  # Talewok : Shop-A Female
    0x1FC4507,  # Talewok : Shop-A Male
    0x1FC47AF,  # Talewok : Shop-B
    0x1FC469F,  # Talewok : Shop-C
    0x1FC4727,  # Talewok : Shop-D
    0x1FC458F,  # Talewok : Shop-E
    0x1FC4617,  # Talewok : Shop-F

    0x1FC3D97,  # Terminor : Mago's House
    0x1FC3C87,  # Terminor : Shop-A
    0x1FC3EA7,  # Terminor : Shop-B
    0x1FC3F2F,  # Terminor : Shop-C
    0x1FC3FB7,  # Terminor : Shop-D
    0x1FC3BFF,  # Terminor : Shop-E
    0x1FC403F,  # Terminor : Shop-F
    0x1FC72BF,  # Terminor : Tamberlain

    0x1FC3AEF,  # Ugarit : Frysil
    0x1FC348F,  # Ugarit : Library
    0x1FC37BF,  # Ugarit : Shop-A
    0x1FC3627,  # Ugarit : Shop-B
    0x1FC36AF,  # Ugarit : Shop-C
    0x1FC3A67,  # Ugarit : Shop-D
    0x1FC3517,  # Ugarit : Shop-E
    0x1FC3407,  # Ugarit : Shop-F
    0x1FC3847,  # Ugarit : Shop-G
    0x1FC3B77,  # Ugarit : Shop-H

    0x1FC315F,  # unused Erromon
    0x1FC4837,  # unused Port Saiid
    0x1FC48BF,  # unused Port Saiid
    0x1FC4CFF,  # unused Port Saiid
    0x1FC414F,  # unused Talewok
    0x1FC41D7,  # unused Talewok
    0x1FC425F,  # unused Talewok
    0x1FC42E7,  # unused Talewok
    0x1FC436F,  # unused Talewok
    0x1FC43F7,  # unused Talewok
    0x1FC3D0F,  # unused Terminor
    0x1FC3E1F,  # unused Terminor
    0x1FC40C7,  # unused Terminor
    0x1FC32F7,  # unused Ugarit
    0x1FC337F,  # unused Ugarit
    0x1FC359F,  # unused Ugarit
    0x1FC3737,  # unused Ugarit
    0x1FC38CF,  # unused Ugarit
    0x1FC3957,  # unused Ugarit
    0x1FC39DF,  # unused Ugarit
    0x1FC4D87,  # unused/university Talewok
    0x1FC4E97,  # unused/university Talewok
]

SHOP_SHIELDS = [
    0x1FC7F19,  # Erromon : Becan
    0x1FC504D,  # Erromon : Cavern Female
    0x1FC50D5,  # Erromon : Cavern Male
    0x1FC2CB5,  # Erromon : Shop-A Male
    0x1FC2C2D,  # Erromon : Shop-B Female
    0x1FC306D,  # Erromon : Shop-B Female
    0x1FC2FE5,  # Erromon : Shop-B Male
    0x1FC2D3D,  # Erromon : Shop-C Female 1
    0x1FC2DC5,  # Erromon : Shop-C Female 2
    0x1FC2E4D,  # Erromon : Shop-C Female 3
    0x1FC2ED5,  # Erromon : Shop-C Female 4
    0x1FC2F5D,  # Erromon : Shop-D Female
    0x1FC30F5,  # Erromon : Shop-D Male
    0x1FC328D,  # Erromon : Shop-E Female
    0x1FC3205,  # Erromon : Shop-E Male

    0x1FC51E5,  # Gwernia : Shop-A
    0x1FC515D,  # Gwernia : Shop-B

    0x1FC4965,  # Port Saiid : Shop-A Bandit
    0x1FC49ED,  # Port Saiid : Shop-A Female
    0x1FC4B85,  # Port Saiid : Shop-B
    0x1FC4A75,  # Port Saiid : Shop-C
    0x1FC4C0D,  # Port Saiid : Shop-D
    0x1FC4C95,  # Port Saiid : Shop-E
    0x1FC4AFD,  # Port Saiid : Shop-F

    0x1FC5C89,  # Talewok : Dryad
    0x1FC4E2D,  # Talewok : Professor 1
    0x1FC4FC5,  # Talewok : Professor 2
    0x1FC4F3D,  # Talewok : Professor 3
    0x1FC449D,  # Talewok : Shop-A Female
    0x1FC4525,  # Talewok : Shop-A Male
    0x1FC47CD,  # Talewok : Shop-B
    0x1FC46BD,  # Talewok : Shop-C
    0x1FC4745,  # Talewok : Shop-D
    0x1FC45AD,  # Talewok : Shop-E
    0x1FC4635,  # Talewok : Shop-F

    0x1FC3DB5,  # Terminor : Mago's House
    0x1FC3CA5,  # Terminor : Shop-A
    0x1FC3EC5,  # Terminor : Shop-B
    0x1FC3F4D,  # Terminor : Shop-C
    0x1FC3FD5,  # Terminor : Shop-D
    0x1FC3C1D,  # Terminor : Shop-E
    0x1FC405D,  # Terminor : Shop-F
    0x1FC72DD,  # Terminor : Tamberlain

    0x1FC3B0D,  # Ugarit : Frysil
    0x1FC34AD,  # Ugarit : Library
    0x1FC37DD,  # Ugarit : Shop-A
    0x1FC3645,  # Ugarit : Shop-B
    0x1FC36CD,  # Ugarit : Shop-C
    0x1FC3A85,  # Ugarit : Shop-D
    0x1FC3535,  # Ugarit : Shop-E
    0x1FC3425,  # Ugarit : Shop-F
    0x1FC3865,  # Ugarit : Shop-G
    0x1FC3B95,  # Ugarit : Shop-H

    0x1FC317D,  # unused Erromon
    0x1FC4855,  # unused Port Saiid
    0x1FC48DD,  # unused Port Saiid
    0x1FC4D1D,  # unused Port Saiid
    0x1FC416D,  # unused Talewok
    0x1FC41F5,  # unused Talewok
    0x1FC427D,  # unused Talewok
    0x1FC4305,  # unused Talewok
    0x1FC438D,  # unused Talewok
    0x1FC4415,  # unused Talewok
    0x1FC3D2D,  # unused Terminor
    0x1FC3E3D,  # unused Terminor
    0x1FC40E5,  # unused Terminor
    0x1FC3315,  # unused Ugarit
    0x1FC339D,  # unused Ugarit
    0x1FC35BD,  # unused Ugarit
    0x1FC3755,  # unused Ugarit
    0x1FC38ED,  # unused Ugarit
    0x1FC3975,  # unused Ugarit
    0x1FC39FD,  # unused Ugarit
    0x1FC4DA5,  # unused/university Talewok
    0x1FC4EB5,  # unused/university Talewok
]

SHOP_ITEMS = [
    0x1FD50EE,  # Erromon : Becan
    0x1FD3F36,  # Erromon : Cavern Female
    0x1FD3FA2,  # Erromon : Cavern Male
    0x1FD4446,  # Erromon : Shop-A Male
    0x1FD4152,  # Erromon : Shop-B Female
    0x1FD44B2,  # Erromon : Shop-B Female
    0x1FD41BE,  # Erromon : Shop-B Male
    0x1FD43DA,  # Erromon : Shop-C Female 1
    0x1FD436E,  # Erromon : Shop-C Female 2
    0x1FD4302,  # Erromon : Shop-C Female 3
    0x1FD4296,  # Erromon : Shop-C Female 4
    0x1FD422A,  # Erromon : Shop-D Female
    0x1FD40E6,  # Erromon : Shop-D Male
    0x1FD400E,  # Erromon : Shop-E Female
    0x1FD407A,  # Erromon : Shop-E Male

    0x1FD3E5E,  # Gwernia : Shop-A
    0x1FD3DF2,  # Gwernia : Shop-B

    0x1FD328E,  # Port Saiid : Shop-A Bandit
    0x1FD3AFE,  # Port Saiid : Shop-A Female
    0x1FD3C42,  # Port Saiid : Shop-B
    0x1FD3B6A,  # Port Saiid : Shop-C
    0x1FD3CAE,  # Port Saiid : Shop-D
    0x1FD3D1A,  # Port Saiid : Shop-E
    0x1FD3BD6,  # Port Saiid : Shop-F

    0x1FD3366,  # Talewok : Professor 1
    0x1FD343E,  # Talewok : Professor 2
    0x1FD33D2,  # Talewok : Professor 3
    0x1FD380A,  # Talewok : Shop-A Female
    0x1FD3876,  # Talewok : Shop-A Male
    0x1FD3A92,  # Talewok : Shop-B
    0x1FD39BA,  # Talewok : Shop-C
    0x1FD3A26,  # Talewok : Shop-D
    0x1FD38E2,  # Talewok : Shop-E
    0x1FD394E,  # Talewok : Shop-F

    0x1FD4F3E,  # Terminor : Mago's House
    0x1FD5016,  # Terminor : Shop-A
    0x1FD4E66,  # Terminor : Shop-B
    0x1FD4DFA,  # Terminor : Shop-C
    0x1FD4D8E,  # Terminor : Shop-D
    0x1FD5082,  # Terminor : Shop-E
    0x1FD4D22,  # Terminor : Shop-F
    0x1FD4C4A,  # Terminor : Tamberlain

    0x1FD458A,  # Ugarit : Frysil
    0x1FD4A9A,  # Ugarit : Library
    0x1FD4812,  # Ugarit : Shop-A
    0x1FD4956,  # Ugarit : Shop-B
    0x1FD48EA,  # Ugarit : Shop-C
    0x1FD45F6,  # Ugarit : Shop-D
    0x1FD4A2E,  # Ugarit : Shop-E
    0x1FD4B06,  # Ugarit : Shop-F
    0x1FD47A6,  # Ugarit : Shop-G
    0x1FD451E,  # Ugarit : Shop-H

    0x1FD3D86,  # unused Port Saiid
    0x1FD365A,  # unused Talewok
    0x1FD36C6,  # unused Talewok
    0x1FD3732,  # unused Talewok
    0x1FD379E,  # unused Talewok
    0x1FD4CB6,  # unused Terminor
    0x1FD4ED2,  # unused Terminor
    0x1FD4FAA,  # unused Terminor
    0x1FD4662,  # unused Ugarit
    0x1FD46CE,  # unused Ugarit
    0x1FD473A,  # unused Ugarit
    0x1FD487E,  # unused Ugarit
    0x1FD49C2,  # unused Ugarit
    0x1FD4B72,  # unused Ugarit
    0x1FD4BDE,  # unused Ugarit
    0x1FD34AA,  # unused/university Talewok
    0x1FD32FA,  # Ardra
    0x1FD3ECA,  # Bowden
    0x1FD3516,  # Cadme
    0x1FD35EE,  # Dust Devil
    0x1FD3222,  # Gabrion
    0x1FD3582,  # Xibid
]

DROP_CAT = {
    0x01FD23E4: "3F",
    0x01FD241C: "3E",
    0x01FD248C: "3C",
    0x01FD24C4: "3B",
    0x01FD24FC: "3A",
    0x01FD2534: "39",
    0x01FD256C: "38",
    0x01FD25A4: "37",
    0x01FD25DC: "36",
    0x01FD2614: "35",
    0x01FD264C: "34",
    0x01FD2684: "33",
    0x01FD26BC: "32",
    0x01FD26F4: "31",
    0x01FD272C: "30",
    0x01FD2764: "2F",
    0x01FD279C: "2E",
    0x01FD27D4: "2D",
    0x01FD280C: "2C",
    0x01FD2844: "2B",
    0x01FD287C: "2A",
    0x01FD28B4: "29",
    0x01FD28EC: "28",
    0x01FD2924: "27",
    0x01FD295C: "26",
    0x01FD2994: "25",
    0x01FD29CC: "24",
    0x01FD2A04: "23",
    0x01FD2A3C: "22",
    0x01FD2A74: "21",
    0x01FD2AAC: "20",
    0x01FD2AE4: "1F",
    0x01FD2B1C: "1E",
    0x01FD2B54: "1D",
    0x01FD2B8C: "1C",
    0x01FD2BC4: "1B",
    0x01FD2BFC: "1A",
    0x01FD2C34: "19",
    0x01FD2C6C: "18",
    0x01FD2CA4: "17",
    0x01FD2CDC: "16",
    0x01FD2D14: "15",
    0x01FD2D4C: "14",
    0x01FD2D84: "13",
    0x01FD2DBC: "12",
    0x01FD2DF4: "11",
    0x01FD2E2C: "10",
    0x01FD2E64: "0F",
    0x01FD2E9C: "0E",
    0x01FD2ED4: "0D",
    0x01FD2F0C: "0C",
    0x01FD2F44: "0B",
    0x01FD2F7C: "0A",
    0x01FD2FB4: "09",
    0x01FD2FEC: "08",
    0x01FD3024: "07",
    0x01FD305C: "06",
    0x01FD3094: "05",
    0x01FD30CC: "04",
    0x01FD3104: "03",
    0x01FD313C: "02",
    0x01FD3174: "01"
}

ITEM_DIC = {
    0x01FCD5D4: "170D",  # Acid (wand)
    0x01FCE608: "3311",  # Acid Bolt (scroll)
    0x01:       "0310",  # Acid Flask
    0x01FCA5A0: "0707",  # Air Fist
    0x01FCDBB8: "1111",  # Air Shield (scroll)
    0x01FCCE04: "0101",  # Amaranth
    0x01FCEB0C: "0713",  # Amulet of Pork
    0x02:       "0710",  # Antidote Potion
    0x01FCADBC: "3507",  # Archmage's Staff
    0x01FCE5DC: "3411",  # Aura of Death (scroll)
    0x01FCE584: "3611",  # Banishing (scroll)
    0x01FCD57C: "190D",  # Banishing (wand)
    0x01FCD918: "000D",  # Banner of Gwernia
    0x01FCD2E0: "020B",  # Bardic Gloves
    0x01FCA904: "0F07",  # Battle Axe
    0x01FCA3B8: "0007",  # Bear Bite
    0x01FCBA98: "1E05",  # Beast Hide (armor)
    0x01FCD06C: "2301",  # Beast Hide (material)
    0x01FCDA7C: "000E",  # Belt of Life
    0x01FCDA50: "010E",  # Belt of Teleport
    0x01FCE76C: "0112",  # Black Key
    0x01FCA934: "1007",  # Blood Axe
    0x01FCE714: "0312",  # Blood Key
    0x01FCB4C0: "3207",  # Boar Tusk
    0x01FCE6E8: "0412",  # Bone Key
    0x01FCDAD8: "010F",  # Boots of Adamant
    0x01FCDB30: "2A0F",  # Boots of Speed
    0x01FCDB88: "050F",  # Boots of Striding
    0x01FCAB48: "6007",  # Bow of Accuracy
    0x01FCAB78: "5F07",  # Bow of Shielding
    0x01FCABA8: "5E07",  # Bow of Thunder
    0x01FCE798: "0012",  # Bowdens Key
    0x01FCAD2C: "6407",  # Breklor's Firestaff
    0x01FCE558: "3711",  # Brilliance (scroll)
    0x01FCB158: "2507",  # Broadsword
    0x01FCC0FC: "1706",  # Bronze Shield
    0x01FCBFDC: "1106",  # Buckler
    0x01FCA3E8: "0107",  # Buzzard Bite
    0x01FCBB88: "0305",  # Chainmail
    0x01FCBDF8: "1005",  # Chaos Armor
    0x01FCAAE4: "4007",  # Chaos Deathwing
    0x01FCA814: "3107",  # Chaos Flameblade
    0x01FCA844: "5407",  # Chaos Maul
    0x01FCB528: "3D05",  # Chaos Robes
    0x01FCAAB4: "5307",  # Chaos Scythe
    0x01FCC1BC: "1B06",  # Chaos Shield
    0x01FCACFC: "4F07",  # Chaos Staff
    0x01FCB1B8: "2707",  # Chaos Sword
    0x01FCAEB4: "2E07",  # Chaos Tail
    0x03:       "0E10",  # Charisma Potion
    0x01FCE52C: "3811",  # Charming (scroll)
    0x01FCE500: "3911",  # Cheat Death (scroll)
    0x01FCD098: "2401",  # Chitin Plates
    0x04:       "0D10",  # Clarity Potion
    0x01FCBAF8: "0005",  # Cloth Armor
    0x01FCA964: "1107",  # Club
    0x01FCE26C: "4811",  # Clumsiness (scroll)
    0x01FCE4D4: "3A11",  # Command (scroll)
    0x01FCDBE4: "1011",  # Control Elem (scroll)
    0x01FCBE2C: "4306",  # Crab Shield
    0x01FCCA68: "1901",  # Cradawgh's Body
    0x01FCE450: "3D11",  # Crushing Death (scroll)
    0x01FCD6B0: "120D",  # Crushing Death (wand)
    0x01FCE4A8: "3B11",  # Ctrl Marquis (scroll)
    0x01FCE47C: "3C11",  # Ctrl Zombie (scroll)
    0x05:       "0610",  # Curing Potion
    0x01FCA754: "4E07",  # Cyclops Club
    0x01FCB39C: "4D07",  # Cyclops Hurlstar
    0x01FCB188: "2607",  # Dagger
    0x01FCBA38: "2005",  # Darkenbat Hide (armor)
    0x01FCD040: "2201",  # Darkenbat Hide (material)
    0x01FCE424: "3E11",  # Darkness (scroll)
    0x01FCD708: "100D",  # Darkness (wand)
    0x01FCB3CC: "6307",  # Dart of Distance
    0x01FCDC10: "0F11",  # Debilitation (scroll)
    0x06:       "0F10",  # Defense Potion
    0x01FCE3A0: "4111",  # Detect Chaos (scroll)
    0x01FCE374: "4211",  # Detect Traps (scroll)
    0x01FCE348: "4311",  # Dexterity (scroll)
    0x07:       "0A10",  # Dexterity Potion
    0x01FCE31C: "4411",  # Dispel Elem (scroll)
    0x01FCE2F0: "4511",  # Dispel Naming (scroll)
    0x01FCE2C4: "4611",  # Dispel Necro (scroll)
    0x01FCE298: "4711",  # Dispel Star (scroll)
    0x01FCA4AC: "0507",  # Dragon Breath
    0x01FCA5D0: "0807",  # Dragon Claws
    0x01FCB30C: "5A07",  # Dragon Fang
    0x01FCDC3C: "0E11",  # Dragon Flames (scroll)
    0x01FCBC78: "0805",  # Dragon Leather
    0x01FCE7C4: "0712",  # DragonKey
    0x01FCBE8C: "3C06",  # Dryad Shield
    0x01FCE3F8: "3F11",  # Dt Moon Phase (scroll)
    0x01FCE3CC: "4011",  # Dt Sun Phase (scroll)
    0x01FCA600: "0907",  # Earth Fist
    0x01FCDC68: "0D11",  # Earth Smite (scroll)
    0x01FCAD8C: "3907",  # Ehud's Staff
    0x01FCA8A4: "3707",  # Elisheva's Scythe
    0x01FCB038: "5607",  # Enchanted Blade
    0x01FCBC48: "0705",  # Enchanted Hide
    0x01FCBD98: "0E05",  # Enchanted Plate
    0x01FCDDC8: "0311",  # Endurance (scroll)
    0x01FCDC94: "0C11",  # Escape (scroll)
    0x01FCD49C: "0A0C",  # Etherial Ring
    0x01FCE0B4: "5211",  # Exhaustion (scroll)
    0x01FCBA08: "2405",  # exp 1 (armor)
    0x01FCB858: "2D05",  # exp 10 (armor)
    0x01FCB828: "2E05",  # exp 11 (armor)
    0x01FCB7F8: "2F05",  # exp 12 (armor)
    0x01FCB7C8: "3005",  # exp 13 (armor)
    0x01FCB798: "3105",  # exp 14 (armor)
    0x01FCB768: "3205",  # exp 15 (armor)
    0x01FCB738: "3305",  # exp 16 (armor)
    0x01FCB708: "3405",  # exp 17 (armor)
    0x01FCB6D8: "3505",  # exp 18 (armor)
    0x01FCB6A8: "3605",  # exp 19 (armor)
    0x01FCB9D8: "2505",  # exp 2 (armor)
    0x01FCB678: "3705",  # exp 20 (armor)
    0x01FCB648: "3805",  # exp 21 (armor)
    0x01FCB618: "3905",  # exp 22 (armor)
    0x01FCB9A8: "2605",  # exp 3 (armor)
    0x01FCB978: "2705",  # exp 4 (armor)
    0x01FCB948: "2805",  # exp 5 (armor)
    0x01FCB918: "2905",  # exp 6 (armor)
    0x01FCB8E8: "2A05",  # exp 7 (armor)
    0x01FCB8B8: "2B05",  # exp 8 (armor)
    0x01FCB888: "2C05",  # exp 9 (armor)
    0x01FCCF0C: "1501",  # exp2 (non-equipable)
    0x01FCB5E8: "3A05",  # exp23 (armor)
    0x01FCB5B8: "3B05",  # exp24 (armor)
    0x01FCCEE0: "1601",  # exp3 (non-equipable)
    0x01FCCEB4: "1701",  # exp4 (non-equipable)
    0x01FCCE88: "1801",  # exp5 (non-equipable)
    0x01FCA268: "4707",  # expansion 10 (weapon)
    0x01FCA238: "4807",  # expansion 11 (weapon)
    0x01FCA208: "4907",  # expansion 12 (weapon)
    0x01FCA1D8: "4A07",  # expansion 13 (weapon)
    0x01FCA1A8: "4B07",  # expansion 14 (weapon)
    0x01FCA178: "4C07",  # expansion 15 (weapon)
    0x01FCA388: "4107",  # expansion 4 (weapon)
    0x01FCA358: "4207",  # expansion 5 (weapon)
    0x01FCA328: "4307",  # expansion 6 (weapon)
    0x01FCA2F8: "4407",  # expansion 7 (weapon)
    0x01FCA2C8: "4507",  # expansion 8 (weapon)
    0x01FCA298: "4607",  # expansion 9 (weapon)
    0x08:       "0010",  # Fire Flask
    0x01FCA630: "0A07",  # Fire Touch
    0x01FCE634: "3211",  # Fireball (scroll)
    0x01FCD7E4: "0A0D",  # Fireball (wand)
    0x01FCB068: "5707",  # Firedrake Fang
    0x01FCE240: "4911",  # Frozen Doom (scroll)
    0x01FCD6DC: "110D",  # Frozen Doom (wand)
    0x01FCBBE8: "0505",  # Full Platemail
    0x01FCA4DC: "0607",  # Gaze
    0x01FCD4F8: "1C0D",  # Gem of Aspect
    0x01FCD524: "1B0D",  # Gem of Sensing
    0x01FCCFE8: "1301",  # Gemstone
    0x01FCA8D4: "3607",  # Giant Axe
    0x01FCB248: "2A07",  # Gladius
    0x01FCD338: "000B",  # Gloves of Healing
    0x01FCD7B8: "0C0D",  # Gravity (wand)
    0x01FCA9C4: "1307",  # Great Axe
    0x01FCAC08: "1807",  # Great Bow
    0x01FCB1E8: "2807",  # Great Sword
    0x01FCD9F4: "040D",  # Harp of Igone
    0x01FCE214: "4A11",  # Haste (scroll)
    0x01FCEB90: "0413",  # Haste Amulet
    0x01FCB45C: "2F07",  # Hatchet
    0x09:       "0410",  # Healing Potion
    0x01FCEC14: "0113",  # Heart of Elisheva
    0x01FCABD8: "5507",  # Heartseeker Bow
    0x01FCC0CC: "1606",  # Heater Shield
    0x01FCBA68: "1F05",  # Hellhound Hide (armor)
    0x01FCD014: "2101",  # Hellhound Hide (material)
    0x01FCD0C8: "0409",  # Helm of Charisma
    0x01FCD120: "0209",  # Helm of Defense
    0x01FCD14C: "0109",  # Helm of Tempests
    0x01FCD0F4: "0309",  # Helm of Wisdom
    0x01FCCFBC: "1201",  # Herb
    0x01FCA724: "6807",  # Hockey Stick
    0x01FCC18C: "1A06",  # Hoplite Shield
    0x01FCD9C8: "030D",  # Horn of Kynon
    0x01FCAC38: "1907",  # Hunter's Bow
    0x01FCB098: "3C07",  # Ice Stiletto
    0x01FCBD38: "0C05",  # Iden Scale
    0x01FCDCC0: "0A11",  # Immolation (scroll)
    0x01FCD5A8: "180D",  # Immolation (wand)
    0x01FCBC18: "0605",  # Improved Plate
    0x010:      "0110",  # Inferno Flask
    0x01FCB588: "4105",  # Irondrake Plate
    0x01FCACCC: "6607",  # Ironwood Staff
    0x01FCB48C: "3007",  # Javelin
    0x01FCA7E4: "3F07",  # Jester's Mace
    0x01FCD390: "030B",  # Jundar Gauntlets
    0x01FCBCA8: "0905",  # Jundar Leather
    0x01FCC12C: "1806",  # Jundar Shield
    0x01FCD178: "0009",  # Kendall's Hat
    0x01FCEAB0: "1812",  # key1
    0x01FCE924: "0F12",  # key10
    0x01FCE8F8: "0E12",  # key11
    0x01FCE8CC: "0D12",  # key12
    0x01FCE8A0: "0C12",  # key13
    0x01FCE874: "0B12",  # key14
    0x01FCE848: "0A12",  # key15
    0x01FCE81C: "0912",  # key16
    0x01FCE7F0: "0812",  # key17
    0x01FCEA84: "1712",  # key2
    0x01FCEA58: "1612",  # key3
    0x01FCEA2C: "1512",  # key4
    0x01FCEA00: "1412",  # key5
    0x01FCE9D4: "1312",  # key6
    0x01FCE9A8: "1212",  # key7
    0x01FCE97C: "1112",  # key8
    0x01FCE950: "1012",  # key9
    0x01FCC06C: "1406",  # Kite Shield
    0x01FCE1E8: "4B11",  # Know Aspect (scroll)
    0x01FCC03C: "1306",  # Large Shield
    0x01FCBB28: "0105",  # Leather Armor
    0x01FCDB5C: "040F",  # Leather Boots
    0x01FCD22C: "000A",  # Leather Cloak
    0x01FCCDAC: "0301",  # Letter to Kitarak
    0x01FCCE30: "0001",  # Letter to Txomin
    0x01FCE1BC: "4C11",  # Light (scroll)
    0x01FCD734: "0F0D",  # Light (wand)
    0x01FCE6BC: "0512",  # Lighthouse Key
    0x01FCE660: "2E11",  # Lighthouse Scroll
    0x01FCDCEC: "0911",  # Lightning (scroll)
    0x01FCD600: "160D",  # Lightning (wand)
    0x01FCAF78: "6707",  # Lightreaver
    0x01FCA874: "3B07",  # Lizard King's Axe
    0x01FCE690: "0612",  # Lodin's Key
    0x01FCB128: "3407",  # Lodin's Sword
    0x01FCAC68: "1A07",  # Long Bow
    0x01FCB218: "2907",  # Longsword
    0x01FCD444: "080C",  # Lunar Ring
    0x01FCA9F4: "1407",  # Mace
    0x01FCA7B4: "6107",  # Mace of Glory
    0x01FCD3EC: "270C",  # Magedrake Ring
    0x01FCCD54: "0501",  # Map 1
    0x01FCCBF4: "0D01",  # Map 10
    0x01FCCBC8: "0F01",  # Map 11
    0x01FCCB9C: "1401",  # Map 12
    0x01FCCB70: "1A01",  # Map 13
    0x01FCCB44: "1B01",  # Map 14
    0x01FCCB18: "1C01",  # Map 15
    0x01FCCAEC: "1D01",  # Map 16
    0x01FCCAC0: "1F01",  # Map 17
    0x01FCCA94: "2001",  # Map 18
    0x01FCCD28: "0601",  # Map 2
    0x01FCCCFC: "0701",  # Map 4
    0x01FCCCD0: "0801",  # Map 5
    0x01FCCCA4: "0901",  # Map 6
    0x01FCCC78: "0A01",  # Map 7
    0x01FCCC4C: "0B01",  # Map 8
    0x01FCCC20: "0C01",  # Map 9
    0x01FCCE5C: "1E01",  # Map to Goblin Lair
    0x01FCA510: "5107",  # Marquis Touch
    0x01FCEAE0: "0913",  # Marquis' Amulet
    0x01FCAA24: "1507",  # Maul
    0x01FCDAA8: "070E",  # Mercenary Belt
    0x01FCB4F0: "3307",  # Minotaur Butt
    0x01FCD284: "020A",  # Mirari Cloak
    0x01FCE190: "4D11",  # Mirror (scroll)
    0x01FCEB38: "0613",  # Mirror Amulet
    0x01FCD944: "010D",  # Moon Gem
    0x01FCBF4C: "2206",  # Moon Shield
    0x01FCAA54: "1607",  # Morningstar
    0x01FCD418: "310C",  # Namers Ring
    0x01FCD200: "280A",  # Nightdrake Mantle
    0x01FCE138: "4F11",  # Opening (scroll)
    0x01FCCDD8: "0201",  # Oriana's Letter
    0x01FCDE20: "0111",  # Oriana's Scroll
    0x01FCEBE8: "0013",  # Pandara's Amulet
    0x01FCBBB8: "0405",  # Partial Platemail
    0x01FCD78C: "0D0D",  # Persuasion (wand)
    0x01FCD258: "010A",  # Phantom Cloak
    0x01FCE10C: "5011",  # Photosynth (scroll)
    0x01FCADEC: "1E07",  # Pike
    0x01FCA540: "5C07",  # Plague Claw
    0x01FCD2B4: "040B",  # Plate Gauntlets
    0x01FCB3FC: "5D07",  # Poison Dart
    0x01FCAB14: "1F07",  # Poleaxe
    0x01FCBD68: "0D05",  # Pome Scale
    0x01FCAEE4: "5807",  # Pseudodragon Sting
    0x01FCA47C: "0407",  # Pseudopod
    0x01FCCD80: "0401",  # Rabisat's Asp
    0x01FCA418: "0207",  # Rat Bite
    0x01FCDA24: "020E",  # Reflection Belt
    0x01FCDD18: "0811",  # Remove Poison (scroll)
    0x011:      "0810",  # Restore Potion
    0x01FCD550: "1A0D",  # Revival (wand)
    0x01FCD3C0: "1F0C",  # Ring of Healing
    0x01FCD4CC: "1D0D",  # Rope
    0x01FCBDC8: "0F05",  # Royal Platemail
    0x01FCB278: "2B07",  # Sabre
    0x01FCCF38: "0E01",  # Sapphire Gem
    0x01FCBB58: "0205",  # Scale Armor
    0x01FCBAC8: "1C05",  # Scorpion scale
    0x01FCBFAC: "1D06",  # Scorpion Shield
    0x01FCAF14: "2307",  # Scorpion Sting
    0x01FCA994: "1207",  # Scythe
    0x01FCDE4C: "0011",  # Sense Aura (scroll)
    0x01FCEC40: "0213",  # Shamsuk Amulet
    0x01FCB558: "3F05",  # Sheridans Armor
    0x01FCBEBC: "3E06",  # Sheridans Shield
    0x01FCB008: "5207",  # Sheridans Sword
    0x01FCEB64: "0513",  # Shield Amulet
    0x01FCE0E0: "5111",  # Shield of Starlight (scroll)
    0x01FCD760: "0E0D",  # Shielding (wand)
    0x01FCAC98: "1C07",  # Short Bow
    0x01FCB2A8: "2C07",  # Short Sword
    0x01FCE740: "0212",  # Skull Key
    0x012:      "0210",  # Sleep Gas Flask
    0x01FCC00C: "1206",  # Small Shield
    0x01FCE5B0: "3511",  # Solar Wrath (scroll)
    0x01FCAE1C: "2007",  # Spear
    0x01FCA784: "6207",  # Spellbreaker Axe
    0x01FCCF90: "1101",  # Spice
    0x01FCB42C: "1B07",  # Spikes
    0x01FCA148: "5B07",  # Spirit Bite
    0x01FCC15C: "1906",  # Spirit Shield
    0x01FCE088: "5311",  # Spirit Shield (scroll)
    0x01FCD1A4: "2609",  # Spiritdrake Helm
    0x01FCEBBC: "0313",  # ST Gem
    0x01FCAE4C: "2107",  # Staff
    0x01FCAD5C: "3E07",  # Staff of Lugash
    0x01FCE05C: "5411",  # Stamina (scroll)
    0x013:      "0510",  # Stamina Potion
    0x01FCBEEC: "4006",  # Stardrake Aegis
    0x01FCD658: "140D",  # Starfire (wand)
    0x01FCE030: "5511",  # Stealth (scroll)
    0x014:      "1010",  # Stealth Potion
    0x01FCAFD8: "5007",  # Stealthblade
    0x01FCE004: "5611",  # Stellar Grav (scroll)
    0x01FCD970: "020D",  # Stormbreaker
    0x01FCD364: "290B",  # Stormdrake Claws
    0x01FCDD44: "0711",  # Strength (scroll)
    0x015:      "0910",  # Strength Potion
    0x01FCE164: "4E11",  # Stupidity (scroll)
    0x01FCCF64: "1001",  # Sulphur
    0x01FCBF7C: "2106",  # Sun Shield
    0x01FCAFA8: "5907",  # Sword of Might
    0x01FCBCD8: "0A05",  # Talewok Mail
    0x01FCB2D8: "2D07",  # Tanto
    0x01FCDFD8: "5711",  # Tap Stamina (scroll)
    0x01FCD810: "090D",  # Tap Stamina (wand)
    0x01FCDFAC: "5811",  # Teleport (scroll - Teleport)
    0x01FCDD70: "0511",  # Teleport (scroll - Wraith Touch)
    0x01FCA660: "0B07",  # Tentacle Slap
    0x01FCBD08: "0B05",  # Terminor Mail
    0x01FCB33C: "1D07",  # Throwing Iron
    0x01FCB36C: "6507",  # Throwing Knife
    0x01FCD30C: "010B",  # Tinker's Gloves
    0x01FCC09C: "1506",  # Tower Shield
    0x01FCB0C8: "3A07",  # Trahern's Sword
    0x01FCA690: "0C07",  # Troll Claw
    0x01FCBF1C: "2306",  # Turtleshell Shield
    0x01FCA570: "3D07",  # Unarmed
    0x01FCAE80: "2207",  # Venom Spit
    0x01FCDF80: "5911",  # vs Elemental (scroll)
    0x01FCD83C: "080D",  # vs Elemental (wand)
    0x01FCDF54: "5A11",  # vs Naming (scroll)
    0x01FCD868: "070D",  # vs Naming (wand)
    0x01FCDF28: "5B11",  # vs Necromancy (scroll)
    0x01FCD894: "060D",  # vs Necromancy (wand)
    0x01FCDEFC: "5C11",  # vs Star (scroll)
    0x01FCD8C0: "050D",  # vs Star (wand)
    0x01FCDED0: "5D11",  # Wall of Bones (scroll)
    0x01FCD8EC: "7C0D",  # Wall of Bones (wand)
    0x01FCAA84: "1707",  # War Hammer
    0x01FCB0F8: "3807",  # Warfang
    0x01FCDD9C: "0411",  # Weakness (scroll)
    0x01FCDEA4: "5E11",  # Web of Starlight (scroll)
    0x01FCD684: "130D",  # Web of Starlight (wand)
    0x01FCDE78: "5F11",  # Whitefire (scroll)
    0x01FCBE5C: "4206",  # Wight Shield
    0x01FCDDF4: "0211",  # Wind (scroll)
    0x01FCD470: "090C",  # Witch Ring
    0x01FCD1D0: "0609",  # Wizard Hat
    0x01FCD99C: "0B0D",  # Wizard's Wand
    0x01FCA448: "0307",  # Wolf Bite
    0x01FCDB04: "000F",  # Woodsman's Boots
    0x01FCA6C0: "0D07",  # Wraith Touch
    0x01FCD62C: "150D",  # Wraith Touch (wand)
    0x01FCAF44: "2407",  # Wyvern Sting
    0x01FCA6F0: "0E07",  # Zombie Fist
}

inv_ITEM_DIC = {v: k for k, v in ITEM_DIC.items()}

SPELL_DIC = {
    0x01FCC564: "3B03",  # Acid Bolt
    0x01FCC268: "0003",  # Air Shield
    0x01FCC588: "3403",  # Aura of Death
    0x01FCC41C: "0A03",  # Banishing
    0x01FCC3D4: "3703",  # Brilliance
    0x01FCC440: "0C03",  # Charming
    0x01FCC540: "3F03",  # Cheat Death
    0x01FCC95C: "2A03",  # Clumsiness
    0x01FCC28C: "0103",  # Control Elem
    0x01FCC464: "0D03",  # Control Marquis
    0x01FCC5D0: "1403",  # Control Zombies
    0x01FCC5F4: "1503",  # Crushing Death
    0x01FCC618: "1603",  # Darkness
    0x01FCC2B0: "0203",  # Debilitation
    0x01FCC8F0: "2703",  # Detect Moon Phase
    0x01FCC914: "2803",  # Detect Sun Phase
    0x01FCC488: "0F03",  # Detecting Traps
    0x01FCC938: "2903",  # Dexterity
    0x01FCC7F0: "2103",  # Dispel Elemental
    0x01FCC814: "2203",  # Dispel Naming
    0x01FCC838: "2303",  # Dispel Necro
    0x01FCC85C: "2403",  # Dispel Star
    0x01FCC2D4: "0303",  # Dragon Flames
    0x01FCC2F8: "0403",  # Earth Smite
    0x01FCC4AC: "1003",  # Endurance
    0x01FCC220: "3C03",  # Escape
    0x01FCC660: "1803",  # Exhaustion
    0x01FCC31C: "0503",  # Fireball
    0x01FCC980: "2B03",  # Frozen Doom
    0x01FCC63C: "1703",  # Haste
    0x01FCC1FC: "3D03",  # Immolation
    0x01FCC9A4: "2D03",  # Light
    0x01FCC340: "0603",  # Lightning
    0x01FCC73C: "3E03",  # Mirror
    0x01FCC4D0: "1103",  # Opening
    0x01FCC884: "3903",  # Photosynthesis
    0x01FCC718: "3203",  # Poison
    0x01FCC244: "3803",  # Remove Poison
    0x01FCC4F4: "1203",  # Sense Aura
    0x01FCC8A8: "3503",  # Solar Wrath
    0x01FCC6F0: "1C03",  # Spirit Shield
    0x01FCC684: "1903",  # Stamina
    0x01FCC8CC: "2603",  # Starlight Shield
    0x01FCC9C8: "2E03",  # Stealth
    0x01FCC9EC: "2F03",  # Stellar Gravity
    0x01FCC364: "0803",  # Strength
    0x01FCC3F8: "3603",  # Stupidity
    0x01FCC6A8: "1A03",  # Tap Stamina
    0x01FCC3B0: "3A03",  # Teleportation
    0x01FCC760: "1D03",  # vs. Elemental
    0x01FCC784: "1E03",  # vs. Naming
    0x01FCC7A8: "1F03",  # vs. Necromancy
    0x01FCC7CC: "2003",  # vs. Star
    0x01FCC6CC: "1B03",  # Wall Of Bones
    0x01FCC518: "1303",  # Weakness
    0x01FCCA10: "3003",  # Web Of Starlight
    0x01FCCA34: "3103",  # Whitefire
    0x01FCC388: "0903",  # Wind
    0x01FCC5AC: "3303"   # Wraith Touch
}

POTIONS = {
    "(potion) Acid Flask": "1003",
    "(potion) Antidote Potion": "1007",
    "(potion) Charisma Potion": "100E",
    "(potion) Clarity Potion": "100D",
    "(potion) Curing Potion": "1006",
    "(potion) Defense Potion": "100F",
    "(potion) Dexterity Potion": "100A",
    "(potion) Fire Flask": "1000",
    "(potion) Healing Potion": "1004",
    "(potion) Inferno Flask": "1001",
    "(potion) Restore Potion": "1008",
    "(potion) Sleep Gas Flask": "1002",
    "(potion) Stamina Potion": "1005",
    "(potion) Stealth Potion": "1010",
    "(potion) Strength Potion": "1009",
}

INV_POTIONS = {v: k for k, v in POTIONS.items()}

SCHOOL = {
    'NONE': '04',
    'Chaos': '00',
    'Elemental': '01',
    'Naming': '02',
    'Necromancy': '03',
    'Star': '05'
}

inv_SCHOOL = {v: k for k, v in SCHOOL.items()}
if __name__ == "__main__":
    main()


"""
ROM reference constants for Aidyn Chronicles (N64)

Centralizes ROM offsets, address lists, and lookup dictionaries used by the editor
Ordering mirrors ROM layout where helpful for hex editor cross-checks
inv_* mappings should be true inverses of their forward dicts
"""