# HowTo: Generierung mehrerer OpenSSL CSRs und privater Schlüssel mit Ansible

Dieses Ansible-Playbook automatisiert die Erstellung von Certificate Signing Requests (CSRs) und zugehörigen privaten Schlüsseln für eine große Anzahl von Hosts oder Diensten (z. B. 1500 Hostnamen) mithilfe des `community.crypto`-Moduls. Es unterstützt dynamische CSR-Definitionen, die aus einer externen Datenquelle (z. B. CSV-Datei) geladen werden, und erstellt für jeden CSR einen eigenen Ordner mit dem privaten Schlüssel und der CSR-Datei.

## Voraussetzungen

- **Ansible**: Version 2.9 oder neuer
- **Collections**:
  - `community.crypto`: Für OpenSSL-Operationen.
  - `community.general`: Für das Laden von CSV-Dateien.
  - Installiere beide mit:
    ```bash
    ansible-galaxy collection install community.crypto community.general
    ```
- **OpenSSL**: Muss auf dem Ansible Control Host installiert sein.
- **Python-Module**: Stelle sicher, dass `pyOpenSSL` oder `cryptography` installiert ist:
  ```bash
  pip install pyOpenSSL cryptography
  ```
- **Schreibrechte**: Der Benutzer muss Schreibrechte im Ausgabeverzeichnis haben.
- **CSV-Datei**: Eine Datenquelle (z. B. `data/hostnames.csv`) mit Hostnamen und CSR-Attributen.

## Playbook-Übersicht

Das Playbook läuft lokal auf dem Ansible Control Host (`localhost`) und generiert:
- Private Schlüssel (RSA oder EC, standardmäßig 2048 Bit).
- CSRs mit konfigurierbaren Attributen wie Common Name (CN), Subject Alternative Names (SANs), Land, Organisation usw.
- Ausgabedateien in host-spezifischen Unterordnern im Basisverzeichnis.

## Verzeichnisstruktur

### Eingabedateien
```plaintext
project_directory/
  ├── data/
  │   └── hostnames.csv  # CSV-Datei mit Hostnamen und CSR-Attributen
  ├── vars/
  │   └── csrs.yml       # Standard-Variablen
  └── generate_csrs.yml  # Playbook
```

### Ausgabedateien
```plaintext
/base_output_directory/
  ├── webserver1.example.com/
  │   ├── webserver1.example.com.key
  │   └── webserver1.example.com.csr
  ├── database.internal.com/
  │   ├── database.internal.com.key
  │   └── database.internal.com.csr
  # ... weitere 1498 Ordner
```

## Konfiguration des Playbooks

1. **CSV-Datei erstellen (`data/hostnames.csv`)**:
   - Definiere Hostnamen und CSR-Attribute in einer CSV-Datei:
     ```csv
     common_name,country,state,locality,organization,organizational_unit,email_address,subject_alt_names,private_key_size,private_key_type,private_key_passphrase
     webserver1.example.com,DE,Hessen,Alheim,Meine Web-Firma GmbH,Webteam,webmaster@example.com,"DNS:www.webserver1.example.com,DNS:app.webserver1.example.com",2048,RSA,
     database.internal.com,DE,Hessen,Alheim,Meine DB-Firma AG,Datenbanken,dbadmin@internal.com,IP:10.0.0.10,2048,RSA,
     mailserver.mycompany.local,US,New York,New York City,My Corp Inc.,Email Services,postmaster@mycompany.local,"DNS:autodiscover.mycompany.local,DNS:mail.mycompany.local",4096,RSA,secret_passphrase
     ```
   - **Spalten**:
     - `common_name`: Pflichtfeld, z. B. `webserver1.example.com`.
     - `country`, `state`, `locality`, `organization`, `organizational_unit`, `email_address`: Pflichtfelder für CSR-Attribute.
     - `subject_alt_names`: Optional, kommagetrennte Liste (z. B. `DNS:www.example.com,IP:10.0.0.10`).
     - `private_key_size`, `private_key_type`, `private_key_passphrase`: Optional, mit Standardwerten aus `vars/csrs.yml`.
   - Speichere die Datei unter `data/hostnames.csv`.

2. **Variablen-Datei konfigurieren (`vars/csrs.yml`)**:
   - Definiere Standardwerte:
     ```yaml
     ---
     base_output_directory: "/tmp/csrs_and_keys"
     default_private_key_size: 2048
     default_private_key_type: RSA
     ```
   - Optional: Verschlüssele die Datei mit Ansible Vault, wenn Passphrases enthalten sind:
     ```bash
     ansible-vault encrypt vars/csrs.yml
     ```

3. **Optionale Passphrase**:
   - Wenn private Schlüssel geschützt werden sollen, füge `private_key_passphrase` in der CSV-Datei hinzu.
   - Speichere Passphrases sicher (z. B. in einer separaten Vault-Datei).

