# SSL-Zertifikat Austausch Playbook

Dieses Ansible-Playbook automatisiert den Austausch von SSL-Zertifikaten auf verschiedenen Betriebssystemen (Debian/Ubuntu, RHEL/CentOS, SUSE, Windows) für Apache, Nginx oder IIS Webserver.

## Voraussetzungen

- Ansible 2.9 oder neuer
- SSH- oder WinRM-Zugriff auf die Zielhosts
- Zertifikatsdateien (*.crt) im Eingangsordner auf dem Ansible Control Host
- Root- oder Administratorrechte auf den Zielhosts
- Installierte Pakete auf Zielhosts:
  - Debian/Ubuntu: `apache2` oder `nginx`
  - RHEL/CentOS: `httpd` oder `nginx`
  - SUSE: `apache2` oder `nginx`
  - Windows: IIS (W3SVC-Dienst)

## Verzeichnisstruktur

```plaintext
/pfad/zum/zertifikat/           # Eingangsordner für neue Zertifikate (*.crt)
/pfad/zum/erledigt_ordner/      # Zielordner für verarbeitete Zertifikate
```

## Dateinamenkonvention

Zertifikatsdateien müssen den Hostnamen im Dateinamen enthalten, z. B.:
- `zertifikat_hostname.crt`
- Der Hostname wird extrahiert und mit `inventory_hostname` abgeglichen.

## Playbook-Beschreibung

1. **Zertifikate finden**: Sucht nach `*.crt`-Dateien im Eingangsordner auf dem Control Host.
2. **Hostnamen extrahieren**: Extrahiert den Hostnamen aus dem Dateinamen der Zertifikate.
3. **Zertifikat austauschen**:
   - **Linux (Debian/Ubuntu, RHEL/CentOS, SUSE)**:
     - Kopiert das Zertifikat in den entsprechenden Ordner (`/etc/apache2/ssl/`, `/etc/httpd/ssl/` oder `/etc/nginx/ssl/`).
     - Startet den Webserver neu (`apache2`, `httpd` oder `nginx`).
   - **Windows**:
     - Prüft, ob IIS (W3SVC) vorhanden ist.
     - Kopiert das Zertifikat temporär nach `C:\Windows\Temp\`.
     - Importiert das Zertifikat in den `WebHosting`-Speicher.
     - Aktualisiert die IIS-Webbindung für HTTPS.
     - Startet IIS neu.
     - Unterstützt OpenSSH (Port 22) oder WinRM (Port 5985) für die Verbindung.
4. **Zertifikat verschieben**: Verschiebt verarbeitete Zertifikate in den Erledigt-Ordner.
5. **Original löschen**: Entfernt die Originalzertifikate aus dem Eingangsordner.

## Verwendung

1. Passe die Pfade in den Variablen `/pfad/zum/zertifikat` und `/pfad/zum/erledigt_ordner` an.
2. Stelle sicher, dass die Zertifikate im Eingangsordner liegen und die Dateinamen den Hostnamen enthalten.
3. Führe das Playbook aus:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Wichtige Hinweise

- Das Playbook prüft, ob der Hostname im Zertifikatsdateinamen mit dem `inventory_hostname` übereinstimmt.
- Auf Windows wird geprüft, ob eine Verbindung über OpenSSH oder WinRM möglich ist.
- Fehler werden protokolliert, wenn keine Verbindung zum Windows-Host hergestellt werden kann.
- Das Playbook sammelt Fakten (`gather_facts: yes`), um Betriebssystem und installierte Pakete zu erkennen.
- Stelle sicher, dass die Zielverzeichnisse auf den Hosts existieren (z. B. `/etc/apache2/ssl/` oder `/etc/nginx/ssl/`).

## Einschränkungen

- Unterstützt nur Apache, Nginx und IIS.
- Zertifikate müssen im `.crt`-Format vorliegen.
- Windows benötigt entweder OpenSSH oder WinRM für die Kommunikation.
- Keine Unterstützung für benutzerdefinierte Zertifikatsspeicherorte oder Webserver-Konfigurationen.

## Fehlerbehandlung

- Wenn ein Zertifikat nicht für den aktuellen Host ist, wird es übersprungen.
- Wenn keine Verbindung zu einem Windows-Host möglich ist, wird ein Fehler ausgegeben.
- Das Playbook überschreibt vorhandene Zertifikate im Zielordner nur, wenn sie sich geändert haben.