#!/bin/bash

#$1 is file that contain list of bz2 files to download
#$2 swift auth token
#$3 swift sotrage url



	line=$1
	swift download redditcomments $line --os-auth-token $2 --os-storage-url $3

	#unzip file
	#bzip2 -d $line

	#run spark and dump data into cassandra
	#split string by "." and take first string
	#IFS='.' read -a filename <<< "$line"

	#upload to hadoop
	echo "@@@@@@@@@@@@@@@@@@@ upload to hdfs"
	#/usr/local/hadoop-2.6.2/bin/hdfs dfs -copyFromLocal ${filename[0]} hdfs://spark1/hdfs/${filename[0]}
	/usr/local/hadoop-2.6.2/bin/hdfs dfs -copyFromLocal $line hdfs://spark1/hdfs/$line
	#remove local file
	rm -f $line  #${filename[0]}

	

