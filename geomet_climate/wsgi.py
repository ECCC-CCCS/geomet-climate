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

import io
import logging
import os

import click
from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
import mapscript

from geomet_climate.env import BASEDIR

LOGGER = logging.getLogger(__name__)

# List of all environment variable used by MapServer
MAPSERV_ENV = [
  'CONTENT_LENGTH', 'CONTENT_TYPE', 'CURL_CA_BUNDLE', 'HTTP_COOKIE',
  'HTTP_HOST', 'HTTPS', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_FORWARDED_PORT',
  'HTTP_X_FORWARDED_PROTO', 'MS_DEBUGLEVEL', 'MS_ENCRYPTION_KEY',
  'MS_ERRORFILE', 'MS_MAPFILE', 'MS_MAPFILE_PATTERN', 'MS_MAP_NO_PATH',
  'MS_MAP_PATTERN', 'MS_MODE', 'MS_OPENLAYERS_JS_URL', 'MS_TEMPPATH',
  'MS_XMLMAPFILE_XSLT', 'PROJ_LIB', 'QUERY_STRING', 'REMOTE_ADDR',
  'REQUEST_METHOD', 'SCRIPT_NAME', 'SERVER_NAME', 'SERVER_PORT'
]

WCS_FORMATS = {
    'image/tiff': 'tif',
    'image/netcdf': 'nc'
}

SERVICE_EXCEPTION = '''<?xml version='1.0' encoding="UTF-8" standalone="no"?>
<ServiceExceptionReport version="1.3.0" xmlns="http://www.opengis.net/ogc"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/ogc
    http://schemas.opengis.net/wms/1.3.0/exceptions_1_3_0.xsd">
  <ServiceException>{}</ServiceException>
</ServiceExceptionReport>'''


def metadata_lang(m, lg):
    """
    function to update the mapfile MAP metadata
    keys in function of the lang of the request

    :param m: mapfile.web object to update language
    :param lg: lang of the request
    """

    m.metadata['ows_address'] = m.metadata[f'ows_address_{lg}']
    m.metadata['ows_contactperson'] = m.metadata[f'ows_contactperson_{lg}']
    m.metadata['ows_city'] = m.metadata[f'ows_city_{lg}']
    m.metadata['ows_country'] = m.metadata[f'ows_country_{lg}']
    m.metadata['ows_keywordlist_http://purl.org/dc/terms/_items'] = m.metadata[f'ows_keywordlist_http://purl.org/dc/terms/_items_{lg}']  # noqa
    m.metadata['wms_attribution_title'] = m.metadata[f'wms_attribution_title_{lg}']  # noqa
    m.metadata['ows_contactinstructions'] = m.metadata[f'ows_contactinstructions_{lg}'] # noqa
    m.metadata['ows_contactposition'] = m.metadata[f'ows_contactposition_{lg}'] # noqa
    m.metadata['ows_contactorganization'] = m.metadata[f'ows_contactorganization_{lg}'] # noqa
    m.metadata['wms_attribution_onlineresource'] = m.metadata[f'wms_attribution_onlineresource_{lg}'] # noqa
    m.metadata['ows_onlineresource'] = m.metadata[f'ows_onlineresource_{lg}']
    m.metadata['ows_abstract'] = m.metadata[f'ows_abstract_{lg}']
    m.metadata['ows_service_onlineresource'] = m.metadata[f'ows_service_onlineresource_{lg}'] # noqa
    m.metadata['ows_title'] = m.metadata[f'ows_title_{lg}']
    m.metadata['ows_hoursofservice'] = m.metadata[f'ows_hoursofservice_{lg}']
    m.metadata['ows_stateorprovince'] = m.metadata[f'ows_stateorprovince_{lg}'] # noqa
    m.metadata['ows_keywordlist'] = m.metadata[f'ows_keywordlist_{lg}']
    m.metadata['wcs_description'] = m.metadata[f'wcs_description_{lg}']


def get_custom_service_exception(code, locator, text):
    """return custom wms:ServiceExceptionReport"""

    return bytes('''<?xml version='1.0' encoding="utf-8"?>
    <ogc:ServiceExceptionReport version="1.3.0"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/ogc
    http://schemas.opengis.net/wms/1.3.0/exceptions_1_3_0.xsd">
    <ogc:ServiceException code="{code}" locator="{locator}">{text}</ogc:ServiceException>
    </ogc:ServiceExceptionReport>'''.format(code=code, locator=locator, text=text), encoding='utf-8') # noqa


