#!/bin/bash -x

. ./config.sh
hfile=`hosts_file "$hosts_filter"`

for host in "$@"; do
    echo "$hfile" | ssh root@$host "cat > /etc/hosts"
done
