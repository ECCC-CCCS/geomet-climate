###############################################################################
#
# Copyright (C) 2018 Louis-Philippe Rousseau-Lambert
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
import io
import json
import mock
import os
import unittest

import yaml

from geomet_climate.vrt import (create_vrt,
                                generate_vrt_list)

from geomet_climate.tileindex import (generate_vrt_list as tileindex_list,
                                      get_time_index_novrt,
                                      get_time_index_vrt,
                                      create_dataset)

from geomet_climate.mapfile import (gen_web_metadata,
                                    gen_layer_metadataurl,
                                    gen_layer)

THISDIR = os.path.dirname(os.path.realpath(__file__))


def msg(test_id, test_description):
    """convenience function to print out test id and desc"""
    return '{}: {}'.format(test_id, test_description)


class GeoMetClimateTest(unittest.TestCase):
    """Test suite for package geomet-climate"""
    data_dir = os.path.join(THISDIR, 'data/climate')
    yml_file = os.path.join(THISDIR, 'geomet-climate-test.yml')

    mock.patch('os.environ', {'BASEDIR': THISDIR,
                              'CONFIG': yml_file,
                              'DATADIR': data_dir})
    with io.open(yml_file) as fh:
        cfg = yaml.load(fh)

    def setUp(self):
        """setup test fixtures, etc."""

        print(msg(self.id(), self.shortDescription()))

    def tearDown(self):
        """return to pristine state"""

        pass

    def test_create_vrt(self):
        """This function is called when we need to create a VRT"""

        out_file = os.path.join(self.data_dir,
                                'cangrd/geotiff/historical/seasonal/JJA/',
                                'anomaly/CANGRD_hist_JJA_anom_ps50km_TMAX.vrt')
        if os.path.isfile(out_file):
            os.remove(out_file)
        layer_info = self.cfg['layers']['CANGRD.ANO.TX_SUMMER']
        vrt_list = ['CANGRD_hist_JJA_anom_ps50km_TMAX_2002.tif',
                    'CANGRD_hist_JJA_anom_ps50km_TMAX_1983.tif',
                    'CANGRD_hist_JJA_anom_ps50km_TMAX_1917.tif',
                    'CANGRD_hist_JJA_anom_ps50km_TMAX_2017.tif']
        vrt_name = 'CANGRD_hist_JJA_anom_ps50km_TMAX.vrt'

        create_vrt(layer_info, vrt_list, self.data_dir, vrt_name)

        self.assertTrue(os.path.isfile(out_file))

    def test_generate_vrt_list_case1(self):
        """This test creates a VRT file per file band"""

        out_file = os.path.join(self.data_dir,
                                'cangrd/geotiff/historical',
                                'monthly_ens/anomaly/',
                                'CANGRD_hist_monthly_anom_ps50km_PCP.vrt')
        if os.path.isfile(out_file):
            os.remove(out_file)
        layer_info = self.cfg['layers']['CANGRD.ANO.PR_MONTHLY']
        generate_vrt_list(layer_info, self.data_dir)

        self.assertTrue(os.path.isfile(out_file))

    def test_generate_vrt_list_case2(self):
        """This test should NOT create a VRT"""
        var = 'CMIP5_hist_MAM_anom_latlon1x1_SICECONC_pctl95_P1Y.vrt'
        out_file = os.path.join(self.data_dir,
                                'cmip5/netcdf/historical',
                                'seasonal/MAM/anomaly/',
                                var)
        if os.path.isfile(out_file):
            os.remove(out_file)
        layer_info = self.cfg['layers']['CMIP5.SIC.HISTO.SPRING.ANO_PCTL95']
        generate_vrt_list(layer_info, self.data_dir)

        self.assertFalse(os.path.isfile(out_file))

    def test_tileindex_list(self):
        """Validate the VRT list name for tilindexing"""
        layer_name = 'CMIP5.SIC.HISTO.SPRING.ANO_PCTL95'
        layer_info = self.cfg['layers'][layer_name]
        vrt_name = 'CMIP5_hist_MAM_anom_latlon1x1_SICECONC_pctl95_P1Y'

        result = tileindex_list(layer_info)

        self.assertTrue(result[-1] == '{}{}'.format(vrt_name, '_106.vrt'))
        self.assertTrue(result[0] == '{}{}'.format(vrt_name, '_1.vrt'))
        self.assertTrue(result[59] == '{}{}'.format(vrt_name, '_60.vrt'))

    def test_get_time_index_novrt(self):
        """Assign the right date to a file (no VRT)"""
        layer_name = 'CANGRD.ANO.PR_MONTHLY'
        layer_info = self.cfg['layers'][layer_name]
        tif_name = 'CANGRD_hist_monthly_anom_ps50km_PCP'

        result = get_time_index_novrt(layer_info)

        self.assertEqual(result['{}{}'.format(tif_name, '_1929-05.tif')],
                         '1929-05')

    def test_get_time_index_vrt(self):
        """Assign the right date to a file (with VRT)"""
        layer_name = 'CMIP5.SIT.RCP45.YEAR.ANO_PCTL50'
        layer_info = self.cfg['layers'][layer_name]
        vrt_name = 'CMIP5_rcp4.5_annual_anom_latlon1x1_SICETHKN_pctl50_P1Y'

        result = get_time_index_vrt(layer_info)

        self.assertEqual(result['{}{}'.format(vrt_name, '_95.vrt')],
                         '2100')
        self.assertEqual(result['{}{}'.format(vrt_name, '_1.vrt')],
                         '2006')
        self.assertEqual(result['{}{}'.format(vrt_name, '_63.vrt')],
                         '2068')

    def test_create_dataset_no_raster(self):
        """Should not create a GPKG (Vector layer)"""
        layer_name = 'CLIMATE.STATIONS'
        layer_info = self.cfg['layers'][layer_name]

        result = create_dataset(layer_info, self.data_dir, self.data_dir)

        self.assertIsNone(result)

    def test_create_dataset_raster_no_time(self):
        """Should not create a GPKG (not a time enabled layer)"""
        layer_name = 'DCS.TM.RCP85.YEAR.2041-2060_PCTL50'
        layer_info = self.cfg['layers'][layer_name]

        result = create_dataset(layer_info, self.data_dir, self.data_dir)

        self.assertIsNone(result)

    def test_create_dataset_raster_Bands(self):
        """Should create a GPKG (from a layer with multiple bands)"""
        layer_name = 'CMIP5.SIT.RCP45.YEAR.ANO_PCTL50'
        var = 'CMIP5_rcp4.5_annual_anom_latlon1x1_SICETHKN_pctl50_P1Y.gpkg'
        out_file = os.path.join(self.data_dir,
                                'cmip5/netcdf/scenarios',
                                'RCP4.5/annual/anomaly/',
                                var)
        if os.path.isfile(out_file):
            os.remove(out_file)
        layer_info = self.cfg['layers'][layer_name]

        create_dataset(layer_info, self.data_dir, self.data_dir)

        self.assertTrue(os.path.isfile(out_file))

    def test_create_dataset_raster_1Band(self):
        """Should create a GPKG (from a layer with 1 band files)"""
        layer_name = 'CANGRD.ANO.TX_SUMMER'
        var = 'CANGRD_hist_JJA_anom_ps50km_TMAX.gpkg'
        out_file = os.path.join(self.data_dir,
                                'cangrd/geotiff/historical',
                                'seasonal/JJA/anomaly/',
                                var)
        if os.path.isfile(out_file):
            os.remove(out_file)
        layer_info = self.cfg['layers'][layer_name]

        create_dataset(layer_info, self.data_dir, self.data_dir)

        self.assertTrue(os.path.isfile(out_file))

    def test_gen_web_metadata(self):
        """test mapfile MAP.WEB.METADATA section creation (En)"""
        url = 'https://fake.url/geomet-climate'
        mapfile = os.path.join(THISDIR,
                               '../geomet_climate/resources/mapfile-base.json')
        with io.open(mapfile) as fh:
            m = json.load(fh, object_pairs_hook=OrderedDict)
        c = self.cfg['metadata']
        services = ['wms', 'wcs']

        for service in services:
            result = gen_web_metadata(m, c, service, url)
            self.assertTrue(result['ows_extent'] == '-141,42,-52,84')
            self.assertTrue(result['ows_stateorprovince'] == 'Quebec')
            self.assertTrue(result['ows_country'] == 'Canada')
            self.assertTrue(result['ows_contactinstructions'] ==
                            'During hours of service')
            self.assertTrue(result['ows_contactinstructions_fr'] ==
                            'Durant les heures de service')

    def test_gen_layer_metadataurl(self):
        """create the metadata url based on some information in the yaml"""
        layer_name = 'CANGRD.TREND.TM_ANNUAL'
        layer_info = self.cfg['layers'][layer_name]

        result = gen_layer_metadataurl(layer_name, layer_info)
        self.assertTrue(result['ows_metadataurl_format'] == 'text/xml')
        self.assertTrue(result['ows_metadataurl_type'] == 'ISO 19115:2003')
        self.assertTrue(result['ows_metadataurl_href'] == 'https://csw.open.'
                                                          'canada.ca/'
                                                          'geonetwork'
                                                          '/srv/csw?service='
                                                          'CSW&version=2.0.2'
                                                          '&request='
                                                          'GetRecordById'
                                                          '&outputschema=csw'
                                                          ':IsoRecord&'
                                                          'elementsetname='
                                                          'full&id=23563e04-'
                                                          '467a-496f-a71c-'
                                                          'fb0aad0171a8')

    def test_gen_layer(self):
        """returns a list of mappyfile layer objects of layer (En)"""
        layer_name = 'CMIP5.TT.RCP26.SPRING.2021-2040_PCTL50'
        layer_info = self.cfg['layers'][layer_name]
        template_path = '/foo/bar/path'
        ows_title_en = 'CMIP5 (Spring)- Projected average change in Air' \
                       ' Temperature for 2021-2040 (50th percentile)'
        ows_layer_group_en = '/CMIP5-based climate scenarios (CMIP5)' \
                             '/Air temperature/RCP 2.6/Spring/2021-2040'
        ows_title_fr = u"CMIP5 (printemps)- Changement moyen projet\xe9 de " \
                       u"la temp\xe9rature de l'air pour 2021 \xe0 2040 " \
                       u"(50e percentile)"
        ows_layer_group_fr = u"/Sc\xe9narios climatiques fond\xe9s sur " \
                             u"CMIP5 (CMIP5)/Temp\xe9rature de l'air/" \
                             u"RCP 2.6/Printemps/2021 \xe0 2040"

        result = gen_layer(layer_name, layer_info,
                           template_path, service='WMS')

        self.assertTrue(result[0]['projection'] == ['+proj=longlat'
                                                    ' +datum=WGS84 +no_defs'])
        self.assertTrue(result[0]['name'] == 'CMIP5.TT.RCP26.SPRING.'
                                             '2021-2040_PCTL50')
        self.assertTrue(result[0]['data'] == ['tests/data/climate/'
                                              'cmip5/netcdf/scenarios/RCP2.6/'
                                              'seasonal/MAM/avg_20years/'
                                              'CMIP5_rcp2.6_MAM_2021-2040_'
                                              'latlon1x1_TEMP_pctl50_P1Y.nc'])
        self.assertTrue(result[0]['metadata']['ows_title'] == ows_title_en)
        self.assertTrue(result[0]['metadata']['ows_layer_group'] ==
                        ows_layer_group_en)
        self.assertTrue(result[0]['metadata']['ows_title_fr'] == ows_title_fr)
        self.assertTrue(result[0]['metadata']['ows_layer_group_fr'] ==
                        ows_layer_group_fr)


if __name__ == '__main__':
    unittest.main()
