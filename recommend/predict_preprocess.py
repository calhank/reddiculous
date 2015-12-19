import os
spark_home='/usr/local/spark-1.5.2-bin-2.7.1'
os.environ['SPARK_HOME']=spark_home
import sys
sys.path.append(os.path.join(spark_home, 'python'))
sys.path.append(os.path.join(spark_home, 'python/lib/py4j-0.8.2.1-src.zip'))

from pyspark import SparkContext, StorageLevel, SparkConf
from pyspark.sql import SQLContext, Row
from pyspark.sql.types import *

scfg=SparkConf()
scfg.set("spark.cores.max",64)
sc=SparkContext(master="spark://final-gateway:7077", appName="reddit-collab-filter", conf=scfg)

parq_df=sqlContext.read.parquet("hdfs://final-gateway/w251/reddit-comments.parquet")

# get subreddits where total number of comments is greater than 10000
sr_counts = parq_df.groupBy(parq_df.subreddit).count().where('count>10000')
pop_sr=parq_df.join(sr_counts,'subreddit')

# ensure all users and sites that have been deleted are removed from data
user_site = pop_sr.map( lambda row: (row.author , row.subreddit ) ).filter( lambda row: row[0] != "[deleted]" and row[1] != "[deleted]" )

# map-reduce user_site combinations to get counts for each time a user commented on a subreddit
mr = user_site.map( lambda row: ( row , 1) ).reduceByKey( lambda a, b: a + b ).map(lambda (a,b): Rating( a[0], a[1] , float(b) ) )

# save result to HDFS for later use in recommendation engine
mr.saveAsTextFile("hdfs://final-gateway/w251_cf-user-site-total")


sc.stop() # kill process
