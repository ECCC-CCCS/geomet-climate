###############################################################################
#
# Copyright (C) 2018 Tom Kralidis
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

import logging
import os

import click
from osgeo import ogr, osr
import yaml

from geomet_climate.env import BASEDIR, CONFIG, DATADIR

LOGGER = logging.getLogger(__name__)


def get_time_index_novrt(layer_info):
    """
    This function is to create a dictionnary to associate
    the file (with one band, no VRT) with the associated time stamp
    """

    cangrd_file = []
    cangrd_dict = {}

    dirname = os.path.join(DATADIR,
                           layer_info['climate_model']['basepath'],
                           layer_info['filepath'])

    for f in os.listdir(dirname):
        if f.endswith('.tif') and f.startswith(layer_info['filename']):
            cangrd_file.append(f)

    for i in cangrd_file:
        filename = i.replace('.tif', '').split('_')
        time = filename[-1].split('-')
        if len(time) == 1:
            cangrd_dict[i] = time[0]
        else:
            month = time[-1]
            year = time[0]
            cangrd_dict[i] = '{}-{}'.format(year, month)

    return cangrd_dict


def get_time_index_vrt(layer_info, input_dir):
    """
    This function is to create a dictionnary to associate
    the file (vrt) with the associated time stamp
    """

    num = 0
    band_time = {}
    file_time = {}
    vrts = []

    vrt_name, extension = os.path.splitext(layer_info['filename'])

    input_ = '{}{}{}{}{}'.format(input_dir, os.sep,
                                 layer_info['climate_model']['basepath'],
                                 os.sep, layer_info['filepath'])

    for f in os.listdir(input_):
        if f.startswith(vrt_name):
            vrts.append(f)

    time_begin = layer_info['climate_model']['temporal_extent']['begin']
    num_bands = layer_info['num_bands']

    # Dict to associate the band number and the time they should refer to
    if layer_info['timestep'] == 'P1M':
        for i in range(1, num_bands + 1):
            begin_year, begin_month = time_begin.split('-')
            begin = (int(begin_year) * 12) + int(begin_month)
            time = begin + num
            year = (time/12)
            month = (time - (year * 12))
            if month == 0:
                    year = year - 1
                    month = 12
            time_stamp = '{}-{}'.format(year, str(month).zfill(2))
            band_time[i] = str(time_stamp)
            num += 1
    else:
        for i in range(1, num_bands + 1):
            time_stamp = time_begin + num
            band_time[i] = str(time_stamp)
            num += 1

    for k in vrts:
        band = k.replace('.vrt', '').split('_')[-1]
        file_time[k] = band_time[int(band)]

    return file_time


def create_shp(layer_info, input_dir, output_dir):
    """
    This function is needed to craete the tile index shapefile
    for every layer, we will want to create a shapefile tile index.

    Every shapefile will have a column with the absolute path to the VRT
    and a timestamp column for the time value associated with each band
    """
    file_time = None

    output = '{}{}{}{}{}'.format(output_dir, os.sep,
                                 layer_info['climate_model']['basepath'],
                                 os.sep, layer_info['filepath'])
    if not os.path.exists(output):
        os.makedirs(output)

    if layer_info['type'] == 'RASTER':
        if all(['is_vrt' in layer_info['climate_model'],
                layer_info['num_bands'] > 1]):
            LOGGER.info('Creating tileindex')
            file_time = get_time_index_vrt(layer_info, input_dir)
            shp_name = layer_info['filename'].replace('.nc', '')
            shp_path = os.path.join(output, layer_info['filename'].replace(
                                    '.nc', '.shp'))

        elif 'timestep' in layer_info and layer_info['num_bands'] == 1:
            file_time = get_time_index_novrt(layer_info)
            shp_name = layer_info['filename']
            shp_path = '{}.shp'.format(
                os.path.join(output, layer_info['filename']))

        else:
            msg = '{} is not a time enabled layer'.format(
                layer_info['label_en'])
            LOGGER.debug(msg)

    if file_time:
        LOGGER.debug('Creating dataset')
        driver = ogr.GetDriverByName('ESRI Shapefile')

        srs = osr.SpatialReference()
        srs.ImportFromWkt(layer_info['climate_model']['projection'])

        shapedata = driver.CreateDataSource(shp_path)
        layer = shapedata.CreateLayer(shp_name, srs, ogr.wkbPolygon)
        layerdefinition = layer.GetLayerDefn()
        layer.CreateField(ogr.FieldDefn('location', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('timestamp', ogr.OFTString))

        extent = layer_info['climate_model']['extent']
        extent = [int(s) for s in extent]

        LOGGER.info('Generating shape file')
        for key in file_time:
            LOGGER.debug('Adding feature to layer')
            if not key.endswith('.tif'):
                filename = os.path.abspath(os.path.join(
                    input_dir,
                    layer_info['climate_model']['basepath'],
                    layer_info['filepath'], key))
            elif key.endswith('.tif'):
                filename = os.path.abspath(
                    os.path.join(
                        DATADIR,
                        layer_info['climate_model']['basepath'],
                        layer_info['filepath'], key
                    )
                )

            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(extent[0], extent[1])
            ring.AddPoint(extent[0], extent[3])
            ring.AddPoint(extent[2], extent[3])
            ring.AddPoint(extent[2], extent[1])
            ring.AddPoint(extent[0], extent[1])
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            LOGGER.debug('Creating feature')
            feature = ogr.Feature(layerdefinition)
            LOGGER.debug('Creating geometry')
            feature.SetGeometry(poly)
            LOGGER.debug('Adding fields')
            feature.SetField('location', filename)
            feature.SetField('timestamp', file_time[key])
            layer.CreateFeature(feature)

        LOGGER.debug('Generating index')
        shapedata.ExecuteSQL('CREATE SPATIAL INDEX ON {}'.format(shp_name))


@click.group()
def tileindex():
    pass


@click.command()
@click.pass_context
@click.option('--layer', '-lyr', help='layer')
def generate(ctx, layer):
    """generate tileindex"""

    input_dir = '{}{}vrt'.format(BASEDIR, os.sep)
    output_dir = '{}{}tileindex'.format(BASEDIR, os.sep)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(CONFIG) as fh:
        cfg = yaml.load(fh)

        if layer is not None:
            if not cfg['layers'][layer]['type'] == 'POINT':
                create_shp(cfg['layers'][layer], input_dir, output_dir)
        else:
            for layers, values in cfg['layers'].items():
                if not values['type'] == 'POINT':
                    create_shp(values, input_dir, output_dir)


tileindex.add_command(generate)
