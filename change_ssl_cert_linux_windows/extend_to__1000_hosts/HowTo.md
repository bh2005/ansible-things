# HowTo: Generierung und Austausch von SSL-Zertifikaten für ca. 1000 Hosts mit Ansible

Dieses HowTo beschreibt, wie du mit zwei Ansible-Playbooks Certificate Signing Requests (CSRs) für ca. 1000 Hosts generierst und signierte SSL-Zertifikate auf Linux (Apache/Nginx) und Windows (IIS) austauschst. Die CSRs werden dynamisch aus einer CSV-Datei erstellt, und das Austausch-Playbook unterstützt sowohl WinRM als auch OpenSSH für Windows-Hosts. Eine Beispiel-CSV-Datei (`example.csv`) dient als Vorlage für die Konfiguration.

## Voraussetzungen

- **Ansible**: Version 2.9 oder neuer
- **Collections**:
  - `community.crypto`: Für OpenSSL-Operationen.
  - `community.general`: Für CSV-Verarbeitung.
  - Installiere mit:
    ```bash
    ansible-galaxy collection install community.crypto community.general
    ```
- **Python-Module**: `pyOpenSSL` oder `cryptography`:
  ```bash
  pip install pyOpenSSL cryptography
  ```
- **OpenSSL**: Auf dem Ansible Control Host installiert.
- **Inventar**: `inventory.yml` mit ca. 1000 Hosts, gruppiert nach Plattform (z. B. `linux_hosts`, `windows_hosts`).
- **CSV-Datei**: `data/hostnames.csv` mit Hostnamen und CSR-Attributen (basierend auf `example.csv`).
- **Verbindung**:
  - Linux: SSH-Zugriff (Port 22).
  - Windows: WinRM (Port 5985) oder OpenSSH (Port 22).
- **Schreibrechte**: Für `/pfad/zum/zertifikat` und `/pfad/zum/erledigt_ordner` auf dem Control Host.
- **Speicherplatz**: Ca. 3 MB für 1000 CSRs, Schlüssel und PFX-Dateien.

## Verzeichnisstruktur

### Eingabedateien
```plaintext
project_directory/
  ├── data/
  │   └── hostnames.csv  # Basierend auf example.csv
  ├── vars/
  │   └── csrs.yml       # Variablen für CSR-Generierung
  ├── inventory.yml      # Ansible-Inventar
  ├── generate_csrs.yml  # Playbook für CSR-Generierung
  └── ssl_certificate_exchange.yml  # Playbook für Zertifikats-Austausch
```

### Ausgabedateien
```plaintext
/pfad/zum/zertifikat/
  ├── webserver1.example.com/
  │   ├── webserver1.example.com.key
  │   ├── webserver1.example.com.csr
  │   └── webserver1.example.com.pfx  # Für Windows
  ├── zertifikat_webserver1.example.com.crt
  └── /pfad/zum/erledigt_ordner/
      ├── zertifikat_webserver1.example.com.crt
      ├── webserver1.example.com.key
      ├── webserver1.example.com.pfx
```

## Konfiguration

1. **CSV-Datei erstellen (`data/hostnames.csv`)**:
   - Verwende die Beispiel-CSV-Datei als Vorlage:
     ```csv
     common_name,country,state,locality,organization,organizational_unit,email_address,subject_alt_names,private_key_size,private_key_type,private_key_passphrase
     webserver1.example.com,DE,Hessen,Alheim,Meine Web-Firma GmbH,Webteam,webmaster@example.com,"DNS:www.webserver1.example.com,DNS:app.webserver1.example.com",2048,RSA,
     database.internal.com,DE,Hessen,Alheim,Meine DB-Firma AG,Datenbanken,dbadmin@internal.com,IP:10.0.0.10,2048,RSA,
     mailserver.mycompany.local,US,New York,New York City,My Corp Inc.,Email Services,postmaster@mycompany.local,"DNS:autodiscover.mycompany.local,DNS:mail.mycompany.local",4096,RSA,secret_passphrase
     winserver1.example.com,DE,Bayern,Muenchen,Meine Firma GmbH,IT,admin@example.com,"DNS:www.winserver1.example.com",2048,RSA,
     api.server.company.net,FR,Ile-de-France,Paris,Tech Corp SAS,API Team,api@company.net,"DNS:api2.server.company.net,IP:192.168.1.100",2048,EC,api_secure123
     frontend.app.local,UK,London,London,App Ltd,Frontend,frontend@app.local,"DNS:www.app.local",2048,RSA,
     backend.app.local,UK,London,London,App Ltd,Backend,backend@app.local,IP:10.0.0.20,4096,RSA,
     winapp1.internal.net,US,California,San Francisco,Enterprise Inc.,Applications,apps@internal.net,"DNS:app1.internal.net",2048,RSA,winapp_secure
     gateway.example.org,DE,Nordrhein-Westfalen,Duesseldorf,Security GmbH,Network,gwadmin@example.org,"DNS:gw1.example.org,DNS:gw2.example.org",2048,RSA,
     monitor.systems.local,CH,Zurich,Zurich,Systems AG,Monitoring,monitor@systems.local,IP:172.16.0.5,2048,EC,
     ```
   - Erweitere die Datei für ca. 1000 Hosts in einer Tabellenkalkulation oder mit einem Skript (siehe "Erweiterung der CSV-Datei").
   - **Spalten**:
     - Pflichtfelder: `common_name`, `country`, `state`, `locality`, `organization`, `organizational_unit`, `email_address`.
     - Optional: `subject_alt_names` (kommagetrennte Liste, z. B. `"DNS:www.example.com,IP:10.0.0.10"`), `private_key_size` (z. B. `2048`), `private_key_type` (`RSA` oder `EC`), `private_key_passphrase`.
   - Speichere unter `data/hostnames.csv`.

