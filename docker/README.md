# Docker setup

```bash
# build Docker image
docker build -t eccc-msc/geomet-climate:nightly .
# (recommended) build Docker image via docker compose
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml build
# startup MSC GeoMet Climate
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d

# test WMS endpoint
curl "http://geomet-dev-11.cmc.ec.gc.ca:8099/?service=WMS&version=1.3.0&request=GetCapabilities"
```