4. **Subject Alternative Names (SANs)**:
   - Definiere SANs in der CSV-Spalte `subject_alt_names` als kommagetrennte Liste, z. B.:
     ```csv
     "DNS:www.example.com,DNS:app.example.com"
     ```

## Schritte zur Ausführung

1. **Vorbereitung**:
   - Installiere die erforderlichen Collections:
     ```bash
     ansible-galaxy collection install community.crypto community.general
     ```
   - Erstelle das Ausgabeverzeichnis und prüfe Berechtigungen:
     ```bash
     mkdir -p /tmp/csrs_and_keys
     chmod 755 /tmp/csrs_and_keys
     ```
   - Stelle sicher, dass `data/hostnames.csv` existiert und korrekt formatiert ist.

2. **Playbook ausführen**:
   - Ohne Vault:
     ```bash
     ansible-playbook generate_csrs.yml
     ```
   - Mit Vault:
     ```bash
     ansible-playbook generate_csrs.yml --vault-password-file vault_pass.txt
     ```

3. **Ausgabe überprüfen**:
   - Das Playbook zeigt die Pfade der generierten Dateien an, z. B.:
     ```
     Privater Schlüssel gespeichert unter: /tmp/csrs_and_keys/webserver1.example.com/webserver1.example.com.key
     CSR gespeichert unter: /tmp/csrs_and_keys/webserver1.example.com/webserver1.example.com.csr
     ```
   - Bestehende Dateien werden nicht überschrieben (`force: no`).

4. **CSRs verwenden**:
   - Sende die `.csr`-Dateien an deine Zertifizierungsstelle (CA).
   - Sichere die `.key`-Dateien für die spätere Zertifikatsinstallation.

## Sicherheitshinweise

- **Private Schlüssel schützen**:
  - Setze restriktive Berechtigungen:
    ```bash
    chmod 600 /tmp/csrs_and_keys/*/*.key
    ```
- **Ausgabeverzeichnis sichern**:
  - Wähle ein nicht-öffentliches Verzeichnis für `base_output_directory`.
  - Verschiebe Dateien nach der Generierung in ein sicheres Backup.
- **Passphrases verwalten**:
  - Speichere Passphrases in einer Vault-Datei:
    ```bash
    ansible-vault encrypt_string 'dein_passwort' --name 'vault_passphrase'
    ```
- **CSV-Datei schützen**:
  - Wenn `hostnames.csv` sensible Daten enthält, verschlüssele sie oder speichere sie in einem sicheren Verzeichnis.

## Fehlerbehebung

- **Fehler: „community.crypto/general nicht gefunden“**:
  - Installiere die Collections:
    ```bash
    ansible-galaxy collection install community.crypto community.general
    ```
- **Fehler: „Permission denied“**:
  - Prüfe Berechtigungen:
    ```bash
    chown $(whoami) /tmp/csrs_and_keys
    chmod 755 /tmp/csrs_and_keys
    ```
- **Fehler: „CSV-Datei nicht gefunden“**:
  - Stelle sicher, dass `data/hostnames.csv` existiert und lesbar ist.
- **Fehler: „Ungültige CSR-Parameter“**:
  - Prüfe die CSV-Spalten auf fehlende oder ungültige Werte.
  - Stelle sicher, dass `subject_alt_names` korrekt formatiert sind.
- **Keine neuen Dateien generiert**:
  - Lösche bestehende Dateien oder setze `force: yes` in den `openssl_privatekey`/`openssl_csr`-Tasks.

## Erweiterte Anpassungen

- **Alternative Datenquellen**:
  - **Ansible-Inventar**:
    - Nutze `groups['all']` für Hostnamen:
      ```yaml
      csr_definitions: "{{ groups['all'] | map('extract', hostvars, ['common_name', 'country']) | list }}"
      ```
  - **Datenbank**:
    - Lade Daten mit `community.database.mysql_query`.
  - **JSON-Datei**:
    - Lade mit `ansible.builtin.slurp` und `from_json`.
- **EC-Schlüssel**:
  - Setze `private_key_type: EC` und `private_key_curve: secp256r1` in der CSV-Datei.
- **Zusätzliche Attribute**:
  - Erweitere die CSV-Datei um `key_usage` oder `extended_key_usage` und passe den `openssl_csr`-Task an:
    ```yaml
    key_usage: "{{ current_csr_details.key_usage | default(['digitalSignature', 'keyEncipherment']) }}"
    ```

## Ressourcen

- Ansible `community.crypto`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html)
- Ansible `community.general`: [Dokumentation](https://docs.ansible.com/ansible/latest/collections/community/general/index.html)
- OpenSSL CSR: [OpenSSL Dokumentation](https://www.openssl.org/docs/manmaster/man1/req.html)
- Subject Alternative Names: [RFC 5280](https://tools.ietf.org/html/rfc5280#section-4.2.1.6)