# -*- coding: utf-8 -*-
# =================================================================
#
# Copyright (c) 2018 Government of Canada
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
# =================================================================

import argparse
from datetime import datetime
import logging
import os
import sys
import unittest
import isodate
import itertools

from PIL import Image, ImageChops, ImageStat, ImageColor
from io import BytesIO
from owslib.wms import WebMapService
import requests
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


LOGGER = logging.getLogger(__name__)
GENERAL_INFO_LEVEL_NUM = 60
logging.addLevelName(GENERAL_INFO_LEVEL_NUM, "\n - General Test Info")


def general_info(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    if self.isEnabledFor(GENERAL_INFO_LEVEL_NUM):
        self._log(GENERAL_INFO_LEVEL_NUM, message, args, **kws)


logging.Logger.general_info = general_info
TestSubSet = unittest.TestSuite()
yamltag = ''
getcapabilitytag = ''
URL = ''

timeformat = '%Y-%m-%dT%H:%M:%SZ'
# The following list of strings is used to avoid testing for an
# empty file for products containing those substrings
# We may want to not do that when we are more certain that
# the GetMap images we are requesting are supposed to be non empty
# e.g. by using a specific BBOX as a function of product
no_empty_check = ['_FR', '_RN', '_NT', '_PR', '_RT', '_SN',
                  '_PEMM', '_PRMM', '_FRMM', '_PRMM', '_RNMM',
                  '_SNMM', 'OCEAN', 'ETA_PN', 'HURRICANE']

# This is now a dict (used to be a list) so we can
# later choose which BBOX to check as a function of product
BBOXS = {'World': (-180, -90, 180, 90),
         'Canada': (-141, 42, -52, 84),
         'Alberta': (-120, 49, -110, 60),
         'British Columbia': (-139, 48, -114, 60),
         'Manitoba': (-102, 49, -89, 60),
         'New Brunswick': (-69, 45, -64, 48),
         'Newfoundland and Labrador': (-67.7, 47, -52, 60),
         'Northwest Territories': (-136.5, 60, -101.5, 79),
         'Nova Scotia': (-66.3, 43, -59.9, 47),
         'Nunavut': (-121, 52, -61, 84),
         'Ontario': (-95, 42, -74, 57),
         'Prince Edward Island': (-64.5, 45.9, -62, 47),
         'Québec': (-79.5, 45, -57, 63),
         'Saskatchewan': (-110, 49, -101.5, 60),
         'Yukon': (-141, 60, -123.8, 69.6)}

FORMAT = 'image/png'
SRS = 'EPSG:4326'


def datetime_generator(begin_dt, end_dt, time_interval):
    """Yield datetime objects between an initial and a final
    datetime for a specified time interval.

    :param begin_dt: initial datetime object
    :param end_dt: final datetime object
    :param time_interval: timedelta object (e.g. forecast_hour_interval)
    """
    from_date = begin_dt
    while from_date <= end_dt:
        yield from_date
        from_date = from_date + time_interval


def time_interval_to_csv_timestamps(time_interval_iso_string):
    '''Takes an ISO 8601 time interval (t_begin/t_end/period) and retruns
    a list of comma separated timestamps.'''

    datetime_list = []
    str_list = time_interval_iso_string.split('/')
    begin_dt = isodate.parse_datetime(str_list[0])
    end_dt = isodate.parse_datetime(str_list[1])
    int_dt = isodate.parse_duration(str_list[2])
    timespan = end_dt - begin_dt
    # We can't divide timedeltas so we need to express them in seconds before
    nb_intervals = int(timespan.total_seconds() / int_dt.total_seconds())
    it = itertools.islice(datetime_generator(begin_dt,
                                             end_dt,
                                             int_dt),
                          nb_intervals + 1)
    datetime_list = list(it)
    csv_list = [isodate.datetime_isoformat(dt) for dt in datetime_list]

    return csv_list


def images_equal(im1, im2):
    '''If im1 and im2 (pngs returned by GetMap) are the same,
    resulting diff bbox is None so returns True
    '''
    return ImageChops.difference(im1, im2).getbbox() is None


def image_empty(im, bgcolor=None):
    '''Takes an image and an optional background color
    in hex format (e.g. #FF0000).
    If im has a single pixel value different from bgcolor if
    any supplied, it is empty.
    '''

    # If an image has uniform values, then standard deviation
    # will be zero, in which case we check if that value != bgcolor if any
    stat = ImageStat.Stat(im)
    bands = stat.extrema

    if im.mode == 'P' or im.mode == 'L':
        image_rgb = (bands[0][0])
    else:
        image_rgb = (bands[0][0], bands[1][0], bands[2][0])

    if bgcolor:
        bgcolor_rgb = ImageColor.getcolor(bgcolor.replace('0x', '#'), 'RGB')
        if sum(ImageStat.Stat(im).stddev) == 0 and image_rgb != bgcolor_rgb:
            err_str = ("Constant pixel value of " + str(image_rgb)
                       + "; Background color for NODATA = "
                       + str(bgcolor)
                       + " (RGB = " + str(bgcolor_rgb) + ")")
            return {'is_empty': True, 'error_string': err_str}
        else:
            return {'is_empty': False}
    else:
        if sum(ImageStat.Stat(im).stddev) == 0:
            err_str = "Constant pixel value of " + str(image_rgb)
            return {'is_empty': True, 'error_string': err_str}
        else:
            return {'is_empty': False}


def msg(test_id, test_description):
    """convenience function to print out test id and desc"""
    return '{}: {}'.format(test_id, test_description)


def format_time_diff(s, timeformat):
    """format time difference"""

    src_time = datetime.strptime(s, timeformat)
    now = datetime.now()

    diff = now - src_time

    days = diff.days
    hours = diff.seconds / 3600
    minutes = diff.seconds % 3600 / 60
    seconds = diff.seconds % 60

    if days > 0:
        return '{} {} {} {}'.format(days, hours, minutes, seconds)
    elif hours > 0:
        return '{} {} {}'.format(hours, minutes, seconds)
    elif minutes > 0:
        return '{} {}'.format(minutes, seconds)
    else:
        return '{}' .format(seconds)


def _write_response_to_disk(filepath, data):
    """convenience function to write test result to file on disk"""

    with open(filepath, 'wb') as ff:
        ff.write(data)


def check_arg(args=None):
    """process mainline arguments"""

    class uclist(list):
        """list subclass that uppercases list members"""
        def __contains__(self, other):
            """overload"""
            return super(uclist, self).__contains__(other.upper())

    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--output-dir',
                        help='Specify output directory where '
                             'to write results (mostly png files); '
                             'default = none')
    parser.add_argument('--loglevel',
                        help='logging level (CRITICAL, '
                             'ERROR, WARNING, INFO, DEBUG)',
                        default='ERROR',
                        choices=uclist(['CRITICAL',
                                        'ERROR',
                                        'WARNING',
                                        'INFO',
                                        'DEBUG']))
    parser.add_argument('--test-subset',
                        help='Specify the test subset you want to run ',
                        default='Default')
    parser.add_argument('--yaml-path',
                        help='Specify the yaml to use for the tests',
                        default='Default')

    results = parser.parse_args(args)
    return (results.url,
            results.output_dir,
            results.loglevel.upper(),
            results.test_subset,
            results.yaml_path)


