/** Utilities for loading and parsing data */

package thunder.util

import thunder.util.io.Parser
import thunder.util.io.PreProcessor
import thunder.util.io.hadoop.FixedLengthBinaryInputFormat
import org.apache.spark.rdd.RDD
import org.apache.spark.SparkContext
import org.apache.spark.SparkContext._
import org.apache.hadoop.io.{BytesWritable, LongWritable}
import java.nio.{ByteOrder, ByteBuffer}

object Load {

  /**
   * Load data from a text file with format
   * <t1> <t2> ...
   * where <t1> <t2> ... are the data values
   *
   * @param sc SparkContext
   * @param dir Directory to the input data files
   * @param preProcessMethod Method for pre processing data (default = "raw")
   * @return An RDD of data with values, RDD[(Array[Double])]
   */
  def fromText(sc: SparkContext,
                       dir: String,
                       preProcessMethod: String = "raw"): RDD[Array[Double]] = {
    val parser = new Parser(0)

    if (preProcessMethod != "raw") {
      val processor = new PreProcessor(preProcessMethod)
      sc.textFile(dir).map(parser.get).map(processor.get)
    } else {
      sc.textFile(dir).map(parser.get)
    }
  }

  /**
   * Load keyed data from a text file with format
   * <k1> <k2> ... <t1> <t2> ...
   * where <k1> <k2> ... are keys and <t1> <t2> ... are the data values
   *
   * @param sc SparkContext
   * @param dir Directory to the input data files
   * @param preProcessMethod Method for pre processing data (default = "raw")
   * @param nKeys Number of keys per data point (default = 3)
   * @return An RDD of data with keys and values, RDD[(Array[Int], Array[Double])]
   */
  def fromTextWithKeys(sc: SparkContext,
               dir: String,
               preProcessMethod: String = "raw",
               nKeys: Int = 3): RDD[(Array[Int], Array[Double])] = {
    val parser = new Parser(nKeys)

    if (preProcessMethod != "raw") {
      val processor = new PreProcessor(preProcessMethod)
      sc.textFile(dir).map(parser.getWithKeys).mapValues(processor.get)
    } else {
      sc.textFile(dir).map(parser.getWithKeys)
    }
  }

  // TODO Make number of bytes per record an argument
  /**
   * Load data from a flat binary file, assuming each record is a set of integers
   * with a total of 8 bytes per record
   *
   * @param sc SparkContext
   * @param dir Directory to the input data files
   * @param preProcessMethod Method for pre processing data (default = "raw")
   * @return An RDD of data with values, RDD[(Array[Double])]
   */
  def fromBinary(sc: SparkContext,
               dir: String,
               preProcessMethod: String = "raw"): RDD[Array[Double]] = {
    val parser = new Parser(0)
    val lines = sc.newAPIHadoopFile[LongWritable, BytesWritable, FixedLengthBinaryInputFormat](dir)
    val data = lines.map{ case (k, v) => v.getBytes}

    if (preProcessMethod != "raw") {
      val processor = new PreProcessor(preProcessMethod)
      data.map(parser.get).map(processor.get)
    } else {
      data.map(parser.get)
    }
  }

  // TODO Make number of bytes per record an argument
  /**
   * Load data from a flat binary file, assuming each record is a set of Integers
   * with a total of 8 bytes per record, and the first integers in each record are the keys
   * and the remaining integers are the values
   *
   *
   * @param sc SparkContext
   * @param dir Directory to the input data files
   * @param preProcessMethod Method for pre processing data (default = "raw")
   * @return An RDD of data with values, RDD[(Array[Double])]
   */
  def fromBinaryWithKeys(sc: SparkContext,
                 dir: String,
                 preProcessMethod: String = "raw",
                 nKeys: Int = 3): RDD[(Array[Int], Array[Double])] = {

    val parser = new Parser(nKeys)
    val lines = sc.newAPIHadoopFile[LongWritable, BytesWritable, FixedLengthBinaryInputFormat](dir)
    val data = lines.map{ case (k, v) => v.getBytes}

    if (preProcessMethod != "raw") {
      val processor = new PreProcessor(preProcessMethod)
      data.map(parser.getWithKeys).mapValues(processor.get)
    } else {
      data.map(parser.getWithKeys)
    }
  }

 }


