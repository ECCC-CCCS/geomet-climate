#!/bin/bash
# default env variables
BASEDIR=/data/web/geomet-climate-nightly
GEOMET_CLIMATE_BASEDIR=$BASEDIR/build
GEOMET_CLIMATE_ES_URL=${GEOMET_CLIMATE_ES_URL}
MAPSERVER_CONFIG_FILE=${MAPSERVER_CONFIG_FILE}
MS_MAP_PATTERN=$GEOMET_CLIMATE_BASEDIR/mapfile/.*

# replace localhost ES URL with docker-host URL to ES
if [ $GEOMET_CLIMATE_ES_URL != "" ]
then
    sed -i 's|http://localhost:9200|'$GEOMET_CLIMATE_ES_URL'|g' geomet-climate.yml
    sed -i 's|http://localhost:9200|'$GEOMET_CLIMATE_ES_URL'|g' tests/geomet-climate-test.yml
fi

cd $BASEDIR

# Ensure the directory for MAPSERVER_CONFIG_FILE exists
mkdir -p "$(dirname "$MAPSERVER_CONFIG_FILE")"

# Ensure MAPSERVER_CONFIG_FILE exists; create it if it doesn't
if [ ! -f "$MAPSERVER_CONFIG_FILE" ]; then
    cat > "$MAPSERVER_CONFIG_FILE" <<EOF
CONFIG
    ENV
        MS_MAP_PATTERN "$MS_MAP_PATTERN"
    END
END
EOF
    echo "MapServer config file created: $MAPSERVER_CONFIG_FILE"
else
    echo "MapServer config file already exists: $MAPSERVER_CONFIG_FILE"
fi

# Set appropriate permissions for the config file
chmod 644 "$MAPSERVER_CONFIG_FILE"

echo "Generating geomet-climate VRTs for all layers..."
geomet-climate vrt generate
echo "Generating geomet-climate tileindex for all layers..."
geomet-climate tileindex generate
echo "Generating geomet-climate legends for all layers..."
geomet-climate legend generate
echo "Generating geomet-climate mapfile for WMS..."
geomet-climate mapfile generate -s WMS
echo "Generating geomet-climate mapfile for WCS..."
geomet-climate mapfile generate -s WCS

echo "Caching WMS (English)..."
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-en.map&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WMS (French)..."
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-fr.map&lang=fr&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WCS (English)..."
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-en.map&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

echo "Caching WCS (French)..."
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-fr.map&lang=fr&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile




echo "Done."

# server runs
echo "Starting up geomet-climate via gunicorn..."
# geomet-climate serve --port=80
gunicorn -w 2 -b 0.0.0.0:8099 --chdir $BASEDIR/geomet_climate wsgi:application --reload --timeout 900 --access-logfile /tmp/gunicorn-geomet-climate.log