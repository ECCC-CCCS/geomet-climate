# geomet-climate

[![Build Status](https://travis-ci.org/ECCC-CCCS/geomet-climate.png)](https://travis-ci.org/ECCC-CCCS/geomet-climate)

## Overview

geomet-climate provides the MapServer setup and configuration for deployment
of MSC GeoMet climate service data OGC Web Services.

## Installation

### Dependencies

- Python MapScript
- GDAL Python bindings

### Requirements
- Python 2.7 (works with Python 3)
- [virtualenv](https://virtualenv.pypa.io/)

### Dependencies
Dependencies are listed in [requirements.txt](requirements.txt). Dependencies
are automatically installed during installation.

### Installing geomet-climate
```bash

# install system wide packages
sudo apt-get install python-mapscript python-gdal

# setup virtualenv
virtualenv geomet-climate
cd geomet-climate
. bin/activate

# clone codebase and install
git clone https://github.com/ECCC-CCCS/geomet-climate.git
cd geomet-climate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# configure environment
vi geomet-climate.env  # edit paths accordingly
. geomet-climate.env
```

## Running

```bash
# help
geomet-climate --help

# get version
geomet-climate --version

# generate VRTs for all layers
geomet-climate vrt generate

# generate VRTs for single layer
geomet-climate vrt generate --layer=CMIP5.SND.RCP26.FALL.ANO_PCTL50

# generate tileindex for all layers
geomet-climate tileindex generate

# generate tileindex for single layer
geomet-climate tileindex generate --layer=CMIP5.SND.RCP26.FALL.ANO_PCTL50

# generate mapfile for WMS (English)
geomet-climate mapfile generate --language=en --service=WMS

# generate mapfile for WMS (English) with specific configuration for single layer
geomet-climate mapfile generate --language=en --service=WMS --layer=CMIP5.SND.RCP26.FALL.ANO_PCTL50

# generate mapfile for WCS (French)
geomet-climate mapfile generate --language=fr --service=WCS

# run server
geomet-climate serve  # server runs on port 8099

# run server on a different port
geomet-climate serve  --port=8011

# cache WMS and WCS Capabilities URLs
mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-en.map&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WMS-fr.map&lang=fr&service=WMS&version=1.3.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WMS-1.3.0-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile

mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-en.map&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-en.xml $GEOMET_CLIMATE_BASEDIR/mapfile

mapserv -nh QUERY_STRING="map=$GEOMET_CLIMATE_BASEDIR/mapfile/geomet-climate-WCS-fr.map&lang=fr&service=WCS&version=2.1.0&request=GetCapabilities" > $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml && mv -f $GEOMET_CLIMATE_BASEDIR/geomet-climate-WCS-2.0.1-capabilities-fr.xml $GEOMET_CLIMATE_BASEDIR/mapfile
```

## Development

### Running Tests

```bash
. test/geomet-climate-test.env
python setup.py test
```

### Cleaning the build of artifacts
```bash
python setup.py cleanbuild
```

## Releasing

```bash
python setup.py sdist bdist_wheel --universal
twine upload dist/*
```

### Code Conventions

* [PEP8](https://www.python.org/dev/peps/pep-0008)

### Bugs and Issues

All bugs, enhancements and issues are managed on [GitHub](https://github.com/ECCC-CCCS/geomet-climate).

## Contact

* [Tom Kralidis](https://github.com/tomkralidis)
