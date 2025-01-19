#!/bin/bash
docker rm cleaners >/dev/null 2>/dev/null
docker run -p 8080:5000 -v ./program:/program --name cleaners img_cleaners
