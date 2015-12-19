from django.shortcuts import render
from django.http import HttpResponse
import os
import sys
#from recommender import main
#from recommender import test
import os
import sys
import argparse
import subprocess

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

prefs = []

def javahash( string ):
    string = str(hash(string))
    return int(string[-9:])

def tup_to_rating( tup ):
    user, subreddit, num = tup
    user = javahash(user)
    subreddit = javahash(subreddit)
    num = float(num)
    return Rating(user, subreddit, num)

def main(cores, pref,sc):

	"""
        cores (int) : number of cores for spark job
        prefs (list[str]) : list of strings containing subreddit names - capital letters are non-trivial
        """


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
                model = ALS.trainImplicit(model_input, 10, 10, alpha=.01)

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

# Create your views here.
def home3(request):
	#spark_home = os.environ['SPARK_HOME'] = '/usr/local/spark-1.5.2-bin-2.7.1/' #'/usr/local/spark/'
	#sys.path.insert(0,os.path.join(spark_home,'python'))
	#sys.path.insert(0,os.path.join(spark_home,'python/lib/py4j-0.8.2.1-src.zip'))
	
	#from pyspark import SparkContext, SparkConf	
	#sc = SparkContext()
	#data=[1,2,3,4,5]
	#distData = sc.parallelize(data)
	#first = distData.take(1)
	#sc.stop()

	prefs = ["worldnews","politics","Economics","Libertarian"]
	
	scfg=SparkConf()
	scfg.set("spark.cores.max",64)
        sc=SparkContext(master="spark://final-gateway:7077", appName="reddit-cf", conf=scfg)

        #data=[1,2,3,4,5]
        #distData = sc.parallelize(data)
        #first = distData.take(1)
        #sc.stop()

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
                #model = ALS.trainImplicit(model_input, 10, 10, alpha=.01)

                # candidate prefs for prediction
                #my_prefs_ids = set([javahash(x) for x in prefs])
                #all_subreddit_ids = parsed_counts.map( lambda (a,b,c): (javahash(b),b) ).distinct().cache()
                #candidates = all_subreddit_ids.map(lambda (a,b): a ).filter( lambda r: r not in my_prefs_ids)

                #predictions = model.predictAll(candidates.map( lambda x: (999, x))).cache()

                #final = predictions.map(lambda (a,b,c): (b,c)).join(all_subreddit_ids).map(lambda (b,(c,d)): (c,d) ).sortByKey(False)

                #output = list( final.take(30) )
                sc.stop()
                #return output
                recommends = ["asfd"] # output
        except Exception, e:
                print("App failed. Stopping gracefully")
                sc.stop()
                raise Exception(e)

	recommends = ["asfd","asdf"]
	recommends = list(model_input.take(20))
    	return render(request, "main/home.html", {'message' : recommends})
	#return render(request, "main/home.html", {'message' : first})


def home(request):

	prefs = ["IAmA","funny","nfl"]

	scfg=SparkConf()
	scfg.set("spark.cores.max",64)
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
		model = ALS.trainImplicit(model_input, 10, 10, alpha=.01)

		# candidate prefs for prediction
		my_prefs_ids = set([javahash(x) for x in prefs])
		all_subreddit_ids = parsed_counts.map( lambda (a,b,c): (javahash(b),b) ).distinct().cache()
		candidates = all_subreddit_ids.map(lambda (a,b): a ).filter( lambda r: r not in my_prefs_ids)

		predictions = model.predictAll(candidates.map( lambda x: (999, x))).cache()

		final = predictions.map(lambda (a,b,c): (b,c)).join(all_subreddit_ids).map(lambda (b,(c,d)): (c,d) ).sortByKey(False)

		output = list( final.take(30) )
		sc.stop()
	except Exception, e:
		print("App failed. Stopping gracefully")
		sc.stop()
		raise Exception(e)
	recommends = output
	return render(request, "main/home.html", {'message' : recommends})
