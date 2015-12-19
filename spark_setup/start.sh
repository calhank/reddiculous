#!/bin/bash -x

onMaster() {
    if [ $HOSTNAME = final-gateway ]; then
	return 0
    fi
    return 1
}

# hadoop
start-dfs.sh
start-yarn.sh
mr-jobhistory-daemon.sh --config $HADOOP_CONF_DIR start historyserver

# spark
start-master.sh
start-slaves.sh
start-history-server.sh
start-shuffle-service.sh

# report
sleep 2
hdfs dfsadmin -report
yarn node -list
