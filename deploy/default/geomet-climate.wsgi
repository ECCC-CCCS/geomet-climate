###############################################################################
#
# Copyright (C) 2020 Tom Kralidis
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

import os

os.environ['GEOMET_CLIMATE_BASEDIR'] = '/opt/geomet-climate'
os.environ['GEOMET_CLIMATE_DATADIR'] = '/data/geomet/feeds/dd/climate'
os.environ['GEOMET_CLIMATE_CONFIG'] = '/opt/geomet-climate/geomet-climate.yml'
os.environ['GEOMET_CLIMATE_URL'] = 'https://geo.wxod-dev-18-04.cmc.ec.gc.ca/geomet-climate'

from geomet_climate.wsgi import application
