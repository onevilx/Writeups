#!/bin/bash
docker build -t web_sitelytic .
docker run --name=web_sitelytic --rm -p1337:80 -it web_sitelytic
