# HowTo: Generierung und Austausch von SSL-Zertifikaten für ca. 1000 Hosts mit Ansible

Dieses HowTo beschreibt, wie du mit zwei Ansible-Playbooks Certificate Signing Requests (CSRs) für ca. 1000 Hosts generierst und signierte SSL-Zertifikate auf Linux (Apache/Nginx) und Windows (IIS) austauschst. Die CSRs werden dynamisch aus einer CSV- oder JSON-Datei erstellt, und das Austausch-Playbook unterstützt sowohl WinRM als auch OpenSSH für Windows-Hosts. Beispiel-Dateien (`example.csv` und `example.json`) dienen als Vorlagen für die Konfiguration.

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
- **Datenquelle**: Entweder `data/hostnames.csv` (basierend auf `example.csv`) oder `data/hostnames.json` (basierend auf `example.json`) mit Hostnamen und CSR-Attributen.
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
  │   ├── hostnames.csv  # Basierend auf example.csv (optional)
  │   └── hostnames.json # Basierend auf example.json (optional)
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

1. **Datenquelle erstellen**:
   - Wähle entweder eine CSV- oder JSON-Datei als Datenquelle für die CSR-Generierung.

   **Option A: CSV-Datei (`data/hostnames.csv`)**:
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
     winapp1.internal.net,US,California,San Francisco,Enterprise Inc.,Applications,apps@web.net,"DNS:app1.web.com",2048,RSA,winapp_secure
     gateway.web.com,DE,Nordrhein-Westfalen,Duesseldorf,Security GmbH,123@web.com,"DNS:gw1.example.org,DNS:example.org",2048,RSA,
     monitor.systems.local,CH,Zurich,Zurich,Systems AG,Monitoring,monitor@systems.local,IP:172.16.0.5,2048,EC,
     ```
   - **Spalten**:
     - Pflichtfelder: `common_name`, `country`, `state`, `locality`, `organization`, `organizational_unit`, `email_address`.
     - Optional: `subject_alt_names` (kommagetrennte Liste, z. B. `"DNS:www.example.com,IP:10.0.com"`), `private_key_size` (z. B. `2048`), `private_key_type` (`RSA` oder `EC`), `private_key_passphrase`.
   - Speichere unter `data/hostnames.csv`.

   **Option B: JSON-Datei (`data/hostnames.json`)**:
   - Verwende die Beispiel-JSON-Datei als Vorlage:
     ```json
     [
       {
         "common_name": "webserver1.example.com",
         "country": "DE",
         "state": "Hessen",
         "locality": "Alheim",
         "organization": "Meine Web-Firma GmbH",
         "organizational_unit": "Webteam",
         "email_address": "webmaster@example.com",
         "subject_alt_names": ["DNS:www.webserver1.example.com", "DNS:app.webserver1.example.com"],
         "private_key_size": 2048,
         "private_key_type": "RSA"
       },
       {
         "common_name": "database.internal.com",
         "country": "DE",
         "state": "Hessen",
         "locality": "Alheim",
         "organization": "Meine DB-Firma AG",
         "organizational_unit": "Datenbanken",
         "email_address": "dbadmin@internal.com",
         "subject_alt_names": ["IP:10.0.0.10"],
         "private_key_size": 2048,
         "private_key_type": "RSA"
       },
       {
         "common_name": "mailserver.mycompany.local",
         "country": "US",
         "state": "New York",
         "locality": "New York City",
         "organization": "My Corp Inc.",
         "organizational_unit": "Email Services",
         "email_address": "postmaster@mycompany.local",
         "subject_alt_names": ["DNS:autodiscover.mycompany.local", "DNS:mail.mycompany.local"],
         "private_key_size": 4096,
         "private_key_type": "RSA",
         "private_key_passphrase": "secret_passphrase"
       },
       {
         "common_name": "winserver1.example.com",
         "country": "DE",
         "state": "Bayern",
         "locality": "Muenchen",
         "organization": "Meine Firma GmbH",
         "organizational_unit": "IT",
         "email_address": "admin@example.com",
         "subject_alt_names": ["DNS:www.winserver1.example.com"],
         "private_key_size": 2048,
         "private_key_type": "RSA"
       },
       {
         "common_name": "api.server.company.net",
         "country": "FR",
         "state": "Ile-de-France",
         "locality": "Paris",
         "organization": "Tech Corp SAS",
         "organizational_unit": "API Team",
         "email_address": "api@company.net",
         "subject_alt_names": ["DNS:api2.server.company.net", "IP:192.168.1.100"],
         "private_key_size": 2048,
         "private_key_type": "EC",
         "private_key_passphrase": "api_secure123"
       },
       {
         "common_name": "frontend.app.local",
         "country": "UK",
         "state": "London",
         "locality": "London",
         "organization": "App Ltd",
         "organizational_unit": "Frontend",
         "email_address": "frontend@app.local",
         "subject_alt_names": ["DNS:www.app.local"],
         "private_key_size": 2048,
         "private_key_type": "RSA"
       },
       {
         "common_name": "backend.app.local",
         "country": "UK",
         "state": "London",
         "locality": "London",
         "organization": "App Ltd",
         "organizational_unit": "Backend",
         "email_address": "backend@app.local",
         "subject_alt_names": ["IP:10.0.0.20"],
         "private_key_size": 4096,
         "private_key_type": "RSA"
       },
       {
         "common_name": "winapp1.example.com",
         "country": "US",
         "state": "California",
         "locality": "San Francisco",
         "organization": "Enterprise Inc.",
         "organizational_unit": "Applications",
         "email_address": "apps@enterprise.com",
         "subject_alt_names": ["DNS:app1.example.com"],
         "private_key_size": 2048,
         "private_key_type": "RSA",
         "private_key_passphrase": "winapp_secure"
       },
       {
         "common_name": "gateway.example.org",
         "country": "DE",
         "state": "Nordrhein-Westfalen",
         "locality": "Duesseldorf",
         "organization": "Security GmbH",
         "organizational_unit": "Network",
         "email_address": "gwadmin@example.org",
         "subject_alt_names": ["DNS:gw1.example.org", "DNS:gw2.example.org"],
         "private_key_size": 2048,
         "private_key_type": "RSA"
       },
       {
         "common_name": "monitor.systems.local",
         "country": "CH",
         "state": "Zurich",
         "locality": "Zurich",
         "organization": "Systems AG",
         "organizational_unit": "Monitoring",
         "email_address": "monitor@systems.local",
         "subject_alt_names": ["IP:172.16.0.5"],
         "private_key_size": 2048,
         "private_key_type": "EC"
       }
     ]
     ```
   - **Felder**:
     - Pflichtfelder: `common_name`, `country`, `state`, `locality`, `organization`, `organizational_unit`, `email_address`.
     - Optional: `subject_alt_names` (Array von Strings, z. B. `["DNS:www.example.com", "IP:10.0.0.10"]`), `private_key_size`, `private_key_type`, `private_key_passphrase`.
   - Speichere unter `data/hostnames.json`.

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
             winapp1.example.com:
             # ... weitere Windows-Hosts
     ```
   - Stelle sicher, dass `common_name` in `hostnames.csv` oder `hostnames.json` mit `inventory_hostname` übereinstimmt.

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
   - Erstelle entweder `data/hostnames.csv` (basierend auf `example.csv`) oder `data/hostnames.json` (basierend auf `example.json`).

