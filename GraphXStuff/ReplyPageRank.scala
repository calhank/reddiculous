import org.apache.spark.SparkContext
import org.apache.spark.rdd.RDD
import org.apache.spark.sql.{SQLContext,DataFrame,Row}
import org.apache.spark.sql.functions.monotonicallyIncreasingId
import org.apache.spark.graphx.{Graph,VertexId, VertexRDD,EdgeRDD,Edge}
import org.apache.hadoop.io.compress.BZip2Codec

object Main extends App {
  ///@brief Reddit API IDs have different prefixes to indicate what kind of
  /// entity is being identified. This turns out not to be all that
  /// important for the comments corpus.
  val id_re="^t([0-9])_".r
  def idType(x: String): (Int,String) = x match {
    case id_re(code) => (code.toInt,
      code.toInt match {
        case 1 => "Comment"
        case 2 => "Account"
        case 3 => "Link"
        case 4 => "Message"
        case 5 => "Subreddit"
        case 6 => "Award"
        case 8 => "PromoCampaign"
        case _ => "Unknown"
      })
    case _ => (0,"Unknown")
  }

  ///@brief I'm interested in patterns of replies (edges) between
  ///users (nodes), with reply being an edge from the user responding
  ///to the one to whom he or she is replying.  This is a multigraph,
  ///which the pagerank implementation handles perfectly well. The
  ///first step in creating this graph is to identify the edges and
  ///some metrics associated with the interaction.
  def genJoinedData(sqlContext: SQLContext) : DataFrame = {
    val parq_df=sqlContext.read.parquet("hdfs://final-gateway/w251/reddit-comments.parquet")
    parq_df.registerTempTable("reddit")
    val df=sqlContext.sql("""
SELECT t1.subreddit as Subreddit,
       t1.name   AS OrigId,                t2.name   AS RespId,
       t1.author AS OrigAuth,              t2.author AS RespAuth,
       t1.score  AS OrigScore,             t2.score  AS RespScore,
       t1.likes  AS OrigLikes,             t2.likes  AS RespLikes,
       t1.num_reports AS OrigReports,      t2.num_reports AS RespReports,
       t1.ups    AS OrigUps,               t2.ups    AS RespUps,
       t1.downs  AS OrigDowns,             t2.downs  AS RespDowns,
       t1.controversiality AS OrigControv, t2.controversiality AS RespControv
FROM reddit t1 INNER JOIN reddit t2 ON t1.name = t2.parent_id
""")
    df.write.parquet("hdfs://final-gateway/w251/reddit-comments-selfjoin.parquet")
    df.registerTempTable("reddit_selfjoin")
    df.cache
    df
  }

  def getJoinedData(sqlContext: SQLContext) : DataFrame = {
    val df=sqlContext.read.parquet("hdfs://final-gateway/w251/reddit-comments-selfjoin.parquet")
    df.registerTempTable("reddit_selfjoin")
    df.cache
    df
  }

  def connect(): (SparkContext,SQLContext) = {
    println("*** Starting spark connection")
    val sc=new SparkContext()
    (sc, new SQLContext(sc))
  }

  println("*** Startup")
  val (sc, sqlContext) = connect()
  //val df=genJoinedData(sqlContext)
  val df=getJoinedData(sqlContext)
  df.cache()
  println("*** Querying IDs, subreddits")
  // Some handy things
  val subreddits=sqlContext.sql("SELECT Subreddit, COUNT(*) AS Count FROM reddit_selfjoin GROUP BY Subreddit")
  val pop_subreddits = subreddits.where(subreddits("Count") > 1000)
  pop_subreddits.registerTempTable("subreddit_names")
  val ids=sqlContext.sql("""
SELECT RespAuth as Auth FROM reddit_selfjoin
WHERE RespAuth IS NOT NULL AND RespAuth != '[deleted]'
UNION
SELECT OrigAuth as Auth FROM reddit_selfjoin
WHERE OrigAuth IS NOT NULL AND OrigAuth != '[deleted]'
""")
    .distinct()
    .withColumn("id", monotonicallyIncreasingId())
  ids.registerTempTable("userids")

  println("*** Selecting edges")
  
  pop_subreddits.collect.foreach((row:Row)=>{
    val subreddit=row.getAs[String]("Subreddit")
    val messageCount=row.getAs[Long]("Count")
    println(s"Processing PageRank for ${subreddit} (${messageCount} messages)")
    val edges=sqlContext.sql(s"""
SELECT resp.id as RespId,orig.id as OrigId,RespAuth,OrigAuth,RespScore
FROM reddit_selfjoin
  INNER JOIN userids resp ON RespAuth=resp.Auth
  INNER JOIN userids orig ON OrigAuth=orig.Auth
WHERE Subreddit = '${subreddit}'""")
    // Again, we consider a reply to be an arrow from the replying user
    // to the originally posting user, with each interaction as a
    // parallel edge.
    println("*** Declaring edge RDD")
    val edge_rdd=EdgeRDD.fromEdges(
      edges.map(
        (row: Row) => Edge(
          row.getAs[Long]("RespId"),
          row.getAs[Long]("OrigId"),
          row)
      ))
    println("*** Declaring vertex RDD")
    val vert_rdd=VertexRDD(
      ids.rdd.map((x:Row)=>(x.getAs[Long]("id"), x.getAs[String]("Auth"))),
      edge_rdd, "Unknown",
      (v1:String, v2:String) => v1)

    println("*** Declaring graph RDD")
    val g=Graph(vert_rdd, edge_rdd)

    {
      println("*** Running 10 rounds of PageRank")
      val pr=g.ops.staticPageRank(10)
      println("*** Joining results with vertex RDD")
      val ext=pr.vertices.innerZipJoin(vert_rdd) {
        case (vid,rank,name)=>(rank,name)
      }.map {
        case (x:VertexId, y:(Double,String)) => y
      }.sortByKey(true)
      println("*+** Saving")
      ext.saveAsTextFile(s"hdfs://final-gateway/w251/reddit-pagerank/${subreddit}", classOf[BZip2Codec])
      println(subreddit)
      println(ext.take(20).mkString("\n"))
    }
  })
//  val ext=sqlContext.readsqlContext.read.format("com.databricks.spark.csv"
//  ).option("header", "true"
//  ).option("inferSchema", "true"
//  ).load("hdfs://final-gateway/w251/reddit-wtf-pr.txt.bz2")
}
