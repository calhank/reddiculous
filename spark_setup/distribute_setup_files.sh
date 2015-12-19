#!/bin/bash -x

for host in "$@"; do
    ssh root@$host mkdir init
    scp *.{sh,diff} root@$host:init
done