2. **Variablen-Datei konfigurieren (`vars/csrs.yml`)**:
   ```yaml
   ---
   base_output_directory: "/pfad/zum/zertifikat"
   default_private_key_size: 2048
   default_private_key_type: RSA
   ```
   - Optional: Verschlüssele mit Ansible Vault, wenn Passphrases enthalten sind:
     ```bash
     ansible-vault encrypt vars/csrs.yml
     ```

3. **Inventar erstellen (`inventory.yml`)**:
   - Definiere ca. 1000 Hosts, gruppiert nach Plattform:
     ```yaml
     all:
       children:
         linux_hosts:
           hosts:
             webserver1.example.com:
             database.internal.com:
             # ... weitere Linux-Hosts
         windows_hosts:
           hosts:
             winserver1.example.com:
             winapp1.internal.net:
             # ... weitere Windows-Hosts
     ```
   - Stelle sicher, dass `common_name` in `hostnames.csv` mit `inventory_hostname` übereinstimmt.

4. **Zertifikatsordner vorbereiten**:
   - Erstelle Verzeichnisse:
     ```bash
     mkdir -p /pfad/zum/zertifikat /pfad/zum/erledigt_ordner
     chmod 755 /pfad/zum/zertifikat /pfad/zum/erledigt_ordner
     ```

## Schritte zur Ausführung

1. **Vorbereitung**:
   - Installiere Collections:
     ```bash
     ansible-galaxy collection install community.crypto community.general
     ```
   - Prüfe Verbindungen:
     - Linux: SSH-Zugriff (`ssh user@hostname`).
     - Windows: WinRM (`Test-WSMan -ComputerName hostname`) oder OpenSSH (`ssh user@hostname`).
   - Erstelle `data/hostnames.csv` basierend auf `example.csv`.

2. **CSRs generieren**:
   - Führe das Playbook aus:
     ```bash
     ansible-playbook generate_csrs.yml
     ```
   - Falls `vars/csrs.yml` oder `hostnames.csv` verschlüsselt sind:
     ```bash
     ansible-playbook generate_csrs.yml --vault-password-file vault_pass.txt
     ```
   - **Ausgabe**: Für jeden Host ein Ordner unter `/pfad/zum/zertifikat/<common_name>/` mit `<common_name>.csr` und `<common_name>.key`.

3. **CSRs signieren**:
   - Sende die `.csr`-Dateien (z. B. `/pfad/zum/zertifikat/webserver1.example.com/webserver1.example.com.csr`) an deine Zertifizierungsstelle (CA).
   - Speichere die signierten Zertifikate im Format `/pfad/zum/zertifikat/zertifikat_<common_name>.crt` (z. B. `zertifikat_webserver1.example.com.crt`).

4. **Zertifikate austauschen**:
   - Führe das Playbook aus:
     ```bash
     ansible-playbook ssl_certificate_exchange.yml -i inventory.yml
     ```
   - **Ausgabe**: Zertifikate und Schlüssel werden auf die Zielsysteme kopiert (Linux: `/etc/apache2/ssl/` oder `/etc/nginx/ssl/`, Windows: IIS-Zertifikatsspeicher), Dienste neu gestartet, und Dateien nach `/pfad/zum/erledigt_ordner` verschoben.

## Erweiterung der CSV-Datei

Für 1000 Hosts erweitere `data/hostnames.csv`:
- **Manuelle Bearbeitung**:
  - Öffne `example.csv` in einer Tabellenkalkulation (z. B. Excel) und füge weitere Einträge hinzu.
