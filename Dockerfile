FROM ubuntu:jammy

# Allow for change during docker build-time
ARG GEOMET_CLIMATE_URL=https://geomet-dev-31-nightly.edc-mtl.ec.gc.ca/geomet-climate

ENV BASEDIR=/data/web/geomet-climate-nightly \
    DOCKERDIR=/data/web/geomet-climate-nightly/docker \
    GEOMET_CLIMATE_BASEDIR=/data/web/geomet-climate-nightly/build \
    GEOMET_CLIMATE_DATADIR=/data/geomet/feeds/dd/climate \
    GEOMET_CLIMATE_CONFIG=/data/web/geomet-climate-nightly/geomet-climate.yml \
    GEOMET_CLIMATE_URL=${GEOMET_CLIMATE_URL} \
    # GEOMET_CLIMATE_ES_USERNAME=foo
    # GEOMET_CLIMATE_ES_PASSWORD=bar
    # ES credentials loaded from host env
    GEOMET_CLIMATE_ES_URL=https://${GEOMET_CLIMATE_ES_USERNAME}:${GEOMET_CLIMATE_ES_PASSWORD}@localhost:9200 \
    GEOMET_CLIMATE_OWS_DEBUG=5 \
    MAPSERVER_CONFIG_FILE=${GEOMET_CLIMATE_BASEDIR}/mapserver.conf
    # GEOMET_CLIMATE_OWS_LOG=/tmp/geomet-climate-ows.log

WORKDIR $BASEDIR

# Install system dependencies
RUN apt update && apt install -y software-properties-common && \
    ## Add this WMO PPA
    add-apt-repository ppa:gcpp-kalxas/wmo-staging && apt update && \
    ## Install dependencies from debian/control
    apt install -y mapserver-bin python3-all python3-pip python3-click python3-gdal python3-mappyfile python3-mapscript python3-matplotlib python3-numpy python3-pyproj python3-yaml proj-bin proj-data python3-certifi && \
    # remove transient packages
    apt clean autoclean && apt autoremove --yes && rm -fr /var/lib/{apt,dpkg,cache,log}/

# Copy source code to base directory of container
COPY . $BASEDIR

# Install application dependencies
RUN pip3 install -r requirements.txt && \
    pip3 install -r requirements-dev.txt && \
    pip3 install -e . && \
    # add gunicorn for Docker deploy
    pip3 install gunicorn && \
    # Getting entrypoint to work
    touch $DOCKERDIR/entrypoint.sh && chmod 0755 $DOCKERDIR/entrypoint.sh

# Start MSC GeoMet Climate
ENTRYPOINT [ "sh", "-c", "$DOCKERDIR/entrypoint.sh" ]