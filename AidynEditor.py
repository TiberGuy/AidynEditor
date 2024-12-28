#
# AidynEditor - an editor for Aidyn Chronicles
# @email fishbane0@gmail.com
#

import os
import shutil
import sys
from tkinter import Tk, LabelFrame, mainloop, Button, PhotoImage, Label, Checkbutton, BooleanVar
from tkinter import filedialog
from views import armors_and_shields, spells, wands_and_scrolls, weapons, trainers_and_shops, accessories, \
    enemies, party
from lib.variables import ARMOR_ADDRESSES, SHIELD_ADDRESSES, PARTY_ADDRESSES, ENEMY_ADDRESSES, WEAPON_ADDRESSES, \
    ACCESSORY_ADDRESSES


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


background = resource_path('images\\aidyn.gif')
icon = resource_path('images\\aidyn.ico')


def file_dialog():
    # function that searches for 'filename' and creates the links to the
    # different editing windows
    party_name_length = 9
    enemy_name_length = 17
    button_width = 10

    filename = filedialog.askopenfilename(initialdir='./',
                                          title='Select A File',
                                          filetype=(('z64', '*.z64'), ('all files', '*.*')))

    if filename != '':
        browse_frame.destroy()

        if backup.get():  # creates a backup of the ROM file before editing
            backup_file = filename.rstrip('.z64') + ' (backup).z64'
            shutil.copy2(filename, backup_file)

        root.configure(background='white')
        aidyn = Label(root, image=image)
        aidyn.grid(column=0, row=0, rowspan=9)

        party_button = Button(root, text='Party', width=button_width,
                              command=lambda: party.PartyEdit(filename,
                                                              icon,
                                                              PARTY_ADDRESSES,
                                                              party_name_length,
                                                              78, 0))
        party_button.grid(column=1, row=0, sticky='ew')

        enemy_button = Button(root, text='Enemy', width=button_width,
                              command=lambda: enemies.EnemyEdit(filename,
                                                                icon,
                                                                ENEMY_ADDRESSES,
                                                                enemy_name_length,
                                                                92, 1))
        enemy_button.grid(column=1, row=1)

        trainer_button = Button(root, text='Shop / Trainer', width=button_width,
                                command=lambda: trainers_and_shops.TrainerEdit(filename, icon))
        trainer_button.grid(column=1, row=2)

        accessory_button = Button(root, text='Accessory', width=button_width,
                                  command=lambda: accessories.AccessoryEdit(filename, icon,
                                                                            ACCESSORY_ADDRESSES,
                                                                            24, 20, 20))
        accessory_button.grid(column=1, row=3)

        armor_button = Button(root, text='Armor', width=button_width,
                              command=lambda: armors_and_shields.ArmorShield(filename, icon,
                                                                             ARMOR_ADDRESSES,
                                                                             26, 25, 22, 5))
        armor_button.grid(column=1, row=4)

        shield_button = Button(root, text='Shield', width=button_width,
                               command=lambda: armors_and_shields.ArmorShield(filename, icon,
                                                                              SHIELD_ADDRESSES,
                                                                              26, 25, 22, 6))
        shield_button.grid(column=1, row=5)

        spell_button = Button(root, text='Spell', width=button_width,
                              command=lambda: spells.SpellEdit(filename, icon))
        spell_button.grid(column=1, row=6)

        wandsscrolls_button = Button(root, text='Wand / Scroll', width=button_width,
                                     command=lambda: wands_and_scrolls.WandScrollEdit(filename, icon))
        wandsscrolls_button.grid(column=1, row=7)

        weapon_button = Button(root, text='Weapon', width=button_width,
                               command=lambda: weapons.WeaponEdit(filename, icon,
                                                                  WEAPON_ADDRESSES,
                                                                  23, 25, 21))
        weapon_button.grid(column=1, row=8)


root = Tk()
root.geometry('+300+150')
root.resizable(False, False)
root.title('Aidyn Editor')
root.iconbitmap(icon)
image = PhotoImage(file=background)
backup = BooleanVar()
backup.set(False)  # sets default mode to create a backup (False would be default no backup)

browse_frame = LabelFrame(root, text='Aidyn Chronicles ROM')
browse_frame.pack()
browse_button = Button(browse_frame, text='Browse', command=file_dialog)
browse_button.pack()
back_up = Checkbutton(browse_frame, text='Backup', var=backup)
back_up.pack()

mainloop()
