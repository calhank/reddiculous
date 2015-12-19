#!/bin/bash -x

for host in "$@"; do
    ssh root@$host 'cd init && ./setup.sh' &
done
wait
