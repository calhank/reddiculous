#!/bin/bash -x

for host in "$@"; do
    kw='automated provisioning system'
    ssh root@$host "perl -pe '\$kw=\"automated provisioning system\"; if (!(/\$kw/.../\$kw/)) { printf \"%s\", \"from=\\\"10.*\\\" \" }' ~/.ssh/authorized_keys"
done
