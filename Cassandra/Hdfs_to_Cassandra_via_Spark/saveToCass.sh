#!/bin/bash

#$1 is file that contain list of bz2 files to download
#$2 swift auth token
#$3 swift sotrage url
#$4 list of servers delimited by comma


IFS=',' read -a myarray <<< "$4"

#get filename of file to download
while IFS='' read -r line || [[ -n "$line" ]]; do
	
	echo "@@@@@____@@@@____@@@@____taking care of this file $line"

	#swift download redditcomments $line --os-auth-token $2 --os-storage-url $3

	#unzip file
	#bzip2 -d $line

	#download file to hadoop (only) server and push it to the hdfs
	ssh root@hadoop /root/saveToHadoop.sh $line $2 $3  < /dev/null

	#run spark and dump data into cassandra
	#split string by "." and take first string
	IFS='.' read -a filename <<< "$line"

	#upload to hadoop
	#echo "@@@@@@@@@@@@@@@@@@@ upload to hdfs"
	#hadoop dfs -copyFromLocal ${filename[0]} hdfs://spark1/hdfs/${filename[0]}
	#remove local file
	#rm -f /usr/local/spark/${filename[0]}

        echo "@@@@@@@@@@@@@@@@@@@ launching spark"
	#$SPARK_HOME/bin/spark-submit   --master spark://spark1:7077 $(find target -iname "*assembly*.jar") ${filename[0]}   #rc-2007-10
	$SPARK_HOME/bin/spark-submit   --master spark://spark1:7077 $(find target -iname "*assembly*.jar") $line   #rc-2007-10	

	#remove file on hadoop
	echo "@@@@@@@@@@@@@@@@@@@ remove file from hdfs"
	hdfs dfs -rm hdfs://spark1/hdfs/$line

done < "$1"
