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

from collections import OrderedDict
from datetime import datetime
import io
import json
import logging
import os
import shutil

import click
import mappyfile
from osgeo import osr
import yaml

from geomet_climate import __version__
from geomet_climate.env import BASEDIR, CONFIG, DATADIR, URL

MAPFILE_BASE = '{}{}resources{}mapfile-base.json'.format(os.path.dirname(
    os.path.realpath(__file__)), os.sep, os.sep)

LOGGER = logging.getLogger(__name__)

THISDIR = os.path.dirname(os.path.realpath(__file__))


def gen_web_metadata(m, c, lang, service, url):
    """
    update mapfile MAP.WEB.METADATA section

    :param m: base mapfile JSON object
    :param c: configuration YAML metadata object
    :param lang: language (en or fr)
    :param service: service (WMS or WCS)
    :param url: URL of service

    :returns: dict of web metadata
    """

    LOGGER.debug('setting web metadata')

    d = {
        '__type__': 'metadata'
    }

    LOGGER.debug('Language: {}'.format(lang))
    LOGGER.debug('Service: {}'.format(service))

    if lang == 'fr':
        d['ows_onlineresource'] = '{}?lang=fr'.format(url)
    else:
        d['ows_onlineresource'] = url

    LOGGER.debug('URL: {}'.format(d['ows_onlineresource']))

    LOGGER.debug('Setting service identification metadata')

    service_title = u'{} {}'.format(
        c['identification']['title'][lang], __version__)

    d['ows_title'] = service_title
    d['ows_abstract'] = c['identification']['abstract'][lang]
    d['ows_keywordlist_vocabulary'] = 'http://purl.org/dc/terms/'
    d['ows_keywordlist_http://purl.org/dc/terms/_items'] = ','.join(
        c['identification']['keywords'][lang])

    d['ows_fees'] = c['identification']['fees']
    d['ows_accessconstraints'] = c['identification']['accessconstraints']
    d['wms_getmap_formatlist'] = 'image/png,image/jpeg'
    d['ows_extent'] = ','.join(str(x) for x in m['extent'])
    d['ows_role'] = c['provider']['role']
    d['ows_http_max_age'] = 604800  # cache for one week
    d['ows_updatesequence'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    d['ows_service_onlineresource'] = c['identification']['url'][lang]
    d['encoding'] = 'UTF-8'
    d['ows_srs'] = m['web']['metadata']['ows_srs']

    LOGGER.debug('Setting contact information')
    d['ows_contactperson'] = c['provider']['contact']['name'][lang]
    d['ows_contactposition'] = c['provider']['contact']['position'][lang]
    d['ows_contactorganization'] = c['provider']['name'][lang]
    d['ows_address'] = \
        c['provider']['contact']['address']['delivery_point'][lang]

    d['ows_addresstype'] = 'postal'
    d['ows_addresstype'] = 'postal'
    d['ows_city'] = c['provider']['contact']['address']['city'][lang]
    d['ows_stateorprovince'] = \
        c['provider']['contact']['address']['stateorprovince'][lang]

    d['ows_postcode'] = c['provider']['contact']['address']['postalcode']
    d['ows_country'] = c['provider']['contact']['address']['country'][lang]
    d['ows_contactelectronicmailaddress'] = \
        c['provider']['contact']['address']['email']

    d['ows_contactvoicetelephone'] = c['provider']['contact']['phone']['voice']
    d['ows_contactfacsimiletelephone'] = \
        c['provider']['contact']['phone']['fax']

    d['ows_contactinstructions'] = \
        c['provider']['contact']['instructions'][lang]

    d['ows_hoursofservice'] = c['provider']['contact']['hours'][lang]

    if service == 'WMS':
        d['wms_enable_request'] = '*'
        d['wms_getfeatureinfo_formatlist'] = \
            'text/plain,application/json,application/vnd.ogc.gml'
        d['wms_attribution_onlineresource'] = c['attribution']['url'][lang]
        d['wms_attribution_title'] = c['attribution']['title'][lang]
        d['wms_attribution_logourl_format'] = c['provider']['logo']['format']
        d['wms_attribution_logourl_width'] = c['provider']['logo']['width']
        d['wms_attribution_logourl_height'] = c['provider']['logo']['height']
        d['wms_attribution_logourl_href'] = c['provider']['logo']['href']
    elif service == 'WCS':
        d['wcs_enable_request'] = '*'
        d['wcs_label'] = service_title
        d['wcs_description'] = c['identification']['abstract'][lang]
        d['ows_keywordlist'] = ','.join(c['identification']['keywords'][lang])

    return d


def gen_layer_metadataurl(layer_name, layer_info):
    """
    function to create the metadata url based on
    some information in the yaml at the model level.
    This function will eventually be updated to add more information

    :param layer_name: name of layer
    :param layer_info: layer information

    :return: dict of layer metadata url keys
    """
    meta_dict = {}

    layer_name_list = layer_name.replace('_', '.').split('.')

    for key in layer_info['climate_model']['metadata_id']:
        if key.upper() in layer_name_list:
            id_ = layer_info['climate_model']['metadata_id'][key]

    metadata_url = ('https://csw.open.canada.ca/geonetwork/srv/csw?'
                    'service=CSW&'
                    'version=2.0.2&'
                    'request=GetRecordById&'
                    'outputschema=csw:IsoRecord&'
                    'elementsetname=full&'
                    'id={}'.format(id_))

    meta_dict['ows_metadataurl_href'] = metadata_url
    meta_dict['ows_metadataurl_format'] = 'text/xml'
    meta_dict['ows_metadataurl_type'] = 'ISO 19115:2003'

    return meta_dict


def gen_layer(layer_name, layer_info, lang,  template_path, service='WMS'):
    """
    mapfile layer object generator

    :param layer_name: name of layer
    :param layer_info: layer information
    :param lang: language (en or fr)
    :param service: service (WMS or WCS)

    :returns: list of mappyfile layer objects of layer
    """

    layers = []

    LOGGER.debug('Setting up layer configuration')
    layer_tileindex = {
        '__type__': 'layer'
    }

    if 'timestep' in layer_info and service == 'WMS':
        layer_tileindex_name = '{}-tileindex'.format(layer_name)

        layer_tileindex['type'] = 'POLYGON'
        layer_tileindex['name'] = layer_tileindex_name
        layer_tileindex['status'] = 'OFF'
        layer_tileindex['CONNECTIONTYPE'] = 'OGR'

        if layer_info['filename'].startswith('CANGRD'):
            filename = '{}.gpkg'.format(layer_info['filename'])
        else:
            filename = layer_info['filename'].replace('.nc', '.gpkg')
        data = os.path.join(BASEDIR, 'tileindex',
                            layer_info['climate_model']['basepath'],
                            layer_info['filepath'],
                            filename)

        layer_tileindex['CONNECTION'] = data
        layer_tileindex['metadata'] = {
            '__type__': 'metadata',
            'ows_enable_request': '!*'
        }

        layers.append(layer_tileindex)

    layer = {
        '__type__': 'layer',
        'classes': []
    }
    layer['type'] = 'RASTER'
    layer['dump'] = True
    layer['template'] = template_path
    layer['name'] = layer_name
    layer['tolerance'] = 150

    layer['metadata'] = {
        '__type__': 'metadata',
        'gml_include_items': 'all',
        'ows_include_items': 'all'
    }

    layer['status'] = 'ON'

    if layer_info['type'] == 'POINT':
        layer['type'] = layer_info['type']
        layer['connectiontype'] = 'OGR'
        layer['connection'] = 'ES:{}'.format(
            layer_info['climate_model']['basepath'])

    if 'timestep' in layer_info and service == 'WMS':
        layer['tileindex'] = layer_tileindex_name
        layer['tileitem'] = 'location'
    elif layer_info['type'] == 'POINT':
        layer['data'] = layer_info['filename']
    else:
        datapath = os.path.join(
            DATADIR,
            layer_info['climate_model']['basepath'],
            layer_info['filepath'],
            layer_info['filename']
        )

        layer['data'] = datapath

    LOGGER.debug('Setting projection')
    if layer_name.startswith('CANGRD'):
        layer['projection'] = ['init=epsg:102998']
    else:
        projection = osr.SpatialReference()
        projection.ImportFromWkt(layer_info['climate_model']['projection'])
        layer['projection'] = [projection.ExportToProj4().strip()]

    if service == 'WCS' and layer_info['type'] == 'RASTER':
        layer['metadata']['wcs_label'] = layer_info['label_{}'.format(lang)]
        layer['metadata']['wcs_bandcount'] = layer_info['num_bands']

        xsize, ysize = layer_info['climate_model']['dimensions']
        layer['metadata']['wcs_size'] = '{} {}'.format(xsize, ysize)

    if service == 'WCS' and 'timestep' in layer_info:
        LOGGER.debug('calculating band names')
        begin = layer_info['climate_model']['temporal_extent']['begin']
        end = layer_info['climate_model']['temporal_extent']['end']
        ts = layer_info['timestep']
        step = [int(s) for s in ts if s.isdigit()][0]

        band_names = []
        if ts == 'P1Y':
            for i in range(begin, end+step, step):
                i = 'B{}'.format(i)
                band_names.append(i)
        elif ts == 'P1M':
            begin = list(map(int, begin.split('-')))
            begin = (begin[0] * 12) + begin[1]
            end = list(map(int, end.split('-')))
            end = (end[0] * 12) + end[1]
            for i in range(begin, end+step, step):
                year = (i/12)
                month = (i - (year * 12))
                if month == 0:
                    year = year - 1
                    month = 12
                time = 'B{}-{}'.format(year, str(month).zfill(2))
                band_names.append(time)
        layer['metadata']['wcs_band_names'] = \
            ' '.join(str(x) for x in band_names)

        if layer_name.startswith('CANGRD'):
            layer['data'] = '{}.vrt'.format(
                 os.path.join(
                     BASEDIR,
                     'vrt',
                     layer_info['climate_model']['basepath'],
                     layer_info['filepath'],
                     layer_info['filename']
                 )
            )
            layer['metadata']['wcs_bandcount'] = len(band_names)

    extent = ' '.join(str(x) for x in layer_info['climate_model']['extent'])
    layer['metadata']['ows_extent'] = extent

    LOGGER.debug('Setting WMS layer hierarchy')
    layer_title_tokens = layer_info['label_{}'.format(lang)].split('/')
    layer_group_end = '/'.join(layer_title_tokens[:-1])

    layer_group = '/'.join([
        '/' + layer_info['climate_model']['label_{}'.format(lang)],
        layer_group_end
    ])

    if layer_group.endswith('/'):
        layer_group = layer_group[:-1]

    layer['metadata']['ows_layer_group'] = layer_group
    layer['metadata']['ows_title'] = layer_title_tokens[-1]
    if 'metadata_id' in layer_info['climate_model']:
        meta_url_dict = gen_layer_metadataurl(layer_name, layer_info)
        layer['metadata'].update(meta_url_dict)

    LOGGER.debug('Setting temporal properties')
    if 'timestep' in layer_info:
        time_extent = '{}/{}/{}'.format(
            layer_info['climate_model']['temporal_extent']['begin'],
            layer_info['climate_model']['temporal_extent']['end'],
            layer_info['timestep']
        )
        layer['metadata']['ows_timeitem'] = 'timestamp'
        layer['metadata']['ows_timeextent'] = time_extent
        layer['metadata']['ows_timedefault'] = \
            layer_info['climate_model']['temporal_extent']['end']

    LOGGER.debug('Setting style properties')
    if 'classgroup' in layer_info:
        layer['classgroup'] = layer_info['classgroup']

    if 'styles' in layer_info:
        for style in layer_info['styles']:
            style_filepath = os.path.join(THISDIR, 'resources', style)
            with io.open(style_filepath) as fh:
                new_class = json.load(fh)
                for class_ in new_class:
                    layer['classes'].append(class_)

    layers.append(layer)

    return layers


@click.group()
def mapfile():
    pass


@click.command()
@click.pass_context
@click.option('--language', '-l', 'lang', type=click.Choice(['en', 'fr']),
              help='language')
@click.option('--service', '-s', type=click.Choice(['WMS', 'WCS']),
              help='service')
@click.option('--layer', '-lyr', help='layer')
def generate(ctx, lang, service, layer):
    """generate mapfile"""

    output_dir = '{}{}mapfile'.format(BASEDIR, os.sep)
    template_dir = '{}{}mapfile{}template'.format(BASEDIR, os.sep, os.sep)

    all_layers = []

    if lang is None or service is None:
        raise click.UsageError('Missing arguments')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    with io.open(MAPFILE_BASE) as fh:
        mapfile = json.load(fh, object_pairs_hook=OrderedDict)
        symbols_file = os.path.join(THISDIR, 'resources/mapserv/symbols.json')
        with io.open(symbols_file) as fh2:
            mapfile['symbols'] = json.load(fh2)

    with io.open(CONFIG) as fh:
        cfg = yaml.load(fh)

    if layer is not None:
        mapfiles = {
          layer: cfg['layers'][layer]
        }
    else:
        mapfiles = cfg['layers']

    mapfile['web']['metadata'] = gen_web_metadata(mapfile, cfg['metadata'],
                                                  lang, service, URL)

    for key, value in mapfiles.items():
        mapfile['layers'] = []

        template_name = 'template-{}.js'.format(key)
        template_path = '{}{}{}'.format(template_dir, os.sep, template_name)

        with io.open(template_path, 'w', encoding='utf-8') as fh:
            template_dir = os.path.join(THISDIR, 'resources', 'mapserv',
                                        'templates')

            stations_layers = ['CLIMATE.STATIONS', 'HYDROMETRIC.STATIONS',
                               'AHCCD.STATIONS']

            if key not in stations_layers:
                trf = os.path.join(template_dir, 'TEMPLATE_RASTER.json')
                with io.open(trf, encoding='utf-8') as template_raster:
                    template_raster = template_raster.read().replace('{}', key)
                    fh.write(template_raster)
            else:
                template_tmp_name = 'TEMPLATE_{}.json'.format(key)
                tvf = os.path.join(template_dir, template_tmp_name)
                with io.open(tvf, encoding='utf-8') as template_vector:
                    template_vector = template_vector.read().replace('{}', key)
                    fh.write(template_vector)

        layers = gen_layer(key, value, lang, template_path, service)

        for lyr in layers:
            mapfile['layers'].append(lyr)
            all_layers.append(lyr)

        filename = 'geomet-climate-{}-{}-{}.map'.format(service, key, lang)
        filepath = '{}{}{}'.format(output_dir, os.sep, filename)

        for i in mapfile['outputformats']:
            if i['name'] == 'GeoJSON':
                i['formatoption'] = ['FILE={}'.format(template_path)]

        with io.open(filepath, 'w', encoding='utf-8') as fh:
            mappyfile.dump(mapfile, fh)

    if layer is None:  # generate entire mapfile
        filename = 'geomet-climate-{}-{}.map'.format(service, lang)
        filepath = '{}{}{}'.format(output_dir, os.sep, filename)

        mapfile['layers'] = all_layers

        with io.open(filepath, 'w', encoding='utf-8') as fh:
            mappyfile.dump(mapfile, fh)

    epsg_file = os.path.join(THISDIR, 'resources', 'mapserv', 'epsg')
    shutil.copy2(epsg_file, os.path.join(BASEDIR, 'mapfile'))


mapfile.add_command(generate)
