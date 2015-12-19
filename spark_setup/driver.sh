#!/bin/bash -x
. ./config.sh

hosts=`host_ext_ips "$target_filter"`
echo "Setting up $hosts"
./distribute_hosts_file.sh $hosts
./distribute_root_key.sh $hosts
./distribute_setup_files.sh $hosts
./setup_hosts.sh $hosts
./distribute_hadoop_key.sh $hosts
./restrict_authorized_keys.sh $hosts
