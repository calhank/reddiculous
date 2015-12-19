#!/bin/bash -x

if ! [ -f id_ed25519 ]; then
    ssh-keygen -t ed25519 -P "" -f id_ed25519
fi
for host in "$@"; do
    ssh-copy-id -i id_ed25519.pub root@$host
    scp -p id_ed25519* root@$host:.ssh/
    ssh root@$host chmod -R go-rwx .ssh
done
