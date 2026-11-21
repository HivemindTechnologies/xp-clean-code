import java.time.{Instant, LocalDate}
import java.util.UUID
import scala.io.Source
import scala.util.Random

object Impure {
  def stamp(): Long =
    // ruleid: scala-clock
    System.currentTimeMillis()

  def stampWithoutParentheses: Long =
    // ruleid: scala-clock
    System.currentTimeMillis

  def instantWithoutParentheses: Instant =
    // ruleid: scala-clock
    Instant.now

  def today(): LocalDate =
    // ruleid: scala-clock
    LocalDate.now()

  def instant(): Instant =
    // ruleid: scala-clock
    java.time.Instant.now()

  def roll(): Int =
    // ruleid: scala-random
    Random.nextInt(6)

  def id(): UUID =
    // ruleid: scala-random
    UUID.randomUUID()

  def home(): Option[String] =
    // ruleid: scala-environment
    sys.env.get("HOME")

  def tz(): String =
    // ruleid: scala-environment
    System.getenv("TZ")

  def read(path: String): String =
    // ruleid: scala-io
    Source.fromFile(path).mkString

  def log(message: String): Unit =
    // ruleid: scala-io
    println(message)

  def count(xs: List[Int]): Int = {
    // ruleid: scala-var
    var total = 0
    xs.foreach(x => total += x)
    total
  }

  // ruleid: scala-var
  private var cache: Map[String, Int] = Map.empty

  def countTyped(xs: List[Int]): Int = {
    // ruleid: scala-var
    var total: Int = 0
    xs.foreach(x => total += x)
    total
  }
}

object Pure {
  // ok: scala-var
  val limit = 10

  // ok: scala-var
  val typed: Int = 10

  def lines(path: String): List[String] = {
    // ok: scala-var
    val parsed: List[String] = List(path)
    parsed
  }

  // ok: scala-var
  val variance = 1 // a name that starts with "var"

  // ok: scala-clock
  def age(now: Instant, born: Instant): Long = now.getEpochSecond - born.getEpochSecond

  // ok: scala-random
  def roll(random: Random): Int = random.nextInt(6)

  // ok: scala-var
  def total(xs: List[Int]): Int = xs.sum
}
