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
import yaml

from geomet_climate.env import BASEDIR, CONFIG, DATADIR

LOGGER = logging.getLogger(__name__)

VRT_TEMPLATE_FULL = '''<VRTDataset rasterXSize="{}" rasterYSize="{}">
 <GeoTransform>{}</GeoTransform>
  <VRTRasterBand dataType="Float64" band="1">
    <SimpleSource>
      <SourceFilename relativeToVRT="0">{}</SourceFilename>
      <SourceBand>{}</SourceBand>
      <SourceProperties RasterXSize="{}" RasterYSize="{}"
          DataType="Float64" BlockXSize="{}" BlockYSize="1" />
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>'''

VRT_TEMPLATE_HEADER = '''<VRTDataset rasterXSize="{}" rasterYSize="{}">
 <GeoTransform>{}</GeoTransform>'''

VRT_TEMPLATE_BODY = '''<VRTRasterBand dataType="Float64" band="{}">
    <SimpleSource>
     <SourceFilename relativeToVRT="0">{}</SourceFilename>
     <SourceBand>1</SourceBand>
     <SourceProperties RasterXSize="{}" RasterYSize="{}"
         DataType="Float64" BlockXSize="{}" BlockYSize="1" />
   </SimpleSource>
  </VRTRasterBand>'''

VRT_TEMPLATE_FOOTER = '''
</VRTDataset>'''


def create_vrt(layer_info, vrt_list, output_dir, vrt_name):
    """
    This function is called when we need to create a VRT
    We need a separate function because for cangrd VRT of month
    we want to create a whole VRT for wms and a single month vrt for WCS
    """

    num = 1
    sources = []
    xsize, ysize = layer_info['climate_model']['dimensions']
    for f in sorted(vrt_list):
        filename = os.path.abspath(
            os.path.join(
                DATADIR,
                layer_info['climate_model']['basepath'],
                layer_info['filepath'], f
            )
        )
        source_data = VRT_TEMPLATE_BODY.format(num - 1, filename,
                                               xsize, ysize, xsize)
        sources.append(source_data)
        num += 1

    LOGGER.debug('Creating VRT file for CanGRD')
    vrt_header = VRT_TEMPLATE_HEADER.format(
        xsize, ysize, layer_info['climate_model']['geo_transform'])

    vrt_footer = VRT_TEMPLATE_FOOTER

    output = '{}{}{}{}{}'.format(output_dir, os.sep,
                                 layer_info['climate_model']['basepath'],
                                 os.sep, layer_info['filepath'])
    if not os.path.exists(output):
        os.makedirs(output)
    filepath = os.path.join(output, vrt_name)

    vrt = '{}{}{}'.format(vrt_header, '\n'.join(sources), vrt_footer)

    with open(filepath, 'w') as fh:
        fh.write(vrt)


def generate_vrt_list(layer_info, output_dir):
    """
    This script creates a VRT file per file band.
    This is needed for creating the tile index.
    in the DCS and CMIP5 netcdf files, 1 band = 1 time step
    So for the tile index we create various VRTs which each
    represent a band of the file
    """

    basepath = layer_info['climate_model']['basepath']

    if layer_info['climate_model']['is_vrt'] and layer_info['num_bands'] > 1:
        xsize, ysize = layer_info['climate_model']['dimensions']
        filename = os.path.join(DATADIR,
                                layer_info['climate_model']['basepath'],
                                layer_info['filepath'],
                                layer_info['filename'])

        LOGGER.debug('Creating VRT files for {} bands'.format(
            layer_info['num_bands']))
        for i in range(1, layer_info['num_bands'] + 1):
            LOGGER.debug('Creating VRT file for band {}'.format(i))
            f_end = '_{}.vrt'.format(i)
            vrt_name = layer_info['filename'].replace('.nc', f_end)
            vrt = VRT_TEMPLATE_FULL.format(
                xsize, ysize, layer_info['climate_model']['geo_transform'],
                filename, i, xsize, ysize, xsize)

            output = '{}{}{}{}{}'.format(output_dir, os.sep,
                                         basepath,
                                         os.sep, layer_info['filepath'])
            if not os.path.exists(output):
                os.makedirs(output)
            filepath = os.path.join(output, vrt_name)

            with open(filepath, 'w') as fh:
                fh.write(vrt)
    elif (not layer_info['climate_model']['is_vrt'] and
          layer_info['type'] == 'RASTER'
          and layer_info['filename'].startswith('CANGRD')):
        dirname = os.path.join(DATADIR,
                               basepath,
                               layer_info['filepath'])
        list_file = os.listdir(dirname)
        vrt_list = []

        for k in list_file:
            if k.startswith(layer_info['filename']):
                vrt_list.append(k)

        vrt_name = '{}.vrt'.format(layer_info['filename'])
        create_vrt(layer_info, vrt_list, output_dir, vrt_name)


@click.group()
def vrt():
    pass


@click.command()
@click.pass_context
@click.option('--layer', '-lyr', help='layer')
def generate(ctx, layer):
    """generate VRT"""

    output_dir = '{}{}vrt'.format(BASEDIR, os.sep)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(CONFIG) as fh:
        cfg = yaml.load(fh)

        if layer is not None:
            generate_vrt_list(cfg['layers'][layer], output_dir)
        else:
            for key, value in cfg['layers'].items():
                generate_vrt_list(value, output_dir)


vrt.add_command(generate)