2. **Playbook für JSON anpassen (falls verwendet)**:
   - Wenn du `hostnames.json` nutzt, passe `generate_csrs.yml` an, um JSON zu lesen:
     ```yaml
     - name: Lade Hostnamen aus JSON-Datei
       ansible.builtin.slurp:
         src: data/hostnames.json
       register: json_data

     - name: Validiere JSON-Daten
       ansible.builtin.assert:
         that:
           - item.common_name is defined and item.common_name | length > 0
           - item.country is defined and item.country | length == 2
         fail_msg: "Ungültiger Eintrag in JSON: {{ item }}"
       loop: "{{ json_data.content | b64decode | from_json }}"
       when: json_data.content | b64decode | from_json | length > 0

     - name: Erstelle dynamische CSR-Definitionen
       set_fact:
         csr_definitions: "{{ json_data.content | b64decode | from_json }}"
       when: json_data.content | b64decode | from_json | length > 0
     ```
   - Ersetze damit die `community.general.read_csv`-Tasks in `generate_csrs.yml`.

3. **CSRs generieren**:
   - Führe das Playbook aus:
     ```bash
     ansible-playbook generate_csrs.yml
     ```
   - Falls `vars/csrs.yml`, `hostnames.csv` oder `hostnames.json` verschlüsselt sind:
     ```bash
     ansible-playbook generate_csrs.yml --vault-password-file vault_pass.txt
     ```
   - **Ausgabe**: Für jeden Host ein Ordner unter `/pfad/zum/zertifikat/<common_name>/` mit `<common_name>.csr`, `<common_name>.key` und (für Windows) `<common_name>.pfx`.

4. **CSRs signieren**:
   - Sende die `.csr`-Dateien (z. B. `/pfad/zum/zertifikat/webserver1.example.com/webserver1.example.com.csr`) an deine Zertifizierungsstelle (CA).
   - Speichere die signierten Zertifikate im Format `/pfad/zum/zertifikat/zertifikat_<common_name>.crt` (z. B. `zertifikat_webserver1.example.com.crt`).

