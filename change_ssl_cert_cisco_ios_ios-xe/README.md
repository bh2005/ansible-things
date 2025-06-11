# SSL-Zertifikat Austausch Playbook für Cisco-Switches

Dieses Ansible-Playbook automatisiert den Austausch von SSL-Zertifikaten auf Cisco-Switches mit IOS oder IOS-XE für die HTTPS-Management-Schnittstelle.

## Voraussetzungen

- Ansible 2.9 oder neuer
- `cisco.ios`-Collection (`ansible-galaxy collection install cisco.ios`)
- SSH-Zugriff auf die Cisco-Switches mit Enable-Modus
- Zertifikatsdateien (*.crt) und optional private Schlüssel (*.p12) im Eingangsordner auf dem Ansible Control Host
- Privilegierte Rechte (Enable-Modus) auf den Switches
- Cisco-Switches mit IOS/IOS-XE, die HTTPS und `crypto pki` unterstützen

## Verzeichnisstruktur

```plaintext
/pfad/zum/zertifikat/           # Eingangsordner für neue Zertifikate (*.crt, *.p12)
/pfad/zum/erledigt_ordner/      # Zielordner für verarbeitete Zertifikate
```

## Dateinamenkonvention

Zertifikatsdateien müssen den Hostnamen im Dateinamen enthalten, z. B.:
- `zertifikat_hostname.crt` (Zertifikat im PEM-Format)
- Optional: `zertifikat_hostname.p12` (PKCS12-Datei mit Zertifikat und Schlüssel)
- Der Hostname wird extrahiert und mit `inventory_hostname` abgeglichen.

## Playbook-Beschreibung

1. **Zertifikate finden**: Sucht nach `*.crt`-Dateien im Eingangsordner auf dem Control Host.
2. **Hostnamen extrahieren**: Extrahiert den Hostnamen aus dem Dateinamen der Zertifikate.
3. **Zertifikat austauschen**:
   - Erstellt oder aktualisiert einen Trustpoint (`crypto pki trustpoint`).
   - Importiert das Zertifikat (PEM-Format) und optional den privaten Schlüssel (PKCS12).
   - Konfiguriert den HTTPS-Server mit dem neuen Trustpoint.
   - Speichert die Konfiguration persistent.
4. **Zertifikat verschieben**: Verschiebt verarbeitete Zertifikate in den Erledigt-Ordner.
5. **Original löschen**: Entfernt die Originalzertifikate aus dem Eingangsordner.

## Verwendung

1. Passe die Pfade in `cert_input_path` und `cert_done_path` im Playbook an.
2. Stelle sicher, dass die Zertifikate im Eingangsordner liegen und die Dateinamen den Hostnamen enthalten.
3. Konfiguriere die Inventargruppe `cisco_switches` mit SSH-Zugangsdaten und Enable-Passwort.
4. Führe das Playbook aus:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Wichtige Hinweise

- Das Playbook prüft, ob der Hostname im Zertifikatsdateinamen mit dem `inventory_hostname` übereinstimmt.
- Der Enable-Modus wird für Konfigurationsänderungen benötigt (`become: yes`, `become_method: enable`).
- Zertifikate müssen im PEM-Format vorliegen; private Schlüssel optional als PKCS12.
- Teste das Playbook in einer Laborumgebung, bevor es in der Produktion eingesetzt wird.
- Stelle sicher, dass der HTTPS-Server auf dem Switch aktiviert ist (`ip http secure-server`).

## Einschränkungen

- Unterstützt nur Cisco-Switches mit IOS/IOS-XE.
- Zertifikate müssen im `.crt`-Format (PEM) vorliegen; Schlüssel optional als `.p12`.
- Keine Unterstützung für andere Protokolle (z. B. SNMP-basierte Zertifikatsverwaltung).
- Ein Neustart des Switches ist möglicherweise erforderlich, wenn der HTTPS-Server nicht korrekt aktualisiert wird.

## Fehlerbehandlung

- Wenn ein Zertifikat nicht für den aktuellen Host ist, wird es übersprungen.
- Fehler beim Zertifikatsimport (z. B. ungültiges Format) werden protokolliert.
- Das Playbook speichert die Konfiguration nur, wenn Änderungen vorgenommen wurden.

## Quellen

- Cisco IOS-Konfiguration für Zertifikate: [Ansible-Dokumentation für cisco.ios](https://docs.ansible.com/ansible/latest/collections/cisco/ios/ios_config_module.html)
- Zertifikatsimport für Cisco-Geräte: [Cisco Community](https://community.cisco.com/t5/networking-knowledge-base/generating-rsa-keys-certificates-using-ansible/td-p/4683548)