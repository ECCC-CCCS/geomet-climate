###############################################################################
#
# Copyright (C) 2020 Louis-Philippe Rousseau-Lambert
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import io
import json
import logging
import os

import click
import matplotlib as mpl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
import yaml
from yaml import CLoader

from geomet_climate.env import BASEDIR, CONFIG

LOGGER = logging.getLogger(__name__)

THISDIR = os.path.dirname(os.path.realpath(__file__))


def generate_legend(layer_info, output_dir):
    """
    Generate legends from matplotlib
    based on information in the configuration file

    :param layer_info: layer information
    :param output_dir: path to output legend

    :returns: True if the legends were generated
    """

    group = layer_info['classgroup']
    color_arr = []
    linear = False
    discrete = False

    style_path = os.path.join(THISDIR, 'resources', layer_info['styles'][0])
    with io.open(style_path) as fh:
        style_json = json.load(fh)

    for map_class in style_json:
        if 'colorrange' in map_class['style']:
            color = map_class['style']['colorrange']
        else:
            color = map_class['style']['color']
        if len(color) == 6:
            linear = True
            rgb1 = color[:3]
            rgb2 = color[3:]
            if rgb1 not in color_arr:
                color_arr.append(rgb1)
            if rgb2 not in color_arr:
                color_arr.append(rgb2)

        elif len(color) == 3:
            discrete = True
            color_arr.append(color)

    if linear:
        min_value = style_json[0]['name'].split(' ')[0]
        max_value = style_json[-1]['name'].split(' ')[-1]

        fig = Figure(figsize=(2, 5))  # , constrained_layout=True)
        canvas = FigureCanvasAgg(fig) # noqa
        # when moving to ubuntu 18.04 and remove add_subplots
        # ax = fig.subplots()
        ax = fig.add_subplot(121)

        all_vals = np.array([[0, 0, 0, 1]])

        for i in range(0, len(color_arr) - 1):
            # number of interpolated values between 2 color ramps
            N = 25
            # 4 = RGBA
            vals = np.ones((N, 4))
            # Red
            vals[:, 0] = np.linspace(color_arr[i][0] / 256.0,
                                     color_arr[i + 1][0] / 256.0,
                                     N)
            # Green
            vals[:, 1] = np.linspace(color_arr[i][1] / 256.0,
                                     color_arr[i + 1][1] / 256.0,
                                     N)
            # Blue
            vals[:, 2] = np.linspace(color_arr[i][2] / 256.0,
                                     color_arr[i + 1][2] / 256.0,
                                     N)
            all_vals = np.concatenate((all_vals, vals))

        newcmp = mpl.colors.ListedColormap(all_vals)
        norm = mpl.colors.Normalize(vmin=float(min_value),
                                    vmax=float(max_value))
        cb = mpl.colorbar.ColorbarBase(ax, cmap=newcmp, norm=norm)

    if discrete:
        bounds = layer_info['bounds']
        vals = np.ones((1, 4))

        fig = Figure(figsize=(2, 6))  # , constrained_layout=True)
        canvas = FigureCanvasAgg(fig) # noqa
        # when moving to ubuntu 18.04 and remove add_subplots
        # ax = fig.subplots()
        ax = fig.add_subplot(121)

        all_vals = np.array([[color_arr[0][0] / 256.0,
                              color_arr[0][1] / 256.0,
                              color_arr[0][2] / 256.0,
                              1]])

        for i in range(1, len(color_arr)):
            vals = [[color_arr[i][0] / 256.0,
                    color_arr[i][1] / 256.0,
                    color_arr[i][2] / 256.0,
                    1]]
            all_vals = np.concatenate((all_vals, vals))

        cmap = mpl.colors.ListedColormap(all_vals[1:-1])
        cmap.set_over(all_vals[-1])
        cmap.set_under(all_vals[0])

        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
        cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap,
                                       norm=norm,
                                       extend='both',
                                       extendfrac='auto',
                                       ticks=bounds,
                                       spacing='uniform')

    for lang in ['en', 'fr']:
        label = 'name_{}'.format(lang)
        legend_title = layer_info[label]
        cb.set_label(legend_title)

        legend_name = '{}-{}.png'.format(group, lang)
        fig.savefig(os.path.join(output_dir, legend_name))

    return True


@click.group()
def legend():
    pass


@click.command()
@click.pass_context
def generate(ctx):
    """generate Legends"""

    output_dir = '{}{}legends'.format(BASEDIR, os.sep)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with io.open(CONFIG) as fh:
        cfg = yaml.load(fh, Loader=CLoader)

        for key, value in cfg['layer_templates'].items():
            if value['type'] == 'RASTER':
                generate_legend(value, output_dir)


legend.add_command(generate)
