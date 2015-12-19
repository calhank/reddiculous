#!/bin/bash
master=${master:-final-gateway}
vs_regexp=${vs_regexp:-'final-gateway|spark'}

on_master() {
    if [ $HOSTNAME = $master ]; then
	return 0
    fi
    return 1
}

host_names() {
    slcli vs list --columns hostname | egrep "$vs_regexp"
    return 0
}

hosts_file() {
    printf "%- 15s  %s\n" 127.0.0.1 "localhost.localdomain localhost"
    slcli vs list --columns hostname,backend_ip | while read host ip; do
	if echo $host | egrep -q "${1:-.}" && echo "$ip" | egrep -q '^[0-9]+(\.[0-9]+){3}$'; then
	    printf "%- 15s  %s\n" $ip $host
	fi
    done
    return 0
}

host_ext_ips() {
    slcli vs list --columns hostname,primary_ip | while read host ip; do
	if echo $host | egrep -q "${1:-.}"; then
	    echo $ip
	fi
    done
    return 0
}
