import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.net.Socket;
import java.net.UnknownHostException;
import java.net.InetAddress;

/**
 * Stellt Methoden zur Kommunikation mit dem Server bereit.
 * Überträgt Videos und registriert den Client, falls keine Videos vorhanden sind.
 */
public class SocketCommunication {

    public SocketCommunication() {}

    /**
     * Überträgt alle .mp4-Videos im angegebenen Ordner an den Server.
     * Registriert den Client, falls keine Videos vorhanden sind.
     * @param folderPath Pfad zum Video-Ordner
     * @throws UnknownHostException 
     */
    public void pingServer(String folderPath) throws UnknownHostException {
        String serverAddress = Config.get("server.address");
        int serverPort = Config.getInt("server.port");
        String piName = Config.get("pi.name");
        

        File folder = new File(folderPath);
        File[] videoFiles = folder.listFiles((dir, name) -> name.endsWith(".mp4"));

        if (videoFiles != null && videoFiles.length > 0) {
            for (File videoFile : videoFiles) {
                // Für jede Videodatei Verbindung aufbauen und übertragen
                try (
                        Socket socket = new Socket(serverAddress, serverPort);
                        DataOutputStream out = new DataOutputStream(socket.getOutputStream());
                        DataInputStream in = new DataInputStream(socket.getInputStream())
                ) {
                    System.out.println("Verbunden mit dem Server auf " + serverAddress + ":" + serverPort);

                    out.writeUTF("SEND_VIDEO");
                    String response = in.readUTF();
                    System.out.println("Server sagt: " + response);

                    if ("READY_TO_RECEIVE".equalsIgnoreCase(response)) {
                        System.out.println("Übertrage Video: " + videoFile.getName());
                        sendMetaData(out, videoFile);
                        sendVideo(out, videoFile);

                        String serverAck = in.readUTF();
                        System.out.println("Server-Antwort nach Video-Upload: " + serverAck);

                        if ("VIDEO_RECEIVED".equalsIgnoreCase(serverAck)) {
                            boolean deleted = videoFile.delete();
                            if (deleted) {
                                System.out.println("Video erfolgreich gelöscht: " + videoFile.getName());
                            } else {
                                System.err.println("Fehler beim Löschen des Videos: " + videoFile.getName());
                            }
                        } else {
                            System.err.println("Unerwartete Antwort vom Server: " + serverAck);
                        }
                    } else {
                        System.err.println("Server versteht die Anfrage nicht oder lehnt sie ab.");
                    }
                } catch (IOException e) {
                    System.err.println("Fehler bei der Kommunikation mit dem Server: " + e.getMessage());
                }
            }
        } else {
            // Keine Videos gefunden, nur Client registrieren
            System.out.println("Keine Videos im Ordner gefunden. Registriere nur Client...");
            try (
                    Socket socket = new Socket(serverAddress, serverPort);
                    DataOutputStream out = new DataOutputStream(socket.getOutputStream());
                    DataInputStream in = new DataInputStream(socket.getInputStream())
            ) {
                out.writeUTF("REGISTER_CLIENT");
                out.writeUTF("PI_NAME:" + piName);
                out.writeUTF("END_HEADER");

                String response = in.readUTF();
                System.out.println("Server-Antwort auf Registrierung: " + response);

            } catch (IOException e) {
                System.err.println("Fehler bei der Client-Registrierung: " + e.getMessage());
            }
        }
    }

    /**
     * Sendet Metadaten (PI-Name, Dateigröße) zum Server.
     * @param out DataOutputStream zum Server
     * @param videoFile Die zu übertragende Videodatei
     * @throws IOException falls ein Fehler beim Senden auftritt
     */
    public static void sendMetaData(DataOutputStream out, File videoFile) throws IOException {
        String piName = Config.get("pi.name");
        out.writeUTF("PI_NAME:" + piName);
        out.writeUTF("FILE_SIZE:" + videoFile.length());
        out.writeUTF("END_HEADER");

        System.out.println("Metadaten gesendet:");
        System.out.println("PI_NAME: " + piName);
        System.out.println("DATEIGRÖSSE: " + videoFile.length() + " Bytes");
    }

    /**
     * Überträgt die Videodatei als Bytestrom an den Server.
     * @param out DataOutputStream zum Server
     * @param videoFile Die zu übertragende Videodatei
     */
    public static void sendVideo(DataOutputStream out, File videoFile) {
        try (FileInputStream fileInputStream = new FileInputStream(videoFile)) {
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = fileInputStream.read(buffer)) != -1) {
                out.write(buffer, 0, bytesRead);
            }
            out.flush();
            System.out.println("Video erfolgreich gesendet!");
        } catch (IOException e) {
            System.err.println("Fehler beim Senden des Videos: " + e.getMessage());
        }
    }
}
