apt-get install -y curl unzip net-tools jq rsync
apt-get install -y openjdk-7-jre
apt-get install -y python-setuptools
easy_install pip
pip install python-swiftclient

fdisk /dev/xvdc

sudo mkfs -t ext3 /dev/xvdc1
mkdir /media/elasticsearch
mount /dev/xvdc1 /media/elasticsearch
mkdir /media/elasticsearch/logs1
mkdir /media/elasticsearch/data1

groupadd elasticsearch
useradd -g elasticsearch elasticsearch
chown -R elasticsearch:elasticsearch /media/elasticsearch
cp /etc/sudoers /etc/sudoers.backup
echo "elasticsearch ALL=(ALL:ALL) ALL" >> /etc/sudoers
mkdir /home/elasticsearch
chown -R elasticsearch:elasticsearch /home/elasticsearch
su elasticsearch

cd ~
echo "export JAVA_HOME=/usr/bin/java" >> ~/.bash_profile
echo "export ES_MIN_MEM=32g" >> ~/.bash_profile
echo "export ES_MAX_MEM=32g" >> ~/.bash_profile
chmod 700 ~/.bash_profile
source ~/.bash_profile
curl -L -O https://download.elasticsearch.org/elasticsearch/release/org/elasticsearch/distribution/zip/elasticsearch/2.1.0/elasticsearch-2.1.0.zip
unzip  elasticsearch-2.1.0.zip
cd  elasticsearch-2.1.0
bin/plugin install license
bin/plugin install marvel-agent

cp /home/elasticsearch/elasticsearch-2.1.0/config/elasticsearch.yml /home/elasticsearch/elasticsearch-2.1.0/config/elasticsearch.yml.backup
