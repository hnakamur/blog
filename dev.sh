#!/bin/sh
ip=$(hostname -I | awk '{print $1}')
hugo server -D --bind 0.0.0.0 --baseURL http://$ip:1313/blog/
