lazy val common = Seq(
  organization := "week9.mids",
  version := "0.1.0",
  scalaVersion := "2.11.7",
  libraryDependencies ++= Seq(
    "org.apache.spark" %% "spark-core" % "1.5.2",
    "org.apache.spark" %% "spark-graphx" % "1.5.2",
    "org.apache.spark" %% "spark-sql" % "1.5.2",
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
    name := "GraphXSandbox",
    mainClass in (Compile, run) := Some("GraphXSandbox.Main"))
