#!/bin/bash
# =================================================================
#
# Copyright (c) 2020 Government of Canada
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

BASEDIR=/data/web/geomet-climate-nightly
GEOMET_CLIMATE_GITREPO=https://github.com/ECCC-CCCS/geomet-climate.git
DAYSTOKEEP=7

# you should be okay from here

DATETIME=`date +%Y%m%d`
TIMESTAMP=`date +%Y%m%d.%H%M`
NIGHTLYDIR=geomet-climate-$TIMESTAMP

echo "Deleting nightly builds > $DAYSTOKEEP days old"

cd $BASEDIR

for f in `find . -type d -name "geomet-climate-20*"`
do
    DATETIME2=`echo $f | awk -F- '{print $3}' | awk -F. '{print $1}'`
    let DIFF=(`date +%s -d $DATETIME`-`date +%s -d $DATETIME2`)/86400
    if [ $DIFF -gt $DAYSTOKEEP ]; then
        rm -fr $f
    fi
done

rm -fr latest
echo "Generating nightly build for $TIMESTAMP"
python3 -m venv --system-site-packages $NIGHTLYDIR && cd $NIGHTLYDIR
source bin/activate
git clone $GEOMET_CLIMATE_GITREPO
cd geomet-climate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
export GEOMET_CLIMATE_BASEDIR=/data/web/geomet-climate-nightly/$NIGHTLYDIR/geomet-climate/_build
export GEOMET_CLIMATE_DATADIR=/data/geomet/feeds/dd.ops/climate
export GEOMET_CLIMATE_CONFIG=/data/web/geomet-climate-nightly/$NIGHTLYDIR/geomet-climate/geomet-climate.yml
export GEOMET_CLIMATE_URL=http://geomet-dev-03-nightly.cmc.ec.gc.ca/geomet-climate/nightly/latest
geomet-climate vrt generate
geomet-climate tileindex generate
geomet-climate legend generate
geomet-climate mapfile generate -s WMS
geomet-climate mapfile generate -s WCS

echo "Caching WMS (English)"
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-en.map&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WMS (French)"
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-fr.map&lang=fr&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WCS (English)"
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-en.map&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WCS (French)"
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-fr.map&lang=fr&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile

cd ../..

ln -s $NIGHTLYDIR latest
