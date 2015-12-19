#!/bin/bash -x

# hadoop
stop-dfs.sh
stop-yarn.sh
mr-jobhistory-daemon.sh --config $HADOOP_CONF_DIR stop historyserver

# spark
stop-master.sh
stop-slaves.sh
stop-history-server.sh
stop-shuffle-service.sh

# report
sleep 2
jps
