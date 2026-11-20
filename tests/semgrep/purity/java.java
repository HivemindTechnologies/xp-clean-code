import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Random;
import java.util.UUID;

class Impure {
    // ruleid: java-static-mutable-field
    private static int counter = 0;

    // ok: java-static-mutable-field
    private static final int LIMIT = 10;

    long stamp() {
        // ruleid: java-clock
        return System.currentTimeMillis();
    }

    Instant instant() {
        // ruleid: java-clock
        return Instant.now();
    }

    LocalDate today() {
        // ruleid: java-clock
        return LocalDate.now();
    }

    int roll() {
        // ruleid: java-random
        return new Random().nextInt(6);
    }

    UUID id() {
        // ruleid: java-random
        return UUID.randomUUID();
    }

    String tz() {
        // ruleid: java-environment
        return System.getenv("TZ");
    }

    String read(Path path) throws Exception {
        // ruleid: java-io
        return Files.readString(path);
    }

    void log(String message) {
        // ruleid: java-io
        System.out.println(message);
    }
}

class Pure {
    // ok: java-clock
    long age(Instant now, Instant born) { return now.getEpochSecond() - born.getEpochSecond(); }

    // ok: java-random
    int roll(Random random) { return random.nextInt(6); }
}
