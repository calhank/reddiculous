lazy val common = Seq(
  organization := "week9.mids",
  version := "0.1.0",
  scalaVersion := "2.10.4",
  libraryDependencies ++= Seq(
    "org.apache.spark" %% "spark-core" % "1.5.0",
    "org.apache.spark" %% "spark-graphx" % "1.5.0",
    "org.json4s" %% "json4s-native" % "3.3.0"
  ),
  mergeStrategy in assembly <<= (mergeStrategy in assembly) { (old) =>
     {
      case PathList("META-INF", xs @ _*) => MergeStrategy.discard
      case x => MergeStrategy.first
     }
  }
)

lazy val twitter_popularity = (project in file(".")).
  settings(common: _*).
  settings(
    name := "SentimentAnalysis",
    mainClass in (Compile, run) := Some("SentimentAnalysis.Main"))
