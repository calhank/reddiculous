import org.apache.spark.SparkContext
import org.apache.spark.SparkContext._
import org.apache.spark.SparkConf
import org.apache.spark._
// To make some of the examples work we will also need RDD
import org.apache.spark.rdd.RDD
import org.json4s._
import org.json4s.native.JsonMethods._
import org.json4s.DefaultFormats._
import org.apache.spark._
import org.apache.spark.graphx._
import scala.util.hashing._
import java.io._
import com.datastax.spark.connector.SomeColumns
import com.datastax.spark.connector._

object Main extends App {


 	//println(args(0))
  	val conf = new SparkConf().setAppName("Simple Application")
		.set("spark.cassandra.connection.host", "127.0.0.1")
		.set("spark.cassandra.connection.port", "9043")
	val sc = new SparkContext(conf)

/*
val collection = sc.parallelize(Seq((1, "sevvcond","third"), (2, "second2","thrid2")))
collection.saveToCassandra("streaming", "tweetdata", SomeColumns("id", "author", "tweet"))
*/

 	//val file = "/usr/local/spark/README.md"
	//val file="file:///usr/local/spark/redditSmall.txt"
	
	//val file="file:///usr/local/spark/rc-2015-01"
	//val file = "file:///usr/local/spark/" +  args(0)
	val file = "hdfs://spark1/hdfs/" + args(0)
	//val file="redditSmall.txt"


	val lines = sc.textFile(file)


	//check to see if id attribute exist, if not we shouldn't add this to the graph
	//i know this is not a clean way of doing things... 
        def checkForID(s:String): Boolean = {

		try {
                	implicit val formats = DefaultFormats
                	val json = parse(s)
                	val extracted = (json \\ "id").extract[String]
                	return true
		} catch {

			case e:Exception=>{
      				return false
    			}
		}
		return false
        }


val tableName = "bysubreddit"

	lines.filter(checkForID).map{ s => 
  implicit val formats = DefaultFormats
                val json = parse(s)

((json \\ "id").extract[String],
(json \\ "archived").extract[Boolean],
(json \\ "author").extract[String],
(json \\ "body").extract[String],
(json \\ "controversiality").extract[Int],
(json \\ "created_utc").extract[String],
(json \\ "distinguished").extract[String],
(json \\ "downs").extract[Int],
(json \\ "gilded").extract[Int],
(json \\ "link_id").extract[String],
(json \\ "name").extract[String],
(json \\ "parent_id").extract[String],
(json \\ "retrieved_on").extract[Int],
(json \\ "score").extract[Int],
(json \\ "score_hidden").extract[Boolean],
(json \\ "subreddit").extract[String],
(json \\ "subreddit_id").extract[String],
(json \\ "ups").extract[Int])

}.saveToCassandra("reddit", tableName, SomeColumns("id","archived","author","body","controversiality", "created_utc","distinguished","downs", "gilded", "link_id", "name","parent_id","retrieved_on","score","score_hidden", "subreddit","subreddit_id","ups"))

	//println(reddits.take(1))

}

//sample post
/*
val bleh = """{"score_hidden":false,"name":"t1_cnas8zv","link_id":"t3_2qyr1a","body":"Most of us have some family members like this. *Most* of my family is like this. ","downs":0,"created_utc":"1420070400","score":14,"author":"YoungModern","distinguished":null,"id":"cnas8zv","archived":false,"parent_id":"t3_2qyr1a","subreddit":"exmormon","author_flair_css_class":null,"author_flair_text":null,"gilded":0,"retrieved_on":1425124282,"ups":14,"controversiality":0,"subreddit_id":"t5_2r0gj","edited":false}"""
