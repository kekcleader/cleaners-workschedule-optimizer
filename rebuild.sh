#!/bin/bash
docker rm cleaners
docker rmi img_cleaners
docker build -t img_cleaners .
./exec.sh
