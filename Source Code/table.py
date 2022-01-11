# coding: utf-8

from tkinter import ttk, Canvas
from xlsxwriter import Workbook
from shutil import copyfile, rmtree
from numpy import load, asarray, save
from cv2 import imread, line, ellipse, imwrite
from os import path, mkdir
from platform import system
from dataclasses import dataclass

# color codes
background = '#EAECEE'
background_selected = '#ABB2B9'
label_line = '#646464'
label_line_selected = 'black'


@dataclass
class Labels:
    name: int
    nuclei: int
    positive: int
    ratio: int
    index: int
    fiber: int


@dataclass
class Lines:
    half_line: int
    full_line: int
    index_line: int


@dataclass
class Rectangle:
    rect: int


@dataclass
class Table_element:
    labels: Labels
    lines: Lines
    rect: Rectangle


class Table(ttk.Frame):

    def __init__(self, root):

        super().__init__(root)

        # initialise the canvas and scrollbar
        self._row_height = 50
        self._base_path = path.abspath('') + "/"

        self._set_layout()
        self._set_bindings()
        self._set_variables()

    def save_table(self, directory):

        # save to an Excel
        workbook = Workbook(self._base_path + 'Projects/' + directory +
                            '/' + directory + '.xlsx')
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True, 'align': 'center'})

        # write filenames
        worksheet.write(0, 0, "Image names", bold)
        max_size = 11
        for i, name in enumerate(self.filenames):
            name = path.basename(self.filenames[i])
            worksheet.write(i+2, 0, name)
            max_size = max(len(name), max_size)
        worksheet.set_column(0, 0, width=max_size)

        # write total nuclei
        worksheet.write(0, 1, "Total number of nuclei", bold)
        worksheet.set_column(1, 1, width=22)
        for i, name in enumerate(self.filenames):
            worksheet.write(i + 2, 1, len(self._nuclei_positions[i][0]) +
                            len(self._nuclei_positions[i][1]))

        # write green nuclei
        worksheet.write(0, 2, "Number of tropomyosin positive nuclei", bold)
        worksheet.set_column(2, 2, width=37)
        for i, name in enumerate(self.filenames):
            worksheet.write(i + 2, 2, len(self._nuclei_positions[i][1]))

        # write ratio
        worksheet.write(0, 3, "Fusion index", bold)
        worksheet.set_column(3, 3, width=17)
        for i, name in enumerate(self.filenames):
            if len(self._nuclei_positions[i][0]) > 0:
                worksheet.write(i + 2, 3, (len(self._nuclei_positions[i][1])) /
                                (len(self._nuclei_positions[i][0]) +
                                 len(self._nuclei_positions[i][1])))
            else:
                worksheet.write(i + 2, 3, 'NA')

        # write fibers
        worksheet.write(0, 4, "Number of Fibres", bold)
        worksheet.set_column(4, 4, width=16)
        for i, name in enumerate(self.filenames):
            worksheet.write(i + 2, 4, len(self._fibre_positions[i]))

        workbook.close()

    def load_project(self, directory):

        # reset
        self.reset()

        # load the data
        if path.isfile(directory + '/data.npy') and \
                path.isdir(directory + '/Original Images'):
            data = load(directory + '/data.npy', allow_pickle=True).tolist()
            for item in data:
                if len(item) == 4:
                    if type(item[0]) == str and type(item[1]) == list and \
                            type(item[2]) == list and type(item[3]) == list:
                        if path.isfile(item[0]):
                            self.filenames.append(self._base_path + item[0])
                            self._nuclei_positions.append([item[1], item[2]])
                            self._fibre_positions.append(item[3])

        # make the table
        self._make_table()

    def save_data(self, directory):

        # make array
        to_save = []
        for i, filename in enumerate(self.filenames):
            to_save.append(["Projects/" + directory + '/Original Images/' +
                            path.basename(filename),
                            self._nuclei_positions[i][0],
                            self._nuclei_positions[i][1],
                            self._fibre_positions[i]])

        # convert to numpy
        arr = asarray(to_save)
        save(self._base_path + 'Projects/' + directory + '/data', arr)

    def save_originals(self, directory):

        # create a directory with the original images
        if not path.isdir(self._base_path + 'Projects/' + directory +
                          '/Original Images'):
            mkdir(self._base_path + 'Projects/' + directory +
                  '/Original Images')

        # save the images
        for filename in self.filenames:
            basename = path.basename(filename)
            if filename != self._base_path + 'Projects/' + directory + \
                    '/Original Images/' + basename:
                copyfile(filename, self._base_path + 'Projects/' + directory
                         + '/Original Images/' + basename)

    def save_altered_images(self, directory):

        # create a directory with the altered images
        if path.isdir(self._base_path + 'Projects/' + directory +
                      '/Altered Images'):
            rmtree(self._base_path + 'Projects/' + directory +
                   '/Altered Images')
        mkdir(self._base_path + 'Projects/' + directory + '/Altered Images')

        # read the images and then save them
        for i, filename in enumerate(self.filenames):
            self._draw_nuclei_save(i, directory)

       # update the image canvas handle
    def set_image_canvas(self, image_canvas):
        self._image_canvas = image_canvas

    def add_fibre(self, position):
        self._fibre_positions[self._current_image_index].append(position)
        self._update_data(self._current_image_index)

    def remove_fibre(self, position):
        self._fibre_positions[self._current_image_index].remove(position)
        self._update_data(self._current_image_index)

    def add_out_nucleus(self, position):
        self._nuclei_positions[self._current_image_index][0].append(position)
        self._update_data(self._current_image_index)

    def remove_out_nucleus(self, position):
        self._nuclei_positions[self._current_image_index][0].remove(position)
        self._update_data(self._current_image_index)

    def remove_in_nucleus(self, position):
        self._nuclei_positions[self._current_image_index][1].remove(position)
        self._update_data(self._current_image_index)

    def in_to_out(self, position):
        self._nuclei_positions[self._current_image_index][0].append(position)
        self._nuclei_positions[self._current_image_index][1].remove(position)
        self._update_data(self._current_image_index)

    def out_to_in(self, position):
        self._nuclei_positions[self._current_image_index][1].append(position)
        self._nuclei_positions[self._current_image_index][0].remove(position)
        self._update_data(self._current_image_index)

    def reset(self):
        # remove everything previous
        for item in self._canvas.find_all():
            self._canvas.delete(item)

        self._items = []
        self._current_image_index = 0
        self._hovering_index = None
        self._nuclei_positions = []
        self._fibre_positions = []
        self.filenames = []

    def add_images(self, filenames):

        # remove everything previous
        for item in self._canvas.find_all():
            self._canvas.delete(item)

        self._items = []

        # add the filenames
        self.filenames += filenames
        self._nuclei_positions += [[[], []] for _ in filenames]
        self._fibre_positions += [[] for _ in filenames]

        # make the table
        self._make_table()

    def input_processed_data(self, nuclei_negative_positions,
                             nuclei_positive_positions, fibre_centres, index):

        # update the data
        self._nuclei_positions[index] = [nuclei_negative_positions,
                                         nuclei_positive_positions]
        if len(fibre_centres) > 0:
            self._fibre_positions[index] = fibre_centres
        self._update_data(index)

        # load the new image if necessary
        if index == self._current_image_index:
            self._image_canvas.load_image(
                self.filenames[self._current_image_index],
                self._nuclei_positions[self._current_image_index],
                self._fibre_positions[self._current_image_index])

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
        self._nuclei_positions = []
        self._fibre_positions = []
        self.filenames = []
        self._current_image_index = 0
        self._hovering_index = None
        self._image_canvas = None

        # handles to widgets on the canvas
        self._items = []

    def _draw_nuclei_save(self, index, project_name):

        # loop through the fibres
        cv_img = imread(self._base_path + "Projects/" + project_name +
                        "/Original Images/" +
                        path.basename(self.filenames[index]))
        square_size = 9
        for i in range(len(self._fibre_positions[index])):
            centre = (int(self._fibre_positions[index][i][0] *
                          cv_img.shape[1]),
                      int(self._fibre_positions[index][i][1] *
                          cv_img.shape[0]))
            line(cv_img, (centre[0] + square_size, centre[1]),
                 (centre[0] - square_size, centre[1]), (0, 0, 255), 2)
            line(cv_img, (centre[0], centre[1] + square_size),
                 (centre[0], centre[1] - square_size), (0, 0, 255), 2)

        # loop through the nuclei
        for i in range(len(self._nuclei_positions[index][0]) +
                       len(self._nuclei_positions[index][1])):

            if i < len(self._nuclei_positions[index][0]):
                # red (negative)
                centre = (int(self._nuclei_positions[index][0][i][0] *
                              cv_img.shape[1]),
                          int(self._nuclei_positions[index][0][i][1] *
                              cv_img.shape[0]))
                ellipse(cv_img, centre, (3, 3), 0, 0, 360,
                        (0, 0, 255), -1)
                ellipse(cv_img, centre, (4, 4), 0, 0, 360,
                        (255, 255, 255), 1)
            else:
                # yellow (positive)
                centre = (int(self._nuclei_positions[index][1]
                              [i - len(self._nuclei_positions[index][0])][0] *
                              cv_img.shape[1]),
                          int(self._nuclei_positions[index][1]
                              [i - len(self._nuclei_positions[index][0])][1] *
                              cv_img.shape[0]))
                ellipse(cv_img, centre, (3, 3), 0, 0, 360,
                        (0, 255, 255), -1)
                ellipse(cv_img, centre, (4, 4), 0, 0, 360,
                        (255, 255, 255), 1)

        # save it
        imwrite(self._base_path + "Projects/" + project_name +
                "/Altered Images/"
                + path.basename(self.filenames[index])[:-4] + ".png",
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
        total_nuclei = len(self._nuclei_positions[index][0]) + \
                       len(self._nuclei_positions[index][1])
        self._canvas.itemconfig(self._items[index].labels.nuclei,
                                text='Total : ' + str(total_nuclei))
        self._canvas.itemconfig(
            self._items[index].labels.positive,
            text='Positive : ' + str(len(self._nuclei_positions[index][1])))
        if total_nuclei > 0:
            self._canvas.itemconfig(
                self._items[index].labels.ratio,
                text="Ratio : {:.2f}%".format(
                    100 * len(self._nuclei_positions[index][1]) /
                    total_nuclei))
        else:
            self._canvas.itemconfig(self._items[index].labels.ratio,
                                    text='Ratio : NA')
        self._canvas.itemconfig(
            self._items[index].labels.fiber,
            text='Fibres : ' + str(len(self._fibre_positions[index])))

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
                                      self._nuclei_positions[index],
                                      self._fibre_positions[index])
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
        for i, name in enumerate(self.filenames):
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
            file_name = path.basename(name)
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
