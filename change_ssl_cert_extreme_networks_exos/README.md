# SSL-Zertifikat Austausch Playbook für Extreme Networks EXOS-Switches

Dieses Ansible-Playbook automatisiert den Austausch von SSL-Zertifikaten auf Extreme Networks Switches mit EXOS für die HTTPS-Management-Schnittstelle.

## Voraussetzungen

- Ansible 2.9 oder neuer
- `community.network`-Collection (`ansible-galaxy collection install community.network`)
- SSH-Zugriff auf die EXOS-Switches mit Enable-Modus (oder HTTP-API aktiviert)
- Zertifikatsdateien (*.crt) und optional private Schlüssel (*.key) im Eingangsordner auf dem Ansible Control Host
- Privilegierte Rechte (Enable-Modus) auf den Switches
- Extreme Networks Switches mit EXOS, die HTTPS und SSL-Zertifikate unterstützen

## Verzeichnisstruktur

```plaintext
/pfad/zum/zertifikat/           # Eingangsordner für neue Zertifikate (*.crt, *.key)
/pfad/zum/erledigt_ordner/      # Zielordner für verarbeitete Zertifikate
```

## Dateinamenkonvention

Zertifikatsdateien müssen den Hostnamen im Dateinamen enthalten, z. B.:
- `zertifikat_hostname.crt` (Zertifikat im PEM-Format)
- Optional: `zertifikat_hostname.key` (Privater Schlüssel im PEM-Format)
- Der Hostname wird extrahiert und mit `inventory_hostname` abgeglichen.

## Playbook-Beschreibung

1. **Zertifikate finden**: Sucht nach `*.crt`-Dateien im Eingangsordner auf dem Control Host.
2. **Hostnamen extrahieren**: Extrahiert den Hostnamen aus dem Dateinamen der Zertifikate.
3. **Zertifikat austauschen**:
   - Lädt das Zertifikat mit `configure ssl certificate`.
   - Lädt den privaten Schlüssel (falls vorhanden) mit `configure ssl privkey`.
   - Aktiviert den HTTPS-Server (`enable web https`).
   - Startet den Webprozess neu (`restart process web`).
   - Speichert die Konfiguration persistent (`save configuration`).
4. **Zertifikat verschieben**: Verschiebt verarbeitete Zertifikate in den Erledigt-Ordner.
5. **Original löschen**: Entfernt die Originalzertifikate aus dem Eingangsordner.

## Verwendung

1. Passe die Pfade in `cert_input_path` und `cert_done_path` im Playbook an.
2. Stelle sicher, dass die Zertifikate im Eingangsordner liegen und die Dateinamen den Hostnamen enthalten.
3. Konfiguriere die Inventargruppe `extreme_switches` mit SSH-Zugangsdaten und Enable-Passwort.
4. Führe das Playbook aus:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Wichtige Hinweise

- Das Playbook prüft, ob der Hostname im Zertifikatsdateinamen mit dem `inventory_hostname` übereinstimmt.
- Der Enable-Modus wird für Konfigurationsänderungen benötigt (`become: yes`, `become_method: enable`).
- Zertifikate und Schlüssel müssen im PEM-Format vorliegen.
- Teste das Playbook in einer Laborumgebung, bevor es in der Produktion eingesetzt wird.
- Stelle sicher, dass der HTTPS-Server auf dem Switch aktiviert ist (`enable web https`).
- Für HTTP-API-Zugriff ändere die Verbindung zu `ansible_connection: ansible.netcommon.httpapi` und konfiguriere die API-Credentials.

## Einschränkungen

- Unterstützt nur Extreme Networks Switches mit EXOS.
- Zertifikate müssen im `.crt`-Format (PEM) vorliegen; Schlüssel als `.key` (PEM).
- Keine direkte Unterstützung für PKCS12-Dateien oder komplexe Zertifikatsketten.
- Der Webprozess-Neustart kann den HTTPS-Zugriff kurzzeitig unterbrechen.
- Begrenzte Flexibilität der `exos_command`- und `exos_config`-Module im Vergleich zu Cisco-Modulen.

## Fehlerbehandlung

- Wenn ein Zertifikat nicht für den aktuellen Host ist, wird es übersprungen.
- Fehler beim Zertifikatsimport (z. B. ungültiges Format) werden protokolliert.
- Die Konfiguration wird nur bei Änderungen gespeichert, um unnötige Schreibvorgänge zu vermeiden.

## Quellen

- Ansible-Dokumentation für EXOS: [community.network.exos_command](https://docs.ansible.com/ansible/latest/collections/community/network/exos_command_module.html)
- Extreme Networks EXOS-Befehle: [Extreme Networks Dokumentation](https://www.extremenetworks.com/support/documentation/)
- Ansible Extreme Networks Beispiele: [GitHub extremenetworks/ansible-extreme](https://github.com/extremenetworks/ansible-extreme)
