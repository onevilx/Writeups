#!/bin/bash
docker rm -f web_regregious
docker build -t web_regregious . 
docker run --name=web_regregious --rm -p1337:1337 -it web_regregious
