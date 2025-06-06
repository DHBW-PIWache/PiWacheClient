import java.net.UnknownHostException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Einstiegspunkt der Anwendung.
 * Führt periodisch eine Aufgabe aus, die mit dem Server kommuniziert.
 */
public class Main {
    public static void main(String[] args) {
        // Pfad zum überwachten Ordner (ggf. aus Config laden)
        final String FOLDERPATH = "/home/berry/Videos";

        // Initialisierung der Socket-Kommunikation
        SocketCommunication socket = new SocketCommunication();

        // ExecutorService für periodische Aufgaben (ein Thread)
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        // Aufgabe, die periodisch ausgeführt wird
        Runnable task = () -> {
            System.out.println("Aufgabe ausgeführt: " + System.currentTimeMillis());
            try {
                socket.pingServer(FOLDERPATH);
            } catch (UnknownHostException e) {
                e.printStackTrace();
            }
        };

        // Aufgabe alle 1 Minute ausführen (Initialverzögerung: 0)
        int sending_interval = Integer.parseInt(Config.get("sending.interval"));
        scheduler.scheduleAtFixedRate(task, 0, sending_interval, TimeUnit.MINUTES);
    }
}