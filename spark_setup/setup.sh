#!/bin/bash -x

. ./config.sh
workdir=$PWD

install_java() {
    java=java-1.8.0-openjdk-headless
    yum install -y rsync $java  yum-utils epel-release
    alternatives --set java $(rpm -ql $java | grep 'java$')
}

update_root_bashprofile() {
    cat <<EOF >> ~/.bash_profile
export JAVA_HOME="$(readlink -f $(which java) | grep -oP '.*(?=/bin)')"
export HADOOP_HOME=/usr/local/hadoop-2.7.1
export LD_LIBRARY_PATH=\$HADOOP_HOME/lib/native
export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop
export HADOOP_MAPRED_HOME=\$HADOOP_HOME
export HADOOP_HDFS_HOME=\$HADOOP_HOME
export HADOOP_YARN_HOME=\$HADOOP_HOME
export SPARK_HOME=/usr/local/spark-1.5.2-bin-2.7.1
export PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$SPARK_HOME/bin:\$SPARK_HOME/sbin
EOF
    . ~/.bash_profile
}

install_swift() {
    # get swift access
    yum-config-manager --enable epel
    yum install -y python-pip rlwrap lbzip2
    pip install python-swiftclient
}

install_devtools() {
    # for patch, and pip installs
    yum group install -y "Development Tools"
}

install_hadoop_spark() {
    # fetch spark/hadoop builds
    swift_auth_opts="-U userid -K apikey -A authurl"
    
    swift $swift_auth_opts download w251cfg hadoop-2.7.1.tar.gz
    rm -rf /usr/local/hadoop-2.7.1
    (cd /usr/local; tar zxf $workdir/hadoop-2.7.1.tar.gz; patch -p0 -i $workdir/hadoop-cfg.diff)
    
    rm -rf /usr/local/spark-1.5.2-bin-2.7.1
    swift $swift_auth_opts download w251cfg spark-1.5.2-bin-2.7.1.tgz
    (cd /usr/local; tar zxf $workdir/spark-1.5.2-bin-2.7.1.tgz; patch -p0 -i $workdir/spark-cfg.diff)
    if on_master; then
	grep -v localhost /etc/hosts | sed -e 's/.* //' | tee $HADOOP_CONF_DIR/slaves > $SPARK_HOME/conf/slaves
        hdfs namenode -format
    fi
}

setup_hdfs_space() {
    if ! grep -q hdfs1 /etc/fstab; then
	mkfs.xfs -L hdfs1 /dev/xvdc
	mkdir -p /mnt/hdfs1
	echo 'LABEL=hdfs1 /mnt/hdfs1 xfs defaults,noatime 0 0' >> /etc/fstab
	mount /mnt/hdfs1
    fi
}

install_python_stuff() {
    yum install -y freetype-devel libpng-devel
    pip install csvkit
    yum deplist pandas scipy | grep provider | cut -f2 -d:  | sort -u | \
        xargs yum -y install
    pip install -U matplotlib pandas
    if on_master; then
        pip install jupyter
    fi
}

setup_hadoop_user() {
    useradd hadoop
    chown -R hadoop:hadoop /mnt/hdfs1 $HADOOP_HOME $SPARK_HOME
}


install_java
update_root_bashprofile
install_swift
install_devtools
install_hadoop_spark
setup_hdfs_space
install_python_stuff
setup_hadoop_user

#http://master-ip:50070/dfshealth.html
#http://master-ip:8088/cluster
#http://master-ip:19888/jobhistory
