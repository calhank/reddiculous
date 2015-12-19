#spark
curl https://bintray.com/sbt/rpm/rpm | sudo tee /etc/yum.repos.d/bintray-sbt-rpm.repo
yum install -y java-1.8.0-openjdk-headless sbt
echo export JAVA_HOME=\"$(readlink -f $(which java) | grep -oP '.*(?=/bin)')\" >> /root/.bash_profile
source /root/.bash_profile
$JAVA_HOME/bin/java -version
curl http://d3kbcqa49mib13.cloudfront.net/spark-1.5.0-bin-hadoop2.6.tgz | tar -zx -C /usr/local --show-transformed --transform='s,/*[^/]*,spark,'
echo export SPARK_HOME=\"/usr/local/spark\" >> /root/.bash_profile
source /root/.bash_profile

#cassandra
cat <<\EOF >> /etc/yum.repos.d/datastax.repo
[datastax]
name = DataStax Repo for Apache Cassandra
baseurl = http://rpm.datastax.com/community
enabled = 1
gpgcheck = 0
EOF
yum -y install dsc20
#copy cassandra.yaml from master
scp root@spark1:/etc/cassandra/conf/cassandra.yaml /etc/cassandra/conf

#hadoop
curl http://apache.claz.org/hadoop/core/hadoop-2.6.2/hadoop-2.6.2.tar.gz | tar -zx -C /usr/local
yum install -y rsync
cat <<\EOF >> ~/.bash_profile
export HADOOP_HOME=/usr/local/hadoop-2.6.2
export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_HDFS_HOME=$HADOOP_HOME
export YARN_HOME=$HADOOP_HOME
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
EOF

source ~/.bash_profile