5. **Zertifikate austauschen**:
   - Führe das Playbook aus:
     ```bash
     ansible-playbook ssl_certificate_exchange.yml -i inventory.yml
     ```
   - **Ausgabe**: Zertifikate und Schlüssel werden auf die Zielsysteme kopiert (Linux: `/etc/apache2/ssl/` oder `/etc/nginx/ssl/`, Windows: IIS-Zertifikatsspeicher), Dienste neu gestartet, und Dateien nach `/pfad/zum/erledigt_ordner` verschoben.

## Erweiterung der Datenquelle

Für 1000 Hosts erweitere entweder `data/hostnames.csv` oder `data/hostnames.json`:

- **CSV (`hostnames.csv`)**:
  - **Manuelle Bearbeitung**: Öffne `example.csv` in einer Tabellenkalkulation (z. B. Excel) und füge weitere Einträge hinzu.
  - **Skript-basierte Generierung**:
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
    ```bash
    ansible-inventory -i inventory.yml --list | jq '._meta.hostvars | keys[]' | awk '{print $1 ",DE,Hessen,Alheim,Meine Firma GmbH,IT,admin@" $1 ",,2048,RSA,"}' > data/hostnames.csv
    ```

- **JSON (`hostnames.json`)**:
  - **Manuelle Bearbeitung**: Bearbeite `example.json` in einem Text- oder JSON-Editor.
  - **Skript-basierte Generierung**:
    ```python
    import json

    base_hosts = [
        {
            "common_name": f"server{i}.example.com",
            "country": "DE",
            "state": "Hessen",
            "locality": "Alheim",
            "organization": "Meine Firma GmbH",
            "organizational_unit": "IT",
            "email_address": f"admin{i}@example.com",
            "subject_alt_names": [f"DNS:www.server{i}.example.com"],
            "private_key_size": 2048,
            "private_key_type": "RSA",
            "private_key_passphrase": ""
        }
        for i in range(1, 1001)
    ]

    with open("data/hostnames.json", "w") as f:
        json.dump(base_hosts, f, indent=2)
    ```
  - **Inventar-basiert**:
    ```bash
    ansible-inventory -i inventory.yml --list | jq '._meta.hostvars | keys[] | {common_name: ., country: "DE", state: "Hessen", locality: "Alheim", organization: "Meine Firma GmbH", organizational_unit: "IT", email_address: ("admin@" + .), subject_alt_names: ["DNS:www." + .], private_key_size: 2048, private_key_type: "RSA", private_key_passphrase: ""}' > data/hostnames.json
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
- **Datenquellen**:
  - Verschlüssele `hostnames.csv` oder `hostnames.json` bei sensiblen Daten (z. B. Passphrases):
    ```bash
    ansible-vault encrypt data/hostnames.csv
    ansible-vault encrypt data/hostnames.json
    ```
- **Backup**:
  - Sichere CSRs, Schlüssel, Zertifikate und Datenquellen:
    ```bash
    tar -czf certs_backup.tar.gz /pfad/zum/zertifikat data/hostnames.csv data/hostnames.json
    ```

## Performance-Optimierungen

- **Parallele Verarbeitung**:
  - Erhöhe `ansible_forks` in `ansible.cfg`:
    ```ini
    [defaults]
    forks = 50
    ```
- **Testlauf**:
  - Teste mit einer kleinen Datenquelle (z. B. 10 Einträge) vor der Verarbeitung von 1000 Hosts.
- **Speicherplatz**:
  - Stelle sicher, dass `/pfad/zum/zertifikat` ca. 3 MB Platz hat.

## Fehlerbehebung

- **Datenquellen-Fehler**:
  - **CSV**: Prüfe `data/hostnames.csv` auf fehlende Pflichtfelder oder ungültige Formate (z. B. `country` muss 2 Buchstaben haben).
  - **JSON**: Prüfe `data/hostnames.json` auf Syntaxfehler (z. B. mit `jq . data/hostnames.json`) oder fehlende Felder.
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
  - Setze `private_key_type: EC` und `private_key_curve: secp256r1` in `hostnames.csv` oder `hostnames.json`.
- **Zusätzliche Attribute**:
  - Erweitere die Datenquelle um `key_usage` oder `extended_key_usage` und passe `generate_csrs.yml` an:
    ```yaml
    key_usage: "{{ current_csr_details.key_usage | default(['digitalSignature', 'keyEncipherment']) }}"
    ```

## Ressourcen

- Ansible `community.crypto`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html)
- Ansible `community.general`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/general/index.html)
- WinRM-Konfiguration: [Ansible Windows](https://docs.ansible.com/ansible/latest/user_guide/windows_setup.html)
- OpenSSL: [Dokumentation](https://www.openssl.org/docs/manmaster/man1/req.html)
- Subject Alternative Names: [RFC 5280](https://tools.ietf.org/html/rfc5280#section-4.2.1.6)