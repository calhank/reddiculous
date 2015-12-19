#!/bin/bash -x

if ! [ -f id_ed25519-hadoop ]; then
    ssh-keygen -t ed25519 -P "" -f id_ed25519-hadoop
fi
for host in "$@"; do
    ssh root@$host "mkdir -m 0700 ~hadoop/.ssh"
    scp -p id_ed25519-hadoop  "root@$host:~hadoop/.ssh/id_ed25519"
    scp -p id_ed25519-hadoop.pub  "root@$host:~hadoop/.ssh/id_ed25519.pub"
    scp -p id_ed25519-hadoop.pub  "root@$host:~hadoop/.ssh/authorized_keys"
    ssh root@$host "chmod -R go-rwx ~hadoop/.ssh"
    ssh root@$host "chown -R hadoop:hadoop ~hadoop/.ssh"
done