def get_directory_size(directory):
    total_size = os.path.getsize(directory)
    for item in os.listdir(directory):
        itempath = os.path.join(directory, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += get_directory_size(itempath)
    return total_size


def CreateTestSubSet(TestSuite):

    # Definition of all the test running for each subset,
    # tried to make a list but apparently
    # the lib is limited in terms of capabilities.
    if TestSuite == 'nightly':
        TestSubSet.addTest(GeoMetTest('test_geomet_service_online'))
        TestSubSet.addTest(GeoMetTest('test_bad_layer_request'))
        TestSubSet.addTest(GeoMetTest('test_layers_availability'))
        TestSubSet.addTest(GeoMetTest('test_legends_availability'))
        TestSubSet.addTest(GeoMetTest('test_styles_availability'))
        TestSubSet.addTest(GeoMetTest('test_time_'
                                      'enabled_yaml_getcapabilities'))
        TestSubSet.addTest(GeoMetTest('test_request_with_time'))
    elif TestSuite == 'dev':
        TestSubSet.addTest(GeoMetTest('test_layers_'
                                      'availability_geomet_climate'))
    elif TestSuite == 'ops':
        TestSubSet.addTest(GeoMetTest('test_layers_'
                                      'availability_geomet_climate'))
    elif TestSuite == 'beta':
        TestSubSet.addTest(GeoMetTest('test_layers_availability'))
    elif TestSuite == 'stage':
        TestSubSet(GeoMetTest('test_layers_availability'))
    elif TestSuite == 'default':
        TestSubSet.addTest(GeoMetTest('test_geomet_service_online'))
        TestSubSet.addTest(GeoMetTest('test_bad_layer_request'))
        TestSubSet.addTest(GeoMetTest('test_layers_availability'))
        TestSubSet.addTest(GeoMetTest('test_legends_availability'))
        TestSubSet.addTest(GeoMetTest('test_styles_availability'))
        TestSubSet.addTest(GeoMetTest('test_time_'
                                      'enabled_yaml_getcapabilities'))
        TestSubSet.addTest(GeoMetTest('test_request_with_time'))
    else:
        print('No test were run, subset test name invalid')


class GeoMetTest(unittest.TestCase):
    """GeoMet test suite"""
    def setUp(self):
        """setup test fixtures, etc."""

        self.headers = {
            'User-Agent': 'GeoMet integration tests'
        }

        self.sizeheight = 1080
        self.sizewidth = 1920
        self.maxDiff = None
        self.wms_missing_layers = 0

        self.layer_time_error_count = 0
        self.modelrun_error_count = 0
        self.getlegend_error_count = 0
        self.getlegend_empty_error_count = 0
        self.getstyle_error_count = 0
        self.gettime_enabled_error_count = 0
        self.getmap_error_time_request_count = 0
        self.image_warning_count = 0

        self.wms = WebMapService('http://geomet2-nightly.cmc.ec.gc.ca/'
                                 'geomet-climate',
                                 version='1.3.0',
                                 timeout=300)
        geomet_climate_yml = self.yaml

        with open(geomet_climate_yml) as ff:
            self.config = load(ff, Loader=Loader)

        print('{} {}'.format(self.id(), self.shortDescription()))

    def tearDown(self):
        """return to pristine state, currently useless"""
        # self.assertEqual([], self.miscellaneous_errors)
        # self.assertEqual([], self.getmap_errors)

    def test_geomet_service_online(self):
        # Test Geomet Service Online : Simple Test
        # with a generic client to make sure the service is online

        # Make a basic request at : http://geomet2-nightly.cmc.ec.gc.ca/geomet
        response = requests.get(self.url, headers=self.headers)
        try:
            # Validate that the request returned an OK code (HTTP 200)
            self.assertEquals(response.status_code, 200, 'Expected HTTP 200')
        except AssertionError:
            # If the request didnt return a HTTP 200, log an error
            LOGGER.error('Geomet-Climate Service Online Failed : '
                         'request issued : \n{}'.format(self.wms.request))

    def test_bad_layer_request(self):
        # Test Bad Layer Request :
        # Make a bad layer request to validate an exception is thrown

        try:
            self.wms.getmap(layers=['some-bad-layername'],
                            srs=SRS,
                            bbox=[-90, -180, 90, 180],
                            size=(self.sizewidth, self.sizeheight),
                            format=FORMAT,
                            transparent=True)
            LOGGER.error('Bad Layer Request Failed : '
                         'Should have return an exception')

        except Exception:
            pass

    def test_layers_availability(self):
        # Test Layer Availability :
        # Ensure all layers in configuration are in WMS

        # Find all the layer present in
        # the yaml file and not in GetCapabilities
        self.wms_missing_layers = list(set(self.config['layers'].keys())
                                       - set(self.wms.contents.keys()))

        # Log all the missing layers as errors
        if self.wms_missing_layers:
            self.layer_time_error_count += 1
            LOGGER.error('Layers Availability Failed : '
                         'WMS missing layers from YAML configuration: '
                         '{}'.format(self.wms_missing_layers))

    def test_legends_availability(self):
        # Test Legends Availability :
        # Ensure all layer legends show up and are not empty

        # COULD BE MODIFIED TO NOT TEST SAME LEGEND MULTIPLES TIMES

        num_layers = 0
        skip_layers = ['CURRENT_CONDITIONS']

        # Loop through all the layers
        for key, layer in self.wms.contents.items():

            if layer.parent is not None:  # leaf layer
                # Loop through all the styles in each layer
                for style in layer.styles.values():
                    num_layers += 1
                    try:
                        # Try a request for the legend actualy validated
                        res = requests.get(style['legend'])
                    except Exception:
                        # Log error if the legend request failed
                        self.getlegend_error_count += 1
                        LOGGER.error('Legends Availability Failed : '
                                     'GetLegendGraphic request failed on '
                                     'request : \n{}'.format(res.url))

                    # If want to skip the actual layer...
                    if key not in skip_layers:
                        img = Image.open(BytesIO(res.content))
                        is_empty = image_empty(img)
                        if ('Content-Length' in res.headers and
                           res.headers['Content-Length'] == 0) or \
                           is_empty['is_empty']:
                            self.getlegend_empty_error_count += 1
                            LOGGER.warning('Legends Availability Warning : '
                                           'Empty content response or empty '
                                           'image with request '
                                           ': \n{}'.format(res.url))

    def test_styles_availability(self):
        # Test Styles Availability : Perform a test to
        # make sure all styles are available

        # List of all the style already tested
        list_layer_evaluated = []

        # Loop through all the layers
        for key, layer in self.wms.contents.items():
            # Loop through all the styles
            for style in layer.styles.keys():
                # Validate if the actual style has already been checked
                if style not in list_layer_evaluated:
                    # Add the style in the validated style
                    list_layer_evaluated.append(style)
                    try:
                        # Try to make a request with the evaluated style
                        res = self.wms.getmap(layers=[key], styles=[style],
                                              srs=SRS,
                                              bbox=[-90, -180, 90, 180],
                                              size=(self.sizewidth,
                                                    self.sizeheight),
                                              format=FORMAT,
                                              transparent=True)
                    except Exception:
                        # Log an error if the request failed
                        self.getstyle_error_count += 1
                        LOGGER.error('tyle Availability Failed : Style '
                                     + style
                                     + ' is unavailable, Style '
                                     'was tested with layer ' + key)
                        LOGGER.error('Failed request : '
                                     '{}'.format(self.wms.request))

                    # Validate if the image returned by
                    # the request is empty or not
                    img = Image.open(res)
                    is_empty = image_empty(img)

                    # If the image is empty : log a warning since some
                    # style might return blank images if no
                    # data is available (ex : FreezingRain or HURRICANE)
                    if is_empty['is_empty']:
                        LOGGER.warning('Style Availability warning : '
                                       + style
                                       + ' is available but the returning '
                                       'image is empty with layer : ' + key)
                        LOGGER.warning('Failed request : '
                                       '{}'.format(self.wms.request))

    def test_time_enabled_yaml_getcapabilities(self):
        # Test Time Enabled Yaml GetCapabilities :
        # Perform a test that make sure all layer in the yaml with
        # time_enabled has a time dimemsion in the GetCapabilities

        # Declare dictionary that will hold the yaml and GetCapabilities layers
        yaml_layers_dict = {}
        getcapa_dict = {}
        yml = self.config['layers'].keys()

        # Get all layers and indicate if the layer has
        # time_enabled or not (time_enabled can be : No, Yes, Future)
        for key in yml:
            try:
                if self.config['layers'][key]['timestep']:
                    yaml_layers_dict.update({key: True})
            except Exception:
                yaml_layers_dict.update({key: False})

        # Get all layers and indicate if the layer has a time
        # dimension or not (The tags isnt there is time_enabled is 'no')
        for key, layer in self.wms.contents.items():
            if layer.dimensions.keys():
                getcapa_dict.update({key: True})
            else:
                getcapa_dict.update({key: False})

        # Compare yaml and GetCapabilities, log an error
        # on a time_enabled missmatch for a layer
        for key in yaml_layers_dict:
            if yaml_layers_dict.get(key) != getcapa_dict.get(key):
                self.gettime_enabled_error_count += 1
                LOGGER.error('Time Enabled Error : Layer '
                             + key
                             + ' YAML Time enabled setup to : '
                             + str(yaml_layers_dict.get(key))
                             + ' and GetCapabilities Time '
                             'Dimension setup to : '
                             + str(getcapa_dict.get(key)))

    def test_request_with_time(self):
        # Test Request With Time : Perform GetMap requests
        # with a time parameter to make sure those are supported

        list_group_evaluated = []
        group = ''

        # Loop through all the layers
        for key, layer in self.wms.contents.items():
            group = key.split('.')
            # Only test one layer per group
            if group[0] not in list_group_evaluated:
                list_group_evaluated.append(group[0])
                # if timeposition available, get first and last time
                if layer.timepositions:  # set start/end times list
                    times = layer.timepositions[0].split('/')[:2]
                    try:
                        # Request layer with time = last time available
                        self.wms.getmap(layers=[key], styles=[''],
                                        srs=SRS,
                                        bbox=[-180, -90, 180, 90],
                                        size=(self.sizewidth,
                                              self.sizeheight),
                                        format=FORMAT,
                                        transparent=True,
                                        time=times[1]).read()
                    # If request failed, log error as time_request failed
                    except Exception as err:
                        self.getmap_error_time_request_count += 1
                        LOGGER.error('Request With Time Failed : Layer '
                                     + key
                                     + ' failed with a time request:'
                                     '{}').format(err)
                        LOGGER.error(self.wms.request)


if __name__ == '__main__':
    URL, OUTPUT_DIR, LOGLEVEL, TESTSUBSET, YAML = check_arg(sys.argv[1:])
    URL = URL.rstrip('/')
    print('URL : {}'.format(URL))
    print('Output directory : {}'.format(OUTPUT_DIR))
    print('Logging level : {}'.format(LOGLEVEL))
    print('Test Subset : {}'.format(TESTSUBSET))
    print('Yaml used : {}'.format(YAML))
    print('Launch time : {}'.format(datetime.utcnow()))
    print('---------------------------------------------------------------')

    if URL == 'http://geo.weather.gc.ca/geomet':
        print('Detected production instance.  Exiting')
        sys.exit(2)

    GeoMetTest.output_dir = OUTPUT_DIR
    GeoMetTest.url = URL
    GeoMetTest.yaml = YAML

    if LOGLEVEL is not None:
        LOGGING_LEVEL = getattr(logging, LOGLEVEL)
        LOGGER.setLevel(LOGGING_LEVEL)
        CH = logging.StreamHandler(sys.stdout)
        CH.setLevel(LOGGING_LEVEL)
        FORMATTER = logging.Formatter('%(levelname)s - %(message)s')
        CH.setFormatter(FORMATTER)
        LOGGER.addHandler(CH)

    # Without next line unittest.main() will fail with AttributeError:
    # 'module' object has no attribute 'http://...'
    sys.argv = [sys.argv[0]]
    # Create a sub set of test depending of the command param
    CreateTestSubSet(TESTSUBSET)
    # Run the test sub set created
    unittest.TextTestRunner().run(TestSubSet)
