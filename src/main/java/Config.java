import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

/**
 * Utility-Klasse zum Laden und Auslesen von Konfigurationseigenschaften aus einer Datei.
 */
public class Config {

    // Properties-Objekt zum Speichern der geladenen Konfigurationen
    private static final Properties properties = new Properties();

    // Statischer Initialisierer lädt die Konfiguration beim ersten Zugriff
    static {
        try (FileInputStream input = new FileInputStream("config.properties")) {
            properties.load(input);
        } catch (IOException e) {
            System.err.println("Fehler beim Laden der Konfiguration: " + e.getMessage());
        }
    }

    /**
     * Gibt den Wert einer Konfigurationseigenschaft als String zurück.
     * @param key Der Schlüssel der Eigenschaft
     * @return Der Wert als String oder null, falls nicht gefunden
     */
    public static String get(String key) {
        return properties.getProperty(key);
    }

    /**
     * Gibt den Wert einer Konfigurationseigenschaft als int zurück.
     * @param key Der Schlüssel der Eigenschaft
     * @return Der Wert als int oder 0, falls nicht gefunden oder ungültig
     */
    public static int getInt(String key) {
        String value = properties.getProperty(key);
        if (value == null) {
            return 0;
        }
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            System.err.println("Ungültiger Integer-Wert für '" + key + "': " + value);
            return 0;
        }
    }
}
