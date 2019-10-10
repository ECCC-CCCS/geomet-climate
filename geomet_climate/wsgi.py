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


def metadata_lang(m, l):
    """
    function to update the mapfile MAP metadata
    keys in function of the lang of the request

    :param m: mapfile object to update language
    :param l: lang of the request
    """

    m.setMetaData('ows_address',
                  m.getMetaData('ows_address_{}'.format(l)))
    m.setMetaData('ows_contactperson',
                  m.getMetaData('ows_contactperson_{}'.format(l)))
    m.setMetaData('ows_city',
                  m.getMetaData('ows_city_{}'.format(l)))
    m.setMetaData('ows_country',
                  m.getMetaData('ows_country_{}'.format(l)))
    m.setMetaData('ows_keywordlist_http://purl.org/dc/terms/_items',
                  m.getMetaData('ows_keywordlist_http://purl.org/dc/terms/_items_{}'.format(l))) # noqa
    m.setMetaData('wms_attribution_title',
                  m.getMetaData('wms_attribution_title_{}'.format(l)))
    m.setMetaData('ows_contactinstructions',
                  m.getMetaData('ows_contactinstructions_{}'.format(l)))
    m.setMetaData('ows_contactposition',
                  m.getMetaData('ows_contactposition_{}'.format(l)))
    m.setMetaData('ows_contactorganization',
                  m.getMetaData('ows_contactorganization_{}'.format(l)))
    m.setMetaData('wms_attribution_onlineresource',
                  m.getMetaData('wms_attribution_onlineresource_{}'.format(l)))
    m.setMetaData('ows_onlineresource',
                  m.getMetaData('ows_onlineresource_{}'.format(l)))
    m.setMetaData('ows_abstract',
                  m.getMetaData('ows_abstract_{}'.format(l)))
    m.setMetaData('ows_service_onlineresource',
                  m.getMetaData('ows_service_onlineresource_{}'.format(l)))
    m.setMetaData('ows_title',
                  m.getMetaData('ows_title_{}'.format(l)))
    m.setMetaData('ows_hoursofservice',
                  m.getMetaData('ows_hoursofservice_{}'.format(l)))
    m.setMetaData('ows_stateorprovince',
                  m.getMetaData('ows_stateorprovince_{}'.format(l)))
    m.setMetaData('ows_keywordlist',
                  m.getMetaData('ows_keywordlist_{}'.format(l)))
    m.setMetaData('wcs_description',
                  m.getMetaData('wcs_description_{}'.format(l)))


def application(env, start_response):
    """WSGI application for WMS/WCS"""
    for key in MAPSERV_ENV:
        if key in env:
            os.environ[key] = env[key]
        else:
            os.unsetenv(key)

    layer = None
    mapfile_ = None

    request = mapscript.OWSRequest()
    request.loadParams()

    lang_ = request.getValueByName('LANG')
    service_ = request.getValueByName('SERVICE')
    request_ = request.getValueByName('REQUEST')
    layers_ = request.getValueByName('LAYERS')
    layer_ = request.getValueByName('LAYER')
    coverageid_ = request.getValueByName('COVERAGEID')
    format_ = request.getValueByName('FORMAT')

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
    if request_ == 'GetCapabilities' and layer is None:
        if service_ == 'WMS':
            filename = 'geomet-climate-WMS-1.3.0-capabilities-{}.xml'.format(
                lang)
            cached_caps = os.path.join(BASEDIR, 'mapfile', filename)
        elif service_ == 'WCS':
            filename = 'geomet-climate-WCS-2.0.1-capabilities-{}.xml'.format(
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
            metadata_lang(mapfile, lang)
            layerobj = mapfile.getLayerByName(layer)
            layerobj.setMetaData('ows_title',
                                 layerobj.getMetaData('ows_title_{}'.format(lang))) # noqa
            layerobj.setMetaData('ows_layer_group',
                                 layerobj.getMetaData('ows_layer_group_{}'.format(lang))) # noqa

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
