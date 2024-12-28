from functools import partial
from tkinter import Toplevel, StringVar, Button, LabelFrame, Label, Entry, Frame
from tkinter.ttk import Combobox

from lib.fuctions import get_major_item_dic, get_minor_dic, int_cast, limit
from lib.variables import SKILLS, SHOP_SKILLS, SHOPS, SHOP_SHIELD, SHOP_SPELLS, SHOP_ITEM_ADDRESSES, SPELL_DIC


class TrainerEdit:
    def __init__(self, f, i):
        self.win = Toplevel()
        self.win.resizable(False, False)
        self.filename = f
        self.icon = i
        self.win.title("Shops and Trainer Edit")
        self.win.iconbitmap(self.icon)
        self.skill_read = 23
        self.shield_read = 1
        self.spell_read = 16

        # following list are the trainers that do not provide shop features
        self.NOT_SHOPS = ["Talewok : Dryad", "Talewok : Professor 1", "Talewok : Professor 2", "Talewok : Professor 3"]

        self.shops = []
        with open(self.filename, 'rb') as f:
            # function for adding Becan to the list of shops
            # this provides his custom name to the editor (if he is given one)
            f.seek(0x01FC7EA4)
            self.becan = 'Erromon : ' + f.read(9).decode("utf-8").rstrip('\x00')
            self.shops = [self.becan] + SHOPS

        # dictionaries
        self.items = get_major_item_dic(self.filename)
        self.inv_items = {v: k for k, v in self.items.items()}
        self.spell_dic = get_minor_dic(self.filename, SPELL_DIC, 22)
        self.inv_spell_dic = {v: k for k, v in self.spell_dic.items()}

        # variables
        self.trainer = StringVar()
        self.trainer.trace('w', self.defaults)
        self.trainer.trace('w', self.skill_frame_text)

        self.skills = []
        for _ in SKILLS:
            i = StringVar()
            i.trace('w', partial(limit, i, 10))
            self.skills.append(i)
        self.shield_skill = StringVar()
        self.shield_skill.trace('w', partial(limit, self.shield_skill, 10))

        self.spells = []
        for i in range(5):
            i = StringVar()
            self.spells.append(i)

        self.spell_levels = []
        for i in range(5):
            i = StringVar()
            i.trace('w', partial(limit, i, 15))
            self.spell_levels.append(i)

        self.shop_item = []
        for i in range(23):
            i = StringVar()
            self.shop_item.append(i)

        # build self.items
        self.main_win = Frame(self.win)
        self.main_win.grid(column=0, row=0, pady=5, padx=(5, 0))
        self.shop_win = LabelFrame(self.win, text='Shop Items')
        self.shop_win.grid(column=1, row=0, pady=5, padx=(0, 5), sticky='n')

        self.default_name_menu = Combobox(self.main_win, textvariable=self.trainer, values=self.shops, width=26,
                                          state='readonly')
        self.save = Button(self.main_win, text="Save", command=self.write, width=8)
        self.spell_frame = LabelFrame(self.main_win, text='Spells and Spell Level')

        self.spell = []
        self.spell_level = []
        for i in range(5):
            self.spell.append(
                Combobox(self.spell_frame, textvariable=self.spells[i], values=list(self.inv_spell_dic.keys()),
                         state='readonly', width=16))
            self.spell_level.append(Entry(self.spell_frame, textvariable=self.spell_levels[i], width=4))

        self.skill_frame = LabelFrame(self.main_win, labelanchor='n')

        self.shield_label = Label(self.skill_frame, text='Shield', anchor='e', width=9)
        self.shield_num = Entry(self.skill_frame, textvariable=self.shield_skill, width=4)
        self.note_box = LabelFrame(self.main_win, text='Notes on self.skills')
        self.note1 = Label(self.note_box, anchor='w', width=30, font=(None, 8),
                           text='* ' + self.becan[10:] + ' edits affect the party version\nof his character\n'
                                                         '- So blank means he can\'t learn')
        self.note2 = Label(self.note_box, anchor='w', width=30, font=(None, 8),
                           text='* Blank and 0 mean those particular\nskills are not taught')

        self.item_box = []
        for i in range(23):
            self.item_box.append(Combobox(self.shop_win, width=28, state='readonly',
                                          textvariable=self.shop_item[i], values=list(self.inv_items.keys())))

        # run
        self.trainer.set(self.shops[0])
        self.build()

    def defaults(self, *args):
        with open(self.filename, 'rb') as f:
            # gets self.trainer self.skills + shield
            address = SHOP_SKILLS[self.shops.index(self.trainer.get())]
            f.seek(address)
            d = f.read(self.skill_read).hex()

            for s in self.skills:
                sn = int(d[self.skills.index(s) * 2] + d[(self.skills.index(s) * 2) + 1], 16)
                if sn == 255:
                    sn = ''
                s.set(sn)

            address = SHOP_SHIELD[self.shops.index(self.trainer.get())]
            f.seek(address)
            d = f.read(self.shield_read).hex()

            shi = int(d[0] + d[1], 16)
            if shi == 255:
                shi = ''
            self.shield_skill.set(shi)

            # self.trainer self.spells
            address = SHOP_SPELLS[self.shops.index(self.trainer.get())]
            f.seek(address)
            d = f.read(self.spell_read).hex()

            for s in self.spells:
                x = (self.spells.index(s) * 4)
                y = x + 4
                s.set(self.spell_dic[d[x:y].upper()])

            for s in self.spell_levels:
                x = (self.spell_levels.index(s) * 2) + 22
                s.set(int(d[x] + d[x + 1], 16))

            # determines whether the shop part of the widget should show up
            # 'NOT_SHOPS' is the list of trainers that do not have shop services
            if self.trainer.get() in self.NOT_SHOPS:
                self.shop_win.grid_forget()
                for item in self.shop_item:
                    item.set('')
            else:
                self.shop_win.grid(column=1, row=0, pady=5, padx=(0, 5), sticky='n')
                address = SHOP_ITEM_ADDRESSES[self.shops.index(self.trainer.get())]
                f.seek(address)

                for item in self.shop_item:
                    d = f.read(2).hex()
                    item.set(self.items[d[0:4].upper()])
                    if self.shop_item.index(item) < 20:
                        address += 5
                        f.seek(address)
                    else:
                        address += 2
                        f.seek(address)

    def write(self):
        with open(self.filename, 'rb+') as f:
            # write self.skills + shield
            address = SHOP_SKILLS[self.shops.index(self.trainer.get())]
            f.seek(address)

            towrite = []
            for i in self.skills:
                j = i.get()
                if j == '':
                    j = '255'
                towrite.append(j)

            f.seek(address)
            if self.trainer.get() == self.becan:
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))
            else:
                for item in towrite:
                    if item == '255':
                        item = '0'
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))

            towrite[:] = []

            address = SHOP_SHIELD[self.shops.index(self.trainer.get())]
            f.seek(address)

            shi = self.shield_skill.get()
            if shi == '':
                shi = 255
            towrite.append(shi)

            if self.trainer.get() == self.becan:
                for item in towrite:
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))
            else:
                for item in towrite:
                    if item == '255':
                        item = '0'
                    item = int_cast(item)
                    f.write(item.to_bytes(1, byteorder='big'))

            # write self.spells
            towrite[:] = []
            address = SHOP_SPELLS[self.shops.index(self.trainer.get())]
            f.seek(address)
            d = f.read(self.spell_read).hex()

            for i in self.spells:
                towrite.append(int(self.inv_spell_dic[i.get()][:2], 16))
                towrite.append(int(self.inv_spell_dic[i.get()][2:], 16))

            towrite.append(d[9] + d[10])

            for i in self.spell_levels:
                towrite.append(i.get())

            f.seek(address)
            for item in towrite:
                item = int_cast(item)
                f.write(item.to_bytes(1, byteorder='big'))

            # writes shop inventory to file
            towrite[:] = []
            if self.trainer.get() not in self.NOT_SHOPS:
                address = SHOP_ITEM_ADDRESSES[self.shops.index(self.trainer.get())]
                f.seek(address)
                d = f.read(106).hex()

                for item in self.shop_item:
                    towrite.append(int((self.inv_items[item.get()])[:2], 16))
                    towrite.append(int((self.inv_items[item.get()])[2:4], 16))
                    if self.shop_item.index(item) < 20:
                        for x in range(5, 11, 2):
                            towrite.append(int(d[((self.shop_item.index(item) * 10) + (x - 1))] +
                                               d[((self.shop_item.index(item) * 10) + x)], 16))

                f.seek(address)
                for item in towrite:
                    f.write(item.to_bytes(1, byteorder='big'))
        self.defaults()

    def build(self):
        self.default_name_menu.grid(column=0, row=0)

        self.save.grid(column=0, row=1)

        self.spell_frame.grid(column=0, row=2)
        for x in range(5):
            self.spell[x].grid(column=0, row=x, sticky='e')
            self.spell_level[x].grid(column=1, row=x, sticky='w')

        self.skill_frame.grid(column=1, row=0, rowspan=24, padx=(2, 5))

        for skill in SKILLS:
            x = SKILLS.index(skill)
            skill_label = Label(self.skill_frame, text=skill, anchor='e', width=9)
            skill_label.grid(column=0, row=x)
            skill_num = Entry(self.skill_frame, textvariable=self.skills[x], width=4)
            skill_num.grid(column=1, row=x)
        self.shield_label.grid(column=0, row=23)
        self.shield_num.grid(column=1, row=23)

        self.note1.configure(relief="flat")
        self.note_box.grid(column=0, row=3)
        self.note1.grid()
        self.note2.grid()

        for item in self.item_box:
            item.grid()

    def skill_frame_text(self, *args):
        if self.trainer.get() == self.becan:
            self.skill_frame['text'] = 'Skills\n(blank = cannot learn)'
            self.skill_frame.grid(ipadx=0)
        else:
            self.skill_frame['text'] = 'Skills\n'
            self.skill_frame.grid(ipadx=15)
