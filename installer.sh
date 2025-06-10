#!/bin/bash

set -e  # Script bei Fehler abbrechen
set -u  # Fehler bei Verwendung nicht gesetzter Variablen

echo "🚀 Starte PiWacheClient Setup..."

# System aktualisieren
echo "🔄 Aktualisiere Systempakete..."
sudo apt update
sudo apt full-upgrade -y

# Raspberry Pi Konfiguration (nur ausführen, wenn auf Pi)
if grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚙️ Raspberry Pi spezifische Konfiguration..."
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_ssh 0
    sudo raspi-config nonint do_serial_hw 0
    sudo raspi-config nonint do_serial_cons 1
    sudo raspi-config nonint do_onewire 0
    sudo systemctl disable hciuart
    echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt
else
    echo "ℹ️ Nicht auf einem Raspberry Pi – Hardware-Konfiguration wird übersprungen."
fi

# Nützliche Tools und Java Dependencies installieren
echo "📦 Installiere benötigte Pakete..."
sudo apt install -y i2c-tools vim git java-common libxi6 libxrender1 libxtst6

# Java installieren
echo "☕ Installiere Java Zulu JDK 21..."
cd ~/Downloads
wget https://cdn.azul.com/zulu/bin/zulu21.38.21-ca-jdk21.0.5-linux_arm64.deb
sudo dpkg -i zulu21.38.21-ca-jdk21.0.5-linux_arm64.deb
rm zulu21.38.21-ca-jdk21.0.5-linux_arm64.deb

# Java Version prüfen
java -version

# SDKMAN installieren
echo "📦 Installiere SDKMAN..."
curl -s "https://get.sdkman.io/" | bash
set +u
source "$HOME/.sdkman/bin/sdkman-init.sh"

# Maven installieren
echo "⚙️ Installiere Maven..."
sudo apt install maven

# Installationen prüfen
sdk version
mvn -v

# Python Abhängigkeiten installieren
echo "🐍 Installiere Python Abhängigkeiten..."
sudo apt install -y python3-opencv python3-pyaudio
pip install sounddevice --break-system-packages

# Projektverzeichnis annehmen
PROJECT_DIR="/home/berry/PiWacheClient"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Projektverzeichnis $PROJECT_DIR nicht gefunden! Bitte vorher klonen."
    exit 1
fi

# Konfigurationsdatei prüfen
CONFIG_FILE="$PROJECT_DIR/config.properties"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️ Konfigurationsdatei $CONFIG_FILE nicht gefunden!"
    echo "Bitte manuell anlegen oder kopieren."
else
    echo "✅ Konfigurationsdatei gefunden: $CONFIG_FILE"
    echo "Du kannst sie jetzt anpassen mit:"
    echo "nano $CONFIG_FILE"
fi

# Services einrichten
echo "🛠️ Erstelle Agent Service..."

sudo bash -c 'cat > /etc/systemd/system/agent.service' <<EOF
[Unit]
Description=Autostart fuer Agent.py
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/berry/PiWacheClient/src/main/python/Agent.py
WorkingDirectory=/home/berry/
StandardOutput=inherit
StandardError=inherit
Restart=always
User=berry
Group=video
Group=audio
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Agent Service erstellt."

# Java-Projekt kompilieren
echo "🛠️ Kompiliere Java-Projekt..."
cd /home/berry/PiWacheClient/src/main/java
javac Main.java
echo "✅ Java-Projekt kompiliert."

echo "🛠️ Erstelle Main Service..."

sudo bash -c 'cat > /etc/systemd/system/main.service' <<EOF
[Unit]
Description=Autostart fuer Main.java
After=network.target

[Service]
ExecStart=/usr/bin/java -cp /home/berry/PiWacheClient/src/main/java Main
WorkingDirectory=/home/berry/PiWacheClient
StandardOutput=inherit
StandardError=inherit
Restart=always
User=berry

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Main Service erstellt."

# Services aktivieren und starten
echo "🔄 Lade systemd neu..."
sudo systemctl daemon-reexec

echo "🚀 Aktiviere und starte Agent Service..."
sudo systemctl enable agent.service
sudo systemctl start agent.service

echo "🚀 Aktiviere und starte Main Service..."
sudo systemctl enable main.service
sudo systemctl start main.service

# Service-Status anzeigen
echo "📋 Status von agent.service:"
sudo systemctl status agent.service --no-pager

echo "📋 Status von main.service:"
sudo systemctl status main.service --no-pager

echo "✅ Setup und Service-Initialisierung abgeschlossen."

echo "ℹ️ Alle aktiven Services anzeigen mit:"
echo "systemctl list-unit-files --type=service --state=enabled"

echo "ℹ️ System ggf. neu starten, um alle Änderungen vollständig zu übernehmen."