def application(env, start_response):
    """WSGI application for WMS/WCS"""
    for key in MAPSERV_ENV:
        if key in env:
            os.environ[key] = env[key]
        else:
            os.unsetenv(key)

    layer = None
    mapfile_ = None

    text = '''Veuillez spécifier une requête respectant le standard WMS, WFS ou WCS. 
    Pour davantage d\'information sur les services web géospatiaux GeoMet 
    du Service météorologique du Canada, veuillez visiter 
    https://www.canada.ca/fr/environnement-changement-climatique/services/conditions-meteorologiques-ressources-outils-generaux/outils-donnees-specialisees/services-web-geospatiaux.html / '  # noqa
    Please specify a request according to the WMS, WFS or WCS standards. 
    For more information on the Meteorological Service of Canada GeoMet 
    Geospatial Web Services, please visit 
    https://www.canada.ca/en/environment-climate-change/services/weather-general-tools-resources/weather-tools-specialized-data/geospatial-web-services.html'''  # noqa

    if not os.environ['QUERY_STRING']:
        response = get_custom_service_exception('MissingParameterValue',
                                                'request',
                                                text)

        start_response('200 OK', [('Content-type', 'text/xml')])
        return [response]
    else:
        request = mapscript.OWSRequest()
        request.loadParams()

    lang_ = request.getValueByName('LANG')
    service_ = request.getValueByName('SERVICE')
    request_ = request.getValueByName('REQUEST')
    layers_ = request.getValueByName('LAYERS')
    layer_ = request.getValueByName('LAYER')
    coverageid_ = request.getValueByName('COVERAGEID')
    format_ = request.getValueByName('FORMAT')
    style_ = request.getValueByName('STYLE')
    time_ = request.getValueByName('TIME')

    if lang_ is not None and lang_ in ['f', 'fr', 'fra']:
        lang = 'fr'
    else:
        lang = 'en'
    if layers_ is not None:
        layer = layers_
    elif layer_ is not None:
        layer = layer_
    elif coverageid_ is not None:
        layer = coverageid_
    else:
        layer = None
    if service_ is None:
        service_ = 'WMS'

    if layer is not None and len(layer) == 0:
        layer = None

    LOGGER.debug('service: {}'.format(service_))
    LOGGER.debug('language: {}'.format(lang))

    if layer is not None and ',' not in layer:
        mapfile_ = '{}/mapfile/geomet-climate-{}-{}.map'.format(
            BASEDIR, service_, layer)
    if mapfile_ is None or not os.path.exists(mapfile_):
        mapfile_ = '{}/mapfile/geomet-climate-{}-{}.map'.format(
            BASEDIR, service_, lang)
    if not os.path.exists(mapfile_):
        start_response('400 Bad Request',
                       [('Content-Type', 'application/xml')])
        msg = 'Unsupported service'
        return [SERVICE_EXCEPTION.format(msg)]

    # if requesting GetCapabilities for entire service, return cache
    if request_ == 'GetCapabilities':
        if layer is None:
            if service_ == 'WMS':
                filename = 'geomet-climate-WMS-1.3.0-capabilities-{}.xml'.format( # noqa
                    lang)
                cached_caps = os.path.join(BASEDIR, 'mapfile', filename)
            elif service_ == 'WCS':
                filename = 'geomet-climate-WCS-2.0.1-capabilities-{}.xml'.format( # noqa
                    lang)
                cached_caps = os.path.join(BASEDIR, 'mapfile', filename)

            if os.path.isfile(cached_caps):
                start_response('200 OK', [('Content-Type', 'application/xml')])
                with io.open(cached_caps, 'rb') as fh:
                    return [fh.read()]
        else:
            LOGGER.debug('Loading mapfile: {}'.format(mapfile_))
            mapfile = mapscript.mapObj(mapfile_)
            if request_ == 'GetCapabilities' and lang == 'fr':
                metadata_lang(mapfile.web, lang)
                layerobj = mapfile.getLayerByName(layer)
                layerobj.metadata['ows_title'] = layerobj.metadata[
                    f'ows_title_{lang}'
                ]
                layerobj.metadata['ows_layer_group'] = layerobj.metadata[
                    f'ows_layer_group_{lang}'
                ]

    elif request_ == 'GetLegendGraphic' and layer is not None:
        mapfile = mapscript.mapObj(mapfile_)
        if style_ in [None, '']:
            layerobj = mapfile.getLayerByName(layer)
            style_ = layerobj.classgroup
        filename = '{}-{}.png'.format(style_, lang)
        cached_legends = os.path.join(BASEDIR, 'legends', filename)

        if os.path.isfile(cached_legends):
            start_response('200 OK', [('Content-Type', 'image/png')])
            with io.open(cached_legends, 'rb') as ff:
                return [ff.read()]

    else:
        LOGGER.debug('Loading mapfile: {}'.format(mapfile_))
        mapfile = mapscript.mapObj(mapfile_)
        layerobj = mapfile.getLayerByName(layer)
        if request_ == 'GetCapabilities' and lang == 'fr':
            metadata_lang(mapfile, lang)
            layerobj.metadata['ows_title'] = layerobj.metadata[f'ows_title_{lang}'] # noqa
            layerobj.metadata['ows_layer_group'] = layerobj.metadata[f'ows_layer_group_{lang}'] # noqa

        if time_ and 'ows_timeextent' in layerobj.metadata.keys():
            try:
                dates = []
                timeextent = layerobj.metadata['ows_timeextent']

                start_date, end_date, duration = timeextent.split('/')
                start_date = isoparse(start_date)
                end_date = isoparse(end_date)
                time_iso = isoparse(time_)

                end_year_month = (end_date.year - start_date.year) * 12
                end_month = end_date.month - start_date.month
                end_date = end_year_month + end_month

                if duration == 'P1Y':
                    if time_ != time_iso.strftime('%Y'):
                        time_error = 'Format de temps invalide, ' \
                                     'format attendu : YYYY / ' \
                                     'Invalid time format, ' \
                                     'expected format: YYYY'
                        response = get_custom_service_exception('InvalidDimensionValue', # noqa
                                                                'time',
                                                                time_error)
                        start_response('200 OK', [('Content-type',
                                                   'text/xml')])
                        return [response]

                    for i in range(0, end_date + 1, 12):
                        date_ = start_date + relativedelta(months=i)
                        dates.append(date_.strftime('%Y'))

                else:
                    if time_ != time_iso.strftime('%Y-%m'):
                        time_error = 'Format de temps invalide, ' \
                                     'format attendu' \
                                     ' YYYY-MM / Invalid time format, ' \
                                     'expected format: YYYY-MM'
                        response = get_custom_service_exception('InvalidDimensionValue', # noqa
                                                                'time',
                                                                time_error)
                        start_response('200 OK', [('Content-type',
                                                   'text/xml')])
                        return [response]

                    for i in range(0, end_date + 1, 1):
                        date_ = start_date + relativedelta(months=i)
                        dates.append(date_.strftime('%Y-%m'))

                if time_ not in dates:
                    time_error = 'Temps en dehors des heures valides /' \
                                 ' Time outside valid hours'
                    response = get_custom_service_exception('NoMatch',
                                                            'time',
                                                            time_error)
                    start_response('200 OK', [('Content-type', 'text/xml')])
                    return [response]

            except ValueError:
                time_error = 'Valeur de temps invalide  /' \
                             ' Time value is invalid'
                response = get_custom_service_exception('InvalidDimensionValue', # noqa
                                                        'time',
                                                        time_error)
                start_response('200 OK', [('Content-type', 'text/xml')])
                return [response]

    mapscript.msIO_installStdoutToBuffer()
    request.loadParamsFromURL(env['QUERY_STRING'])

    try:
        LOGGER.debug('Dispatching OWS request')
        mapfile.OWSDispatch(request)
    except (mapscript.MapServerError, IOError) as err:
        # let error propagate to service exception
        LOGGER.error(err)
        pass

    headers = mapscript.msIO_getAndStripStdoutBufferMimeHeaders()

    headers_ = [
        ('Content-Type', headers['Content-Type']),
    ]

    # for WCS requests, generate useful filename for response
    if not headers['Content-Type'].startswith('text/xml'):
        if service_ == 'WCS' and request_ == 'GetCoverage':
            filename = 'geomet-climate-{}.{}'.format(layer,
                                                     WCS_FORMATS[format_])
            headers_.append(('Content-Disposition',
                             'attachment; filename="{}"'.format(filename)))

    content = mapscript.msIO_getStdoutBufferBytes()

    start_response('200 OK', headers_)

    return [content]


@click.command()
@click.pass_context
@click.option('--port', '-p', type=int, help='port', default=8099)
def serve(ctx, port):
    """Serve geomet-climate via wsgiref, for dev"""

    from wsgiref.simple_server import make_server
    httpd = make_server('', port, application)
    click.echo('Serving on port {}'.format(port))
    httpd.serve_forever()
