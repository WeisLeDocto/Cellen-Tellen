# coding: utf-8

from tkinter import ttk, Canvas
from xlsxwriter import Workbook
from shutil import copyfile, rmtree
from numpy import load, asarray, save
from cv2 import imread, line, ellipse, imwrite
from pathlib import Path
from platform import system
from typing import List
from copy import deepcopy
from structure_classes import Nucleus, Fibre, Nuclei, Fibres, Labels, Lines, \
    Rectangle, Table_element

# color codes
background = '#EAECEE'
background_selected = '#ABB2B9'
label_line = '#646464'
label_line_selected = 'black'

in_fibre = 'yellow'  # green
out_fibre = 'red'  # 2A7DDE


class Table(ttk.Frame):

    def __init__(self, root):

        super().__init__(root)

        # initialise the canvas and scrollbar
        self._row_height = 50
        self._base_path = Path(__file__).parent
        self._projects_path = self._base_path / 'Projects'

        self._set_layout()
        self._set_bindings()
        self._set_variables()

    def save_table(self, directory: Path):

        # save to an Excel
        workbook = Workbook(str(directory / str(directory.name + '.xlsx')))
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True, 'align': 'center'})

        # write filenames
        worksheet.write(0, 0, "Image names", bold)
        max_size = 11
        for i, _ in enumerate(self.filenames):
            name = self.filenames[i].name
            worksheet.write(i+2, 0, name)
            max_size = max(len(name), max_size)
        worksheet.set_column(0, 0, width=max_size)

        # write total nuclei
        worksheet.write(0, 1, "Total number of nuclei", bold)
        worksheet.set_column(1, 1, width=22)
        for i, _ in enumerate(self.filenames):
            worksheet.write(i + 2, 1, len(self._nuclei[i]))

        # write green nuclei
        worksheet.write(0, 2, "Number of tropomyosin positive nuclei", bold)
        worksheet.set_column(2, 2, width=37)
        for i, _ in enumerate(self.filenames):
            worksheet.write(i + 2, 2, self._nuclei[i].nuclei_in_count)

        # write ratio
        worksheet.write(0, 3, "Fusion index", bold)
        worksheet.set_column(3, 3, width=17)
        for i, _ in enumerate(self.filenames):
            if self._nuclei[i].nuclei_out_count > 0:
                worksheet.write(i + 2, 3, self._nuclei[i].nuclei_in_count /
                                len(self._nuclei[i]))
            else:
                worksheet.write(i + 2, 3, 'NA')

        # write fibers
        worksheet.write(0, 4, "Number of Fibres", bold)
        worksheet.set_column(4, 4, width=16)
        for i, _ in enumerate(self.filenames):
            worksheet.write(i + 2, 4, len(self._fibres[i]))

        workbook.close()

    def load_project(self, directory: Path):

        # reset
        self.reset()

        # load the data
        if (directory / 'data.npy').is_file() and \
                (directory / 'Original Images').is_dir():
            data = load(str(directory / 'data.npy'),
                        allow_pickle=True).tolist()
            if isinstance(data, list):
                for item in data:
                    if len(item) == 4:
                        if isinstance(item[0], str) and \
                                isinstance(item[1], list) and \
                                isinstance(item[2], list) and \
                                isinstance(item[3], list):
                            if (directory / 'Original Images' /
                                    item[0]).is_file():
                                self.filenames.append(
                                    directory / 'Original Images' / item[0])
                                self._nuclei.append(
                                    Nuclei([Nucleus(x, y, None, out_fibre)
                                            for x, y in item[1]] +
                                           [Nucleus(x, y, None, in_fibre)
                                            for x, y in item[2]]))
                                self._fibres.append(
                                    Fibres([Fibre(x, y, None, None)
                                            for x, y in item[3]]))

        # make the table
        self._make_table()

    def save_data(self, directory: Path):

        # make array
        to_save = []
        for i, file in enumerate(self.filenames):
            nuc_out = [(nuc.x_pos, nuc.y_pos) for nuc in self._nuclei[i]
                       if nuc.color == out_fibre]
            nuc_in = [(nuc.x_pos, nuc.y_pos) for nuc in self._nuclei[i]
                      if nuc.color == in_fibre]
            fib = [(fib.x_pos, fib.y_pos) for fib in self._fibres[i]]
            to_save.append([file.name,
                            nuc_out,
                            nuc_in,
                            fib])

        # convert to numpy
        save(str(directory / 'data'), asarray(to_save))

    def save_originals(self, directory: Path):

        # create a directory with the original images
        if not (directory / 'Original Images').is_dir():
            Path.mkdir(directory / 'Original Images')

        # save the images
        for filename in self.filenames:
            if self._projects_path not in filename.parents:
                copyfile(filename, directory / 'Original Images' /
                         filename.name)

    def save_altered_images(self, directory: Path):

        # create a directory with the altered images
        if (directory / 'Altered Images').is_dir():
            rmtree(directory / 'Altered Images')
        Path.mkdir(directory / 'Altered Images')

        # read the images and then save them
        for i, _ in enumerate(self.filenames):
            self._draw_nuclei_save(i, directory)

       # update the image canvas handle
    def set_image_canvas(self, image_canvas):
        self._image_canvas = image_canvas

    def add_fibre(self, fibre):
        self._fibres[self._current_image_index].append(deepcopy(fibre))
        self._update_data(self._current_image_index)

    def remove_fibre(self, fibre):
        self._fibres[self._current_image_index].remove(fibre)
        self._update_data(self._current_image_index)

    def add_nucleus(self, nucleus):
        self._nuclei[self._current_image_index].append(deepcopy(nucleus))
        self._update_data(self._current_image_index)

    def remove_nucleus(self, nucleus):
        self._nuclei[self._current_image_index].remove(nucleus)
        self._update_data(self._current_image_index)

    def switch_nucleus(self, nucleus):
        for nuc in self._nuclei[self._current_image_index]:
            if nuc == nucleus:
                nuc.color = out_fibre if nuc.color == in_fibre else in_fibre
        self._update_data(self._current_image_index)

    def reset(self):
        # remove everything previous
        for item in self._canvas.find_all():
            self._canvas.delete(item)

        self._items = []
        self._current_image_index = 0
        self._hovering_index = None
        self._nuclei = []
        self._fibres = []
        self.filenames: List[Path] = []

    def add_images(self, filenames: List[Path]):

        # remove everything previous
        for item in self._canvas.find_all():
            self._canvas.delete(item)

        self._items = []

        # add the filenames
        self.filenames += filenames
        self._nuclei += [Nuclei() for _ in filenames]
        self._fibres += [Fibres() for _ in filenames]

        # make the table
        self._make_table()

    def input_processed_data(self, nuclei_negative_positions,
                             nuclei_positive_positions, fibre_centres, index):

        # update the data
        self._nuclei[index] = Nuclei()
        for x, y in nuclei_negative_positions:
            self._nuclei[index].append(Nucleus(x, y, None, out_fibre))
        for x, y in nuclei_positive_positions:
            self._nuclei[index].append(Nucleus(x, y, None, in_fibre))

        self._fibres[index] = Fibres()
        for x, y in fibre_centres:
            self._fibres[index].append(Fibre(x, y, None, None))

        self._update_data(index)

        # load the new image if necessary
        if index == self._current_image_index:
            self._image_canvas.load_image(
                self.filenames[self._current_image_index],
                self._nuclei[self._current_image_index],
                self._fibres[self._current_image_index])

    def _set_layout(self):
        self.pack(expand=True, fill="both", anchor="n", side='top')

        self._canvas = Canvas(self, bg='#FFFFFF',
                              highlightbackground='black',
                              highlightthickness=3)
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        self._canvas.pack(expand=True, fill="both", anchor="w", side='left',
                          pady=5)

        self._vbar = ttk.Scrollbar(self, orient="vertical")
        self._vbar.pack(side='right', fill='y', pady=5)
        self._vbar.config(command=self._canvas.yview)
        self._canvas.config(yscrollcommand=self._vbar.set)

        self.update()

    def _set_bindings(self):
        if system() == "Linux":
            self._canvas.bind('<4>', self._on_wheel)
            self._canvas.bind('<5>', self._on_wheel)
        else:
            self._canvas.bind('<MouseWheel>', self._on_wheel)
        self._canvas.bind('<ButtonPress-1>', self._left_click)
        self._canvas.bind('<Motion>', self._motion)

    def _set_variables(self):
        # data about the images
        self._nuclei = []
        self._fibres = []
        self.filenames = []
        self._current_image_index = 0
        self._hovering_index = None
        self._image_canvas = None

        # handles to widgets on the canvas
        self._items = []

    def _draw_nuclei_save(self, index, project_name: Path):

        # loop through the fibres
        cv_img = imread(str(project_name / "Original Images" /
                        self.filenames[index].name))
        square_size = 20
        for fib in self._fibres[index]:
            x, y = int(fib.x_pos), int(fib.y_pos)
            line(cv_img, (x + square_size, y), (x - square_size, y),
                 (0, 0, 255), 4)
            line(cv_img, (x, y + square_size), (x, y - square_size),
                 (0, 0, 255), 4)

        # loop through the nuclei
        for nuc in self._nuclei[index]:
            centre = (int(nuc.x_pos), int(nuc.y_pos))
            if nuc.color == out_fibre:
                ellipse(cv_img, centre, (6, 6), 0, 0, 360,
                        (0, 0, 255), -1)
            else:
                ellipse(cv_img, centre, (6, 6), 0, 0, 360,
                        (0, 255, 255), -1)

        # save it
        imwrite(str(project_name / "Altered Images" /
                    self.filenames[index].name),
                cv_img)

    def _on_wheel(self, event):

        if system() == "Linux":
            delta = 1 if event.num == 4 else -1
        else:
            delta = int(event.delta / abs(event.delta))

        if self._table_height > self._canvas.winfo_height():
            self._canvas.yview_scroll(-delta, "units")

    def _update_data(self, index):
        # set the variables labels for the image
        nuclei = self._nuclei[index]
        total_nuclei = len(nuclei)
        self._canvas.itemconfig(self._items[index].labels.nuclei,
                                text='Total : ' + str(total_nuclei))
        self._canvas.itemconfig(
            self._items[index].labels.positive,
            text='Positive : ' + str(nuclei.nuclei_in_count))
        if total_nuclei > 0:
            self._canvas.itemconfig(
                self._items[index].labels.ratio,
                text="Ratio : {:.2f}%".format(
                    100 * nuclei.nuclei_in_count /
                    total_nuclei))
        else:
            self._canvas.itemconfig(self._items[index].labels.ratio,
                                    text='Ratio : NA')
        self._canvas.itemconfig(
            self._items[index].labels.fiber,
            text='Fibres : ' + str(len(self._fibres[index])))

        # these functions are called by image window to update the lists
        # in the table

    def _motion(self, event):

        if self.filenames:
            # un hover previous
            if self._hovering_index is not None:
                self._un_hover(self._hovering_index)

            # hover over new item
            if self._canvas.canvasy(event.y) < self._table_height:
                self._hover(int(self._canvas.canvasy(event.y) /
                                (self._row_height * 2)))
        elif self._hovering_index is not None:
            self._un_hover(self._hovering_index)
            self._hovering_index = None

    def _hover(self, index):

        self._hovering_index = index
        self._set_aesthetics(index, selected=True, hover=True)

    def _un_hover(self, index):

        if index != self._current_image_index:
            self._set_aesthetics(index, selected=False, hover=True)

    def _unselect_image(self, index):

        self._set_aesthetics(index, selected=False, hover=False)

    def _select_image(self, index):

        self._image_canvas.load_image(self.filenames[index],
                                      self._nuclei[index], self._fibres[index])
        self._current_image_index = index
        self._set_aesthetics(index, selected=True, hover=False)

    def _set_aesthetics(self, index, selected, hover):

        line_color = label_line_selected if selected else label_line
        rect_color = background_selected if selected else background

        if index > 0:
            self._canvas.itemconfig(self._items[index-1].lines.full_line,
                                    fill=line_color)

        if not hover:
            self._canvas.itemconfig(self._items[index].rect.rect,
                                    fill=rect_color)

        self._canvas.itemconfig(self._items[index].lines.half_line,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].lines.full_line,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].lines.index_line,
                                fill=line_color)

        self._canvas.itemconfig(self._items[index].labels.name,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].labels.nuclei,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].labels.ratio,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].labels.positive,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].labels.index,
                                fill=line_color)
        self._canvas.itemconfig(self._items[index].labels.fiber,
                                fill=line_color)

    def _left_click(self, event):

        if self._canvas.canvasy(event.y) < self._table_height:
            # unselect previous
            self._unselect_image(self._current_image_index)

            # select new image
            self._select_image(int(self._canvas.canvasy(event.y) /
                                   (self._row_height * 2)))

    @property
    def _table_height(self):
        return self._row_height * 2 * len(self.filenames)

    def _make_table(self):

        # make the table
        width = self._canvas.winfo_width()
        for i, file in enumerate(self.filenames):
            top = 2 * i * self._row_height
            middle = (2 * i + 1) * self._row_height
            bottom = (2 * i + 2) * self._row_height

            # horizontal lines
            half_line = self._canvas.create_line(
                -1, middle, width, middle, width=1, fill=label_line)
            full_line = self._canvas.create_line(
                -1, bottom, width, bottom, width=3, fill=label_line)

            # rectangle
            rect = self._canvas.create_rectangle(
                -1, top, width, bottom, fill=background)
            self._canvas.tag_lower(rect)  # lower it (background)

            index_text = self._canvas.create_text(
                25, top + int(self._row_height / 2),
                text=str(i + 1), anchor='center',
                font=('Helvetica', 10, 'bold'), fill=label_line)
            index_line = self._canvas.create_line(
                50, top, 50, middle, width=1, fill=label_line)

            # set the filename
            file_name = file.name
            if len(file_name) >= 59:
                file_name = '...' + file_name[-59:]

            padding = 10
            name_text = self._canvas.create_text(
                60, top + int(self._row_height / 4),
                text=file_name, anchor='nw', fill=label_line)
            nuclei_text = self._canvas.create_text(
                padding, middle + int(self._row_height / 4),
                text='error', anchor='nw', fill=label_line)
            positive_text = self._canvas.create_text(
                padding + (width - 2 * padding) / 4,
                middle + int(self._row_height / 4),
                text='error', anchor='nw', fill=label_line)
            ratio_text = self._canvas.create_text(
                padding + (width - 2 * padding) * 2 / 4,
                middle + int(self._row_height / 4),
                text='error', anchor='nw', fill=label_line)
            fiber_text = self._canvas.create_text(
                padding * 3 + (width - 2 * padding) * 3 / 4,
                middle + int(self._row_height / 4),
                text='error', anchor='nw', fill=label_line)

            # append the handles
            self._items.append(Table_element(Labels(name_text,
                                                    nuclei_text,
                                                    positive_text,
                                                    ratio_text,
                                                    index_text,
                                                    fiber_text),
                                             Lines(half_line,
                                                   full_line,
                                                   index_line),
                                             Rectangle(rect)))

            # update the text
            self._update_data(i)

        # set scroll region
        self._canvas.config(scrollregion=(0, 0, width, self._table_height))

        # create highlighted parts
        if self.filenames:
            self._select_image(self._current_image_index)
        else:
            self._image_canvas.reset()
