package PiVideos;

import java.io.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class Main {
    public static void main(String[] args) throws InterruptedException { //Exception kann wieder entfernt werden

        // Pfad der output-Datei
        final String FOLDERPATH = "C:/Users/hecht/Videos/vids";

        // try {

        SocketCommunication socket = new SocketCommunication();

        // Erstellen eines ScheduledExecutorService mit einem Pool von 1 Thread
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        // Definieren der Aufgabe, die alle 3 Minuten ausgeführt werden soll
        Runnable task = new Runnable() {
            @Override
            public void run() {
                // Hier kannst du den Code einfügen, der alle 3 Minuten ausgeführt werden soll
                System.out.println("Aufgabe ausgeführt: " + System.currentTimeMillis());
                
                socket.pingServer(FOLDERPATH);
              
            }
        };

        // Planen der Aufgabe, die alle 3 Minuten ausgeführt wird
        scheduler.scheduleAtFixedRate(task, 0, 1, TimeUnit.MINUTES);

            // // Python-Skript zur Bewegungserkennung/Videoaufnahme bauen und ausführen
            // ProcessBuilder builder = new ProcessBuilder("python3", "/home/berry/PIWacheClient/src/main/java/PiVideos/Detect_motion_and_record.py");
            // builder.redirectErrorStream(true);
            // Process process = builder.start();

            // // Konsolenausgaben des Python-Codes ausgeben
            // BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            // String line;
            // while ((line = reader.readLine()) != null) {
            //     System.out.println(line);
            // }

            // int exitCode = process.waitFor();
            // System.out.println("Python-Skript beendet mit Code: " + exitCode);

            // // aufgenommenes Video an ServerPi versenden
            // SocketCommunication socketCommunication = new SocketCommunication();
            // socketCommunication.pingServer(FOLDERPATH);
            

        // } catch (IOException | InterruptedException e) {
        //     e.printStackTrace();
        // }
    }
}