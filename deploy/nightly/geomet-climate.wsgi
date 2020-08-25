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
import sys

os.environ['GEOMET_CLIMATE_BASEDIR'] = '/data/web/geomet-climate-nightly/latest/geomet-climate/_build'
os.environ['GEOMET_CLIMATE_DATADIR'] = '/data/geomet/dev/feeds/amqp/climate'
os.environ['GEOMET_CLIMATE_CONFIG'] = '/data/web/geomet-climate-nightly/latest/geomet-climate/geomet-climate.yml'
os.environ['GEOMET_CLIMATE_URL'] = 'http://geomet-dev-03-nightly.cmc.ec.gc.ca/msc-pygeoapi/nightly/latest/'

sys.path.insert(0, '/data/web/geomet-climate-nightly/latest/lib/python3.6/site-packages')

from geomet_climate.wsgi import application
