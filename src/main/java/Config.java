

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class Config {

    private static final Properties properties = new Properties();

    static {
        try {
            FileInputStream input = new FileInputStream("config.properties"); 
            properties.load(input);
            input.close();
        } catch (IOException e) {
            System.err.println("Fehler beim Laden der Konfiguration: " + e.getMessage());
        }
    }

    public static String get(String key) {
        return properties.getProperty(key);
    }

    public static int getInt(String key) {
        return Integer.parseInt(properties.getProperty(key));
    }
}
