from functools import partial
from tkinter import Toplevel, Frame, LabelFrame, Entry, Radiobutton, Label, Button, StringVar, IntVar
from tkinter.ttk import Combobox

from lib.limits import limit_name_size, limit
from lib.fuctions import get_major_name_lists, int_cast
from lib.variables import SPELL_ADDRESSES, inv_TARGET_NUM, inv_TARGET_TYPE, inv_SPELL_INGREDIENTS, \
    TARGET_NUM, TARGET_TYPE, SPELL_INGREDIENTS, SCHOOL, inv_SCHOOL


class SpellEdit():
    def __init__(self, filename, icon):
        win = Toplevel()
        win.resizable(False, False)
        win.title("Spell Edit")
        win.iconbitmap(icon)
        filename = filename
        data_seek = 25
        data_read = 11
        name_length = 22

        self.spell_list, self.spell_addresses = get_major_name_lists(filename, SPELL_ADDRESSES, name_length)
        self.default_spell_menu = Combobox()

        def set_defaults(*args):
            with open(filename, 'rb') as f:
                address = self.spell_addresses[self.default_spell_menu.current()]

                # get name that can be changed
                f.seek(address)
                name.set(f.read(name_length).decode("utf-8"))

                # get everything else
                f.seek(address + data_seek)
                d = f.read(data_read).hex()

                school.set(inv_SCHOOL[(d[0] + d[1]).upper()])
                damage.set(int(d[2] + d[3], 16))
                stamina.set(int(d[4] + d[5], 16))
                target_num.set(inv_TARGET_NUM[d[7]])
                target_type.set(inv_TARGET_TYPE[d[9]])
                # target_area.set(int(sd[10] + sd[11], 16))
                wizard.set(int(d[12] + d[13], 16))
                asp = d[15]
                if asp == range(0, 2):
                    asp = 0
                aspect.set(asp)
                spell_range.set(int(d[16] + d[17], 16))
                ingredient.set(inv_SPELL_INGREDIENTS[d[19]])
                exp.set(int(d[20] + d[21], 16))

        def write():
            with open(filename, 'rb+') as f:
                address = self.spell_addresses[self.default_spell_menu.current()]

                new_name = bytearray(name.get(), 'utf-8')
                if len(new_name) < name_length:
                    while len(new_name) < name_length:
                        new_name.append(0x00)
                f.seek(address)
                f.write(new_name)

                f.seek(address + data_seek)
                d = f.read(data_read).hex()

                towrite = [
                    SCHOOL[school.get()],
                    damage.get(),
                    stamina.get(),
                    TARGET_NUM[target_num.get()],
                    TARGET_TYPE[target_type.get()],
                    (d[10] + d[11]),
                    wizard.get(),
                    aspect.get(),
                    spell_range.get(),
                    SPELL_INGREDIENTS[ingredient.get()],
                    exp.get()
                ]

                f.seek(address + data_seek)
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))

                reset_list()
                self.spell.set(self.spell_list[self.spell_list.index(name.get().rstrip('\x00'))])
            set_defaults()

        def build():
            box = Frame(win)
            box.grid(column=0, row=0, pady=5, padx=5)

            self.default_spell_menu = Combobox(box, textvariable=self.spell, width=22,
                                               values=self.spell_list,
                                               postcommand=reset_list, state='readonly')
            self.default_spell_menu.grid(column=0, row=0)

            new_name_label = LabelFrame(box, text='New Name')
            new_name_label.grid(column=0, row=1)
            new_name_entry = Entry(new_name_label, textvariable=name, width=22)
            new_name_entry.grid()

            stats_frame = LabelFrame(box, text='Stats')
            stats_frame.grid(column=0, row=2, rowspan=4)
            damage_label = Label(stats_frame, text='Damage:')
            damage_label.grid(column=0, row=0, sticky='e')
            damage_entry = Entry(stats_frame, textvariable=damage, width=4)
            damage_entry.grid(column=1, row=0, sticky='w')

            stamina_label = Label(stats_frame, text='Stamina Cost:')
            stamina_label.grid(column=0, row=1, sticky='e')
            stamina_entry = Entry(stats_frame, textvariable=stamina, width=4)
            stamina_entry.grid(column=1, row=1, sticky='w')

            wizard_label = Label(stats_frame, text='Wizard Required:')
            wizard_label.grid(column=0, row=2, sticky='e')
            wizard_entry = Entry(stats_frame, textvariable=wizard, width=4)
            wizard_entry.grid(column=1, row=2, sticky='w')

            range_label = Label(stats_frame, text='Range:')
            range_label.grid(column=0, row=3, sticky='e')
            range_entry = Entry(stats_frame, textvariable=spell_range, width=4)
            range_entry.grid(column=1, row=3, sticky='w')

            exp_label = Label(stats_frame, text='EXP to Rank:')
            exp_label.grid(column=0, row=4, sticky='e')
            exp_entry = Entry(stats_frame, textvariable=exp, width=4)
            exp_entry.grid(column=1, row=4, sticky='w')
            exp_label2 = Label(stats_frame, text='(Higher # = more EXP to rank)', font=(None, 8))
            exp_label2.grid(row=5, columnspan=3, rowspan=2, sticky='ew')

            save = Button(box, text='Save', command=write, width=8)
            save.grid(column=1, row=0)

            aspect_frame = LabelFrame(box, text='Aspect')
            aspect_frame.grid(column=1, row=1)
            aspect_none = Radiobutton(aspect_frame, text='NONE', variable=aspect, value=0)
            aspect_none.grid(column=0, row=0)
            aspect_solar = Radiobutton(aspect_frame, text='Solar', variable=aspect, value=4)
            aspect_solar.grid(column=1, row=0)
            aspect_lunar = Radiobutton(aspect_frame, text='Lunar', variable=aspect, value=3)
            aspect_lunar.grid(column=2, row=0)

            school_frame = LabelFrame(box, text='School')
            school_frame.grid(column=1, row=2)
            school_box = Combobox(school_frame, textvariable=school, width=12, state='readonly',
                                  values=(list(SCHOOL.keys())[0:1] + list(SCHOOL.keys())[2:]))
            school_box.grid()

            ingredient_frame = LabelFrame(box, text='Ingredient')
            ingredient_frame.grid(column=1, row=3)
            ingredient_menu = Combobox(ingredient_frame, textvariable=ingredient, width=12,
                                       values=list(SPELL_INGREDIENTS.keys()), state='readonly')
            ingredient_menu.grid(column=0, row=0)

            target_num_frame = LabelFrame(box, text='Number of targets:')
            target_num_frame.grid(column=1, row=4)
            target_num_menu = Combobox(target_num_frame, textvariable=target_num, width=23,
                                       values=list(TARGET_NUM.keys()), state='readonly')
            target_num_menu.grid()

            target_type_frame = LabelFrame(box, text='Who is targeted:')
            target_type_frame.grid(column=1, row=5)
            target_type_menu = Combobox(target_type_frame, textvariable=target_type, values=list(TARGET_TYPE.keys()),
                                        width=23, state='readonly')
            target_type_menu.grid()

        def reset_list():
            self.spell_list[:] = []
            self.spell_addresses[:] = []
            self.spell_list, self.spell_addresses = get_major_name_lists(filename, SPELL_ADDRESSES, name_length)
            self.default_spell_menu['values'] = self.spell_list

        self.spell = StringVar()
        self.spell.trace('w', set_defaults)
        name = StringVar()
        name.trace('w', partial(limit_name_size, name, name_length))

        damage = StringVar()
        damage.trace('w', partial(limit, damage, 255))
        stamina = StringVar()
        stamina.trace('w', partial(limit, stamina, 120))
        wizard = StringVar()
        wizard.trace('w', partial(limit, wizard, 10))
        spell_range = StringVar()
        spell_range.trace('w', partial(limit, spell_range, 255))
        exp = StringVar()
        exp.trace('w', partial(limit, exp, 255))
        school = StringVar()
        target_num = StringVar()
        target_type = StringVar()
        # target_area = IntVar()
        aspect = IntVar()
        ingredient = StringVar()

        build()
        self.spell.set(self.spell_list[0])

    """def build(self):
        super().build()
        self.resist_frame.destroy()"""