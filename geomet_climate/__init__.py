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

__version__ = '1.4.0'

import click

from geomet_climate.mapfile import mapfile
from geomet_climate.tileindex import tileindex
from geomet_climate.vrt import vrt
from geomet_climate.wsgi import serve


@click.group()
@click.version_option(version=__version__)
def cli():
    pass


cli.add_command(mapfile)
cli.add_command(vrt)
cli.add_command(tileindex)
cli.add_command(serve)
