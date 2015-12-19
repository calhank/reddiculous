# Reddiculous
## Reddit Analysis and Subreddit Recommender

---  

## Table of Contents

1. [Introduction & Data](#introduction--data)

1. [Data Collection and Storage](#data-collection-and-storage)

  1. [Acquisition and Management](#acquisition-and-management)

  1. [Data Management/Ingest Tools](#data-managementingest-tools)

    1. [Approach 1 - Spark, Parquet, and HDFS](#approach-1---spark-parquet-and-hdfs)

    1. [Approach 2 - ElasticSearch](#approach-2---elasticsearch)

    1. [Approach 3 - Cassandra](#approach-3---cassandra)

1. [Exploratory Data Analysis](#exploratory-data-analysis)

  1. [Data Applications](#data-applications)

    1. [Author Graph Analysis](#author-graph-analysis)

    1. [Kibana Analytical Capability](#kibana-analytical-capability)

    1. [Subreddit Recommender System](#subreddit-recommender-system)

1. [Code Breakdown](#code-breakdown)

  1. [ElasticSearch Code](#elasticsearch-code)

  1. [PySpark Subreddit Recommender System](#pyspark-subreddit-recommender-system)

  1. [PageRank and Graph Analysis Code](#pagerank-and-graph-analysis-code)

  1. [Spark Cluster Setup](#spark-cluster-setup)

  1. [Cassandra Cluster Setup and Data Ingestion](#cassandra-cluster-setup-and-data-ingestion)

  1. [Sentiment Analysis Prototype](#sentiment-analysis-prototype)

  1. [Django Web App prototype for Recommender product] (#django-web-app-prototype-for-recommender-product)

## Introduction & Data
Reddit is an extremely popular social networking site. They have 32 million users every month. There are ~850,000 subreddits and growing(1). The possible social network analysis that can be performed on the information in this popular site are endless. In July 2015, a reddit user announced the availability of the Reddit comments between October of 2007 and May of 2015(2). The dataset is available for an download from archive.org(3). There are 1.7 billion comments at approx. 150 GB compressed.

*Data Format:*
```
{"score_hidden":false,"name":"t1_cnas8zv","link_id":"t3_2qyr1a"...
{"distinguished":null,"id":"cnas8zw","archived":false,"author":"...
{"score_hidden":false,"link_id":"t3_2qxefp","name":"t1_cnas8zx",...
{"parent_id":"t3_2qys4x","subreddit":"AdviceAnimals","gilded":0,...
{"body":"Very fast, thank you!","created_utc":"1420070400","down...
{"author":"BigGupp1","score":6,"archived":false,"id":"cnas900","...
```

##Data Collection and Storage
###Acquisition and Management

The reddit comments corpus consists of approximately 150GB of bzip2-compressed JSONL files (i.e., each line is a JSON document). We retrieved these from [archive.org](https://archive.org/details/2015_reddit_comments_corpus).

Range-parallelized `GET`s using [`htcat`](https://github.com/htcat/htcat) sped up download substantially (factor of 3-5x), but we encountered [data corruption](https://github.com/htcat/htcat/issues/16) in some cases, and reverted to simpler HTTP clients.  We saved each file's data directly to SoftLayer Object Storage (i.e., via pipes rather retrieving to temporary files then uploading) to share them easily across the team.

###Data Management/Ingest Tools

We each explored different systems to bring the data closer to compute resources for analysis.

#### Approach 1 - Spark, Parquet, and HDFS

Hadoop's `File` APIs and Spark's `SQLContext` made loading the corpus almost trivial: simply opening the containing directory with Hadoop text file APIs  reads and decompresses each files in the directory and provides their contents sequentially.  Since the JSON lines in this corpus are flat (no subobjects or arrays) and have identical keys between documents, these were also ideally suited to the Spark `DataFrame` and SQL abstractions. We were able to load them all and parse the entire corpus using a single statement: `val reddit_df=sqlContext.read.json("hdfs://final-gateway/w251/reddit-comments/")`.

Originally, we had intended to consume the data from SoftLayer Object Storage (i.e., `val reddit_df=sqlContext.read.json("swift://redditcomments.dal05/")`, plus some configuration). To permit this, we built a Hadoop 2.7.1 with [patches to support SLOS authentication](https://www.ibm.com/developerworks/community/blogs/e90753c6-a6f1-4ae2-81d4-86eb33cf313c/entry/apache_spark_integrartion_with_softlayer_object_store?lang=en).  The original attempt failed since the Swift driver (or more specifically, `java.net.url`) requires containers' names to be valid DNS hostnames (`^[a-z0-9-]+$`). After failed attempts to work around this, we copied the data from container `reddit_comments` to a new container `redditcomments` using Swift's server-side `COPY` REST call.  However, the Swift driver proved somewhat flaky (timeouts on large files, etc.) and less performant than copying the corpus to HDFS first.  This is not all that surprising since the HDFS code is much more heavily used/tested, and avoids copying the corpus over a network since the data blocks reside on cluster-local disks.

Once the data was available as an RDD, we saved it these to HDFS using Parquet. We also used this approach for subsequent RDDs involving expensive processing. This made it relatively quick to resume work across sessions, as we did not have to replay all the transforms needed to consume the bz2 files -- an hours-long process due primarily to the computational overhead of parsing 1.6 billion JSON strings.  Interestingly, the bzip2 compression was not a greater factor.  Since it reduced the disk I/O by about a factor of 6, it more than paid for the computational cost in its imnprovements to total runtime, offering approximately a 10x increase in read rates for the unparsed text vs. uncompressed.  Parquet blocks are also BZip2 compressed, but since they are columnar and type-aware, the deserialization is much less expensive that JSON parsing.

#### Approach 2 - ElasticSearch

ElasticSearch provides an essential function that Reddit simply doesn't have: Ability to search for posts by the content of the post *body*. Reddit currently only allows searches for subreddit name or the title of the forum link. ElasticSearch enables this by creating Lucene indexes for each field.

But this process is costly in terms of both computation and memory. Furthermore, as ElasticSearch primarily operates with a REST API over HTTP, uploading individual records is additionally costly in terms of network traffic. If, for example, you average 50 milliseconds per request and you upload 1 record per request, indexing 1,000,000,000 posts would take approximately *1.5 years*.

Thankfully ElasticSearch provides a "Bulk Upload API." This API accepts multiple records in a single file, formatted such that the metadata for each record precedes the record. We chose to upload files that contained 5000 records a piece, using (3 x the number of nodes) threads that were evenly distributed among the node IP addresses. By uploading records in bulk and ensuring that each node was given equal work, we were able to achieve speeds ranging from 9k to 18k records per second. Our main upload method took approximately 37 hours to complete. After all the data was uploaded, the index shards were replicated across servers to ensure redundancy and maximal uptime. We utilized the Marvel plugin to monitor node health during upload.

#### Approach 3 - Cassandra

We used a bash script to obtain each BZip2 file, stored each in HDFS as to keep the disk space consistent, the used Cassandra connector library to save the content to a Cassandra table. Each BZip2 file in HDFS was cleaned up after each successful data storage into Cassandra. We used subreddit id and comment id as primary indexes. Later, we added author and link_id (comment thread id) as we had hoped to query the table by either of the attributes. However,  we did not complete the cassandra ingestion because of the cluster instability issues, and also because HDFS Parquet approach above seemed to be a more stable option while achieving the same goal. 

As we experimented with adding new nodes (we had maximum of 20 nodes at some point) automating the setup work around password less communication among nodes and Spark/HDFS/Cassandra Installation using bash file helped reduce the pain as we expanded the cluster. Also, rsync was a lifesaver when it came to passing around the cassandra/hdfs/spark setup files. Additionally, CSSH (CSSHX on mac) was very useful in configuring the entire cluster at once. 

##Exploratory Data Analysis

We interacted with Spark primarily through IPython notebooks, except for a few cases where functionality was only available in Scala. The key example of the latter were the GraphX APIs, which we used to analyze properties of some of the networks derived from the comments.  We built a Spark 1.5.2 matching our Hadoop 2.7.1, both with Scala 2.11.  Hadoop built without trouble, but there were some deprecated features to clean up for Spark, and the Hive and thrift server support had to be disabled.  

When exploring the data with Scala code, we perhaps surprisingly did not work interactively using `spark-shell`.  Our Scala programs tended to be short, our data well-distributed and quickly loaded using Parquet (also needed to build locally, since prebuilt only support Scala 2.10), and our development data of manageable size, the latency of a traditional edit/compile/submit cycle did not inhibit development efficiency significantly.

There were also a few avenues we explored that did not pan out.  Two particularly intriguing ones were to use an IPython kernel (`spark-kernel` or `jupyter-scala`) to interact with Spark in scala from a notebook. However, due to difficulties porting the kernels to Scala 2.11, we were not able to use these.  In retrospect, using Scala 2.11 substantially increased the effort needed to get a working system. After having started with it, it seemed worthwhile to work through the problems. This seems now to have been the sunk cost fallacy.  In the other direction, there was not enough time to adapt Kushal Datta's [Python GraphX API](https://issues.apache.org/jira/browse/SPARK-3789) from Spark 1.4.0 to 1.5.2.

###Data Applications
#### Author Graph Analysis
On the Spark cluster, the main graph analysis was a MLLib PageRank with users as nodes and their interactions (replies) as directed (multi-)edges.  The prototype was developed using a single subreddit (“WTF”), and the approach appeared to work, supporting a loose interpretation as “ability of a user to elicit replies”. For example, we might expect that if a high-rank user replies to another user, more people would see that user’s post and possibly reply themselves. Alternatively, high-rank users may simply post more insightful comments than other users. This could bear more detailed investigation, perhaps integrating with the Reddit API to include user profile information.

Going into more detail, edges are identified with a self-join to connect replies with their parents:

`FROM reddit t1 INNER JOIN reddit t2 ON t1.name = t2.parent_id`

The query excluded all documents that did not have have replies, and fields not conducive to graph analyses, such as the comment bodies. As a result the edge table is substantially smaller.

**Full comments v. self-joined RDD stats**

Name | Columns | Rows | Parquet Size (GB)
---- | ------- | ---- | -----------------
`reddit-comments` | 33 | 1,659,361,605 | 152.4
`reddit-comments-selfjoin` | 17 | 993,838,767 | 21.0

Since this table is smaller, it seemed preferable for caching. So extracted vertices (user IDs) from this rather than the raw data.  After generating the graph RDD and running pagerank, we saw that the most influential user (by 2 orders of magnitude) was '[deleted]'! This was clearly a dummy value, so we updated the queries to remove this “user” from the vertices to avoid its disproportional weight contribution to comments to which deleted users replied.

The next (current) prototype loops over subreddits with at least 1000 comments and saves the pagerank output to HDFS as Parquet tables. This required some tuning of driver memory (for event logging JSON serialization). This algorithm achieves excellent cluster utilization, with each iteration consuming ~95% CPU on each host.  Assuming no (more) out-of-memory conditions or other errors, the run should take approximately 3 days to complete.

**Top 4 for subreddit WTF, 10 iterations, .15 teleportation:**

User | PageRank
---- | --------
lukeatron | 447.3230812297997
AtlanteanSteel | 175.2990489825727
zachferguson019 | 163.66208707023688
Ceedog48 | 154.4812491444715

The edge table also includes comment quality metrics such as up/down votes, likes, gold (Reddit's user-to-user pseudo-currency), and abuse report counts.  These have not yet been used, but seem desirable for weight-scored graph algorithms or classifiers.

#### Kibana Analytical Capability

Upon exploring ElasticSearch, we found that the best way to use the system besides searching for specific posts about a topic was to use the "Search API" to query for a specific term that had recieved many upvotes or gold. But even  more interesting results could be achieved via visualization.

Kibana is an ElasticSearch visualization tool. When indexing the data, we first identified the timestamp field as UTC format. Using this timestamp, we are able to visually track trends in the public conversation.

For example, running a query against the appearance of the word "NFL" in the post body text over time yields a spike in mentions around the end of the playoffs / the Superbowl every year since 2009.

![](https://cloud.githubusercontent.com/assets/12476582/11873648/b410cedc-a4a9-11e5-8cbd-002c3755e587.png)

On the political side, running a query against the word "NSA" reveals almost no discussion whatsoever prior to June 2013 when the Snowden documents were released, a very large spike in interest, and a gradual trailing off interrupted by spikes associated mostly with news stories about the agency.

![](https://cloud.githubusercontent.com/assets/12476582/11873654/b825996c-a4a9-11e5-9ba5-4bf6fae28873.png)

#### Subreddit Recommender System

Reddit website provides only elementary keyword-based search. We implemented Subreddit Recommender System: The program accepts a user's current favorite subreddits as input, and returns a list of the top 30 subreddits they are most likely to like as output.

The recommender system was built in PySpark using MLLib. Pre-processing consisted of a map-reduce job that calculated the count of posts that a single user submitted to a single subreddit. The output was a tuple like `('someUser1999','IAmA', 41)`. This tuple was converted to a `Rating( )` object by hashing the username and subreddit name to integers. After the algorithm finished running, these ID numbers were used to re-convert the results to human-readable subreddit names.

We elected to use the `ALS.trainImplicit( )` method from MLLib because it is designed to use proxy metrics rather than direct preference scores. Our proxy metric was the number of comments a user submitted to a single subreddit.

For example, if a user submits the following subreddits - *nfl, baseball, sports, CFB* - the resulting output might be:

Rank | Score | Subreddit
---- | ---- | ------
1 | 0.3856 | Music
2 | 0.3078 | nba
3 | 0.2862 | movies
4 | 0.2765 | trees
5 | 0.2644 | videos
6 | 0.2582 | soccer
7 | 0.2144 | hockey
8 | 0.2120 | leagueoflegends
9 | 0.1631 | fantasyfootball
10 | 0.1573 | hiphopheads

Using 256 cores, each recommendation takes approximately 3-5 minutes.


##Code Breakdown

### ElasticSearch Code

* [`elasticsearch/elasticsearch-softlayer-vs-config`](elasticsearch/elasticsearch-softlayer-vs-config) - Command line input for ES node configuration via Softlayer
* [`elasticsearch/es-setup.sh`](elasticsearch/es-setup.sh) - Shell script to configure Softlayer VS for elasticsearch, including mounting external filesystem
* [`elasticsearch/elasticsearch.yml`](elasticsearch/elasticsearch.yml) - Copy this file to ElasticSearch/config directory on VS, change `node.name` and `network.host` and `discovery.zen.ping.unicast.hosts` to match cluster config
* [`elasticsearch/reddit_file_list.txt`](elasticsearch/reddit_file_list.txt) - Input to bulk upload containing names of compressed Reddit post files in Swift Object Store
* [`elasticsearch/bulk_upload.py`](elasticsearch/bulk_upload.py) - Python script to initialize upload to ElasticSearch. Sample usage: `python bulk_upload.py 184.173.97.152 reddit_ts reddit_file_list.txt 5000` will initialize upload at node with IP "184.173.97.152", adding records to the "reddit_ts" index, reading files from "reddit_file_list.txt" and uploading chunks of 5000 records at a time. **NOTE:** *This script requires directory named `progress/` to exist in same directory where `bulk_upload.py` script will run.*

### PySpark Subreddit Recommender System

* [`recommend/predict_preprocess.py`](recommend/predict_preprocess.py) - Preprocesses Parquet-format Reddit posts to `(user, subreddit, num_comments)` tuples and saves to HDFS
* [`recommend/subreddit_preferences.py`](recommend/subreddit_preferences.py) - Takes a list of user's favorite subreddits and outputs the top 30 recommendations for other subreddits the user should check out. Usage: `$ python subreddit_preferences.py --cores <int> <subreddit1> <subreddit2> ...` Example Usage: `$ python subreddit_preferences.py --cores 192 nfl baseball sports CFB`
* [`recommend/subreddit_names.txt`](recommend/subreddit_names.txt) - List of all acceptable inputs into recommendation engine (only subreddits with at least 10000 posts)

### PageRank and Graph Analysis Code

* [`GraphXStuff/ReplyPageRank.scala`](GraphXStuff/ReplyPageRank.scala) - Assembled User-Reply graphs, calculates PageRank, writes to file.  Build with `sbt`. 
* [`GraphXStuff/python-wip.ipynb`](GraphXStuff/python-wip.ipynb) - data exploration IPython notebook

### Spark Cluster Setup
For the Spark cluster, we initially used 4 (8GB), then 16 (32GB), then 32 (32GB) instances with 8 cores and a 300GB XFS filesystem for HDFS each. Since the cluster nodes were added incrementally (especially the second hexadecad, as the VS creation ticket approval latencies were around a day), it was necessary to use `hdfs balance` after additions to ensure the HDFS data remained distributed evenly across datanodes. The nodes after the initial four were configured using the scripts in [spark_setup/](spark_setup), which starts with 
* [`driver.sh`](spark_setup/driver.sh) on a machine with `slcli` access.  This 
  * distributes the scripts, 
  * generates and distributes keys, and
  * runs `setup.sh` on each new node.
* [`setup.sh`](spark_setup/setup.sh)
  * sets up the environment
  * formats and configues the filesystem for HDFS data
  * retrieves and installs software, and
  * configures Spark and Hadoop
Nodes are configured to communicate and trust only nodes on the private network.

After nodes are added, we update `/etc/hosts` on all hosts using [`distribute_hosts_file.sh`](setup_scripts/distribute_hosts_file.sh), and finally (manually) update the master's Hadoop and Spark `slaves` files.
Convenience scripts [`start.sh`](setup_scripts/start.sh) and [`stop.sh`](setup_scripts/stop.sh) are provided to start Yarn, HDFS, Spark, history daemons, and the shuffle service (not used -- I was not able to get masters under Yarn working properly).

### Cassandra Cluster Setup and Data Ingestion
* [`Cassandra/clusterSetup/setup_password_less_ssh/`](Cassandra/clusterSetup/setup_password_less_ssh/) - Contains bash files for automating setup of the passwordless communication amont nodes.

* [`Cassandra/clusterSetup/hadoop_spark_cassandra_install.sh`](Cassandra/clusterSetup/hadoop_spark_cassandra_install.sh) - Bash file for installing Spark, Cassandra and Hadoop

* [`Cassandra/cassandra_conf/cassandra.yaml`](Cassandra/cassandra_conf/cassandra.yaml) - Cassandra.yaml file used

* [`Cassandra/Hdfs_to_Cassandra_via_Spark/saveToHadoop.sh`](Cassandra/Hdfs_to_Cassandra_via_Spark/saveToHadoop.sh) - Bash file for obtaining reddit BZ2 files.

* [`Cassandra/Hdfs_to_Cassandra_via_Spark/saveToCass.sh`](Cassandra/Hdfs_to_Cassandra_via_Spark/saveToCass.sh) - Bash file for automating retrieval and ingestion of reddit BZ2 file for each month. The files to obtain can be configured in bz2list file in the same folder.

* [`Cassandra/Hdfs_to_Cassandra_via_Spark/saveToCass.sh`](Cassandra/Hdfs_to_Cassandra_via_Spark/saveToCass.sh) - Bash file for automating retrieval and ingestion of reddit BZ2 file for each month. The files to obtain can be configured in bz2list file in the same folder.

* [`Cassandra/Hdfs_to_Cassandra_via_Spark/SaveToCassandraWithSpark/`](Cassandra/Hdfs_to_Cassandra_via_Spark/SaveToCassandraWithSpark/) - Spark application used for storing data in
to Cassandra

### Sentiment Analysis Prototype
* [`Sentiment/`](Sentiment/) - Prototype for Sentiment Analysis using AlchemyAPI using Spark

### Django Web App prototype for Recommender product
* [`webapp/`](webapp/) - An attempt to launch spark job from django web app (it does not work yet)


References:
(1)  http://expandedramblings.com/index.php/reddit-stats/
(2)  https://www.reddit.com/r/datasets/comments/3bxlg7/i_have_every_publicly_available_reddit_comment/
(3)  https://archive.org/details/2015_reddit_comments_corpus