- **Skript-basierte Generierung**:
  - Beispiel in Python:
    ```python
    import csv

    base_hosts = [
        {"common_name": f"server{i}.example.com", "country": "DE", "state": "Hessen", "locality": "Alheim",
         "organization": "Meine Firma GmbH", "organizational_unit": "IT", "email_address": f"admin{i}@example.com",
         "subject_alt_names": f"DNS:www.server{i}.example.com", "private_key_size": "2048", "private_key_type": "RSA",
         "private_key_passphrase": ""}
        for i in range(1, 1001)
    ]

    with open("data/hostnames.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_hosts[0].keys())
        writer.writeheader()
        writer.writerows(base_hosts)
    ```
- **Inventar-basiert**:
  - Exportiere Hostnamen aus `inventory.yml`:
    ```bash
    ansible-inventory -i inventory.yml --list | jq '._meta.hostvars | keys[]' | awk '{print $1 ",DE,Hessen,Alheim,Meine Firma GmbH,IT,admin@" $1 ",,2048,RSA,"}' > data/hostnames.csv
    ```

## Sicherheitshinweise

- **Private Schlüssel**:
  - Setze restriktive Berechtigungen:
    ```bash
    chmod 600 /pfad/zum/zertifikat/*/*.key
    ```
- **PFX-Dateien**:
  - Verwende sichere Passphrases (z. B. `temporary_passphrase` in `ssl_certificate_exchange.yml`).
  - Lösche PFX-Dateien nach dem Import automatisch.
- **CSV-Datei**:
  - Verschlüssele bei sensiblen Daten (z. B. Passphrases):
    ```bash
    ansible-vault encrypt data/hostnames.csv
    ```
- **Backup**:
  - Sichere CSRs, Schlüssel und Zertifikate:
    ```bash
    tar -czf certs_backup.tar.gz /pfad/zum/zertifikat data/hostnames.csv
    ```

## Performance-Optimierungen

- **Parallele Verarbeitung**:
  - Erhöhe `ansible_forks` in `ansible.cfg`:
    ```ini
    [defaults]
    forks = 50
    ```
- **Testlauf**:
  - Teste mit einer kleinen CSV-Datei (z. B. 10 Einträge) vor der Verarbeitung von 1000 Hosts.
- **Speicherplatz**:
  - Stelle sicher, dass `/pfad/zum/zertifikat` ca. 3 MB Platz hat.

## Fehlerbehebung

- **CSV-Fehler**:
  - Prüfe `data/hostnames.csv` auf fehlende Pflichtfelder oder ungültige Formate (z. B. `country` muss 2 Buchstaben haben).
  - Beispiel-Fehler: `common_name` fehlt → Playbook schlägt fehl mit Assertion.
- **Verbindungsfehler (Windows)**:
  - **WinRM**: Prüfe Konfiguration (`winrm get winrm/config`) und Firewall (Port 5985).
  - **OpenSSH**: Stelle sicher, dass SSH-Server läuft (`Get-Service sshd`) und Port 22 offen ist.
- **Zertifikat nicht gefunden**:
  - Überprüfe `/pfad/zum/zertifikat/zertifikat_<hostname>.crt`.
  - Stelle sicher, dass der Dateiname mit `inventory_hostname` übereinstimmt.
- **Privater Schlüssel fehlt**:
  - Prüfe `/pfad/zum/zertifikat/<hostname>/<hostname>.key`.
- **Dienst-Neustart fehlgeschlagen**:
  - Überprüfe Dienst-Logs (z. B. `journalctl -u apache2` oder `Get-EventLog -LogName System`).

## Erweiterte Anpassungen

- **Alternative Datenquellen**:
  - **Ansible-Inventar**:
    - Generiere CSRs direkt aus `groups['all']`:
      ```yaml
      csr_definitions: "{{ groups['all'] | map('extract', hostvars, ['common_name', 'country']) | list }}"
      ```
  - **Datenbank**:
    - Nutze `community.database.mysql_query` für Host-Daten.
- **EC-Schlüssel**:
  - Setze `private_key_type: EC` und `private_key_curve: secp256r1` in `hostnames.csv`.
- **Zusätzliche Attribute**:
  - Erweitere `hostnames.csv` um `key_usage` oder `extended_key_usage` und passe `generate_csrs.yml` an:
    ```yaml
    key_usage: "{{ current_csr_details.key_usage | default(['digitalSignature', 'keyEncipherment']) }}"
    ```

## Ressourcen

- Ansible `community.crypto`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html)
- Ansible `community.general`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/general/index.html)
- WinRM-Konfiguration: [Ansible Windows](https://docs.ansible.com/ansible/latest/user_guide/windows_setup.html)
- OpenSSL: [Dokumentation](https://www.openssl.org/docs/manmaster/man1/req.html)
- Subject Alternative Names: [RFC 5280](https://tools.ietf.org/html/rfc5280#section-4.2.1.6)