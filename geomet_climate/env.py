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


LOGGER = logging.getLogger(__name__)

LOGGER.info('Fetching environment variables')

BASEDIR = os.environ.get('GEOMET_CLIMATE_BASEDIR', None)
CONFIG = os.environ.get('GEOMET_CLIMATE_CONFIG', None)
DATADIR = os.environ.get('GEOMET_CLIMATE_DATADIR', None)
OWS_DEBUG = os.environ.get('GEOMET_CLIMATE_OWS_DEBUG', None)
OWS_LOG = os.environ.get('GEOMET_CLIMATE_OWS_LOG', None)
URL = os.environ.get('GEOMET_CLIMATE_URL', None)

LOGGER.debug(BASEDIR)
LOGGER.debug(CONFIG)
LOGGER.debug(DATADIR)
LOGGER.debug(OWS_LOG)
LOGGER.debug(OWS_DEBUG)
LOGGER.debug(URL)

if None in [BASEDIR, CONFIG, DATADIR, URL]:
    msg = 'Environment variables not set!'
    LOGGER.exception(msg)
    raise EnvironmentError(msg)
