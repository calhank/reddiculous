# base libs
import os
import sys
import argparse

# spark configs
spark_home='/usr/local/spark-1.5.2-bin-2.7.1'
os.environ['SPARK_HOME']=spark_home
sys.path.append(os.path.join(spark_home, 'python'))
sys.path.append(os.path.join(spark_home, 'python/lib/py4j-0.8.2.1-src.zip'))

# spark imports
from pyspark.sql.types import *
from pyspark import SparkContext, SparkConf
# from pyspark.sql import SQLContext, Row
from pyspark.mllib.recommendation import ALS, Rating #,MatrixFactorizationModel

def javahash( string ):
    # ALS requires Java-compatible integers as ID fields. Method hashes `string` to java-compatible int.
    string = str(hash(string))
    return int(string[-9:])

def tup_to_rating( tup ):
    # map (user, subreddit, count_of_comments) tuples to Rating( ) object for ALS
    user, subreddit, num = tup
    user = javahash(user)
    subreddit = javahash(subreddit)
    num = float(num)
    return Rating(user, subreddit, num)

def main(cores, prefs):

	"""
	ALS Algorithm to Recommend Subreddits to User based on User-defined preferences
	
	args:
	cores (int) : number of cores for spark job
	prefs (list[str]) : list of strings containing subreddit names - capital letters are non-trivial
	"""

	scfg=SparkConf()
	scfg.set("spark.cores.max",cores)
	sc=SparkContext(master="spark://final-gateway:7077", appName="reddit-cf", conf=scfg)

	try:
		# prep data
		raw_counts = sc.textFile("hdfs://final-gateway/w251_cf-user-site-total")
		parsed_counts = raw_counts.map(lambda st: eval(st))
		all_ratings = parsed_counts.map( tup_to_rating )
		# assign user-identified preferred subreddits
		raw_prefs = [ (999, x, 100) for x in prefs ]
		my_prefs = sc.parallelize(raw_prefs).map(tup_to_rating)

		# train model
		model_input = all_ratings.union(my_prefs)
		model = ALS.trainImplicit(model_input, 10, 10, alpha=.01, seed=5)

		# candidate prefs for prediction
		my_prefs_ids = set([javahash(x) for x in prefs])
		all_subreddit_ids = parsed_counts.map( lambda (a,b,c): (javahash(b),b) ).distinct().cache()
		candidates = all_subreddit_ids.map(lambda (a,b): a ).filter( lambda r: r not in my_prefs_ids)

		predictions = model.predictAll(candidates.map( lambda x: (999, x))).cache()

		final = predictions.map(lambda (a,b,c): (b,c)).join(all_subreddit_ids).map(lambda (b,(c,d)): (c,d) ).sortByKey(False)

		output = list( final.take(30) )
		sc.stop()
		return output
	except Exception, e:
		print("App failed. Stopping gracefully")
		sc.stop()
		raise Exception(e)

if __name__=="__main__":
	
	"""
	ALS Algorithm to Recommend Subreddits to User based on User-defined preferences
	
	example usage:
	$ python subreddit_preferences.py --cores 192 nfl baseball sports CFB
	"""
	
	parser = argparse.ArgumentParser()
	parser.add_argument("--cores")
	parser.add_argument("subreddits", nargs='+')

	args = parser.parse_args()

	if args.cores is None:
		cores = 128
	else:
		cores = int(args.cores)
	
	print main(cores, args.subreddits)
