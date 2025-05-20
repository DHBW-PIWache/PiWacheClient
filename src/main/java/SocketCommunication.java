


import java.io.*;
import java.net.Socket;

/*******************************************************************************************************
 Autor: Julian Hecht
 Datum letzte Änderung: 10.05.2025
 Änderung: Registriert Client, auch wenn keine Videos vorhanden sind
 *******************************************************************************************************/

public class SocketCommunication {

    public SocketCommunication() {}


    public void pingServer(String folderPath) {

        String serverAddress = Config.get("server.address");
        int serverPort = Config.getInt("server.port");
        String piName = Config.get("pi.name");

        File folder = new File(folderPath);
        File[] videoFiles = folder.listFiles((dir, name) -> name.endsWith(".mp4"));

        if (videoFiles != null && videoFiles.length > 0) {
            for (File videoFile : videoFiles) {

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


    public static void sendMetaData(DataOutputStream out, File videoFile) throws IOException {
        String piName = Config.get("pi.name");

        out.writeUTF("PI_NAME:" + piName);
        out.writeUTF("FILE_SIZE:" + videoFile.length());
        out.writeUTF("END_HEADER");

        System.out.println("Metadaten gesendet:");
        System.out.println("PI_NAME: " + piName);
        System.out.println("DATEIGRÖSSE: " + videoFile.length() + " Bytes");
    }


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
