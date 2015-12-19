# bulk elasticsearch upload method

import time
import os
import subprocess
import argparse
import requests
import bz2
import json
from multiprocessing import Process, Queue
import logging
import signal
from datetime import timedelta

def get_node_ips(url):
	# returns IP addresses for all nodes in cluster
	r = requests.get("http://%s:9200/_nodes" % url)
	if r.status_code in (200, 201):
		data = r.json()
		nodes = []
		for _, node in data["nodes"].iteritems():
			nodes.append(node["ip"])
		return nodes
	else:
		raise Exception( "No Cluster Found at %s.\nError: %s" % (url, r.content) )

def transform_for_index(line, new_index, Type):
	# adds index metadata to data for Bulk Upload API
	record = json.loads(line)
	meta = {
		"index":{
			"_index": new_index,
			"_type": Type,
			"_id": record["id"]
		}
	}
	output = json.dumps(meta) + "\n" + line + "\n"
	return output

def bulk_upload(queue):
	# worker function that consumes bulk data chunks from queue
	# and asynchronously uploads to node via REST
	signal.signal(signal.SIGINT, signal.SIG_IGN)
	while 1:
		_start = time.time()
		time.sleep(.5)
		args = queue.get()
		url, data = args
		if len(data)<=0:
			# no data, kill thread
			print "no data, terminating"
			break
		try:
			requests.post( "http://%s:9200/_bulk" % url, data=data)
		except:
			# fail gracefully
			pass
		dur = time.time() - _start
		print url,'upload latency', str(dur)[:6]

if __name__=="__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("url", help="url for elasticsearch cluster")
	parser.add_argument("to_index", help="new index name")
	parser.add_argument("file_list", help="file containing list of files to upload separated by newlines")
	parser.add_argument("size", help="number of records per request")
	parser.add_argument("--log", help="log file name")
	args = parser.parse_args()
	if args.log is not None:
		logging.basicConfig(filename=args.log, level=logging.INFO)
	
	ES_URL_LIST = get_node_ips(args.url)

	queue = Queue(len(ES_URL_LIST)+1) # initialize queue with max length of number of ES nodes + 1
	procs = [Process(target=bulk_upload, args=(queue,)) for i in range(0,len(ES_URL_LIST)*3)] # launch 3 x number of ES Nodes upload worker processes
	for proc in procs:
		proc.daemon = True # daemonize processes
		proc.start()

	uploads = 0
	records = 0
	_start_all = time.time()

	with open(args.file_list) as fin:
		# read file list into python
		file_list = list(reversed([f for f in fin.read().split("\n") if len(f) > 0]))

	logging.info("STARTING SCRIPT")
	print args
	print "Desination URLs", ES_URL_LIST
	logging.debug("urls" + str(ES_URL_LIST))
	print "File list", file_list
	logging.debug("files" + str(file_list))

	try:
		for f in file_list:
			# keep track of progress per file
			progress_file = os.path.join("progress",  f + ".progress")

			if os.path.exists( progress_file ):
				# if a progress file exists, skip records that were already uploaded
				print progress_file, "exists"

				with open( progress_file ,'r') as prog:
					progress = prog.read()
					if progress == "COMPLETE":
						continue
					else:
						progress = int(progress)
						print f, "skipping to line", progress
			else:
				print progress_file, "does not exist"
				progress = -1
				with open(progress_file, 'w') as prog:
					prog.write(str(0))

			print "Downloading", f
			logging.debug("downloading " + f)
			a=subprocess.check_output([ "./swift_auth.sh"], shell=True)
			b=subprocess.check_output([ "swift", "download", "--skip-identical", "redditcomments", f ])
			print a, b
			print "Opening", f
			logging.debug("uploading " + f)
			with bz2.BZ2File(f,'r') as fin: # open compressed file
				lines = 0
				total_lines = 0
				data = ""
				for line in fin:
					total_lines += 1
					if total_lines <= progress: # skip to avoid redundant uploads
						continue
					lines += 1
					data += transform_for_index(line, args.to_index, "posts")
					if lines >= int(args.size):
						url = ES_URL_LIST.pop(0) # rotate upload URLs to ensure even distribution of requests among nodes
						ES_URL_LIST.append(url)
						queue.put((url, data)) # put data in queue for upload
						with open( progress_file ,'w') as prog: # track progress
							prog.write(str(total_lines))
						records += lines
						data = ""
						lines = 0
						uploads += 1
						dur_sec = (time.time() - _start_all)
						duration = timedelta(seconds=dur_sec)
						rate = records / dur_sec
						print "F:", f,
						print "N:",records,
						print "R:", int(rate),
						print "H", duration.seconds / 60**2,"M", (duration.seconds / 60 ) % 60
				url = ES_URL_LIST.pop(0)
				ES_URL_LIST.append(url)
				queue.put((url, data))
			print "Finished", f
			with open( progress_file ,'w') as prog:
				prog.write("COMPLETE")
			print "Deleting", f
			logging.debug("deleting " + f)
			os.unlink(f)
		else:
			print "No More Data"
			for i in range(0,len(ES_URL_LIST)*3):
				queue.put((url,""))
	
		print "joining queue"
		for proc in procs:
			proc.join()
		
	except (KeyboardInterrupt, Exception), e:
		print "terminating"
		print e
		queue.close()
		for proc in procs:
			proc.terminate()
			proc.join()

	duration = time.time() - _start_all	
	print records, "records in", duration, "seconds. rate", records/duration


