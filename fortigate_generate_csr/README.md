# HowTo: Generierung mehrerer OpenSSL CSRs und privater Schlüssel mit Ansible

Dieses Ansible-Playbook automatisiert die Erstellung von Certificate Signing Requests (CSRs) und zugehörigen privaten Schlüsseln für mehrere Hosts oder Dienste mithilfe des `community.crypto`-Moduls. Es erstellt für jeden CSR einen eigenen Ordner mit dem privaten Schlüssel und der CSR-Datei, basierend auf den im Playbook definierten Konfigurationen.

## Voraussetzungen

- **Ansible**: Version 2.9 oder neuer
- **`community.crypto`-Collection**: Installiere die Collection mit:
  ```bash
  ansible-galaxy collection install community.crypto
  ```
- **OpenSSL**: Muss auf dem Ansible Control Host installiert sein (üblicherweise standardmäßig auf Linux-Systemen vorhanden).
- **Schreibrechte**: Der Benutzer, der das Playbook ausführt, muss Schreibrechte im angegebenen Ausgabeverzeichnis haben.
- **Python-Module**: Stelle sicher, dass `pyOpenSSL` oder `cryptography` auf dem Control Host installiert ist:
  ```bash
  pip install pyOpenSSL cryptography
  ```

## Playbook-Übersicht

Das Playbook läuft lokal auf dem Ansible Control Host (`localhost`) und generiert:
- Private Schlüssel (RSA oder EC, standardmäßig 2048 Bit).
- CSRs mit konfigurierbaren Attributen wie Common Name (CN), Subject Alternative Names (SANs), Land, Organisation usw.
- Ausgabedateien werden in host-spezifischen Unterordnern im Basisverzeichnis gespeichert.

## Verzeichnisstruktur der Ausgabe

Die generierten Dateien werden wie folgt organisiert:
```plaintext
/base_output_directory/
  ├── webserver1.example.com/
  │   ├── webserver1.example.com.key  # Privater Schlüssel
  │   └── webserver1.example.com.csr  # CSR
  ├── database.internal.com/
  │   ├── database.internal.com.key
  │   └── database.internal.com.csr
  └── mailserver.mycompany.local/
      ├── mailserver.mycompany.local.key
      └── mailserver.mycompany.local.csr
```

## Konfiguration des Playbooks

1. **Öffne das Playbook** (`generate_csrs.yml`) und bearbeite die `vars`-Sektion:
   ```yaml
   vars:
     base_output_directory: "/tmp/csrs_and_keys"  # Zielordner für die Ausgabe
     default_private_key_size: 2048  # Schlüsselgröße (z. B. 2048 oder 4096)
     default_private_key_type: RSA   # Schlüsseltyp (RSA oder EC)
     csr_definitions:               # Liste der CSRs
       - common_name: "webserver1.example.com"
         country: "DE"
         state: "Hessen"
         locality: "Alheim"
         organization: "Meine Web-Firma GmbH"
         organizational_unit: "Webteam"
         email_address: "webmaster@example.com"
         subject_alt_names:
           - "DNS:www.webserver1.example.com"
           - "DNS:app.webserver1.example.com"
       # Weitere CSR-Definitionen hier hinzufügen
   ```
   - **Anpassungen**:
     - Ändere `base_output_directory` zu einem gewünschten Pfad (z. B. `/home/user/csrs`).
     - Passe `default_private_key_size` und `default_private_key_type` an, falls andere Standardwerte benötigt werden.
     - Füge für jeden CSR einen Eintrag in `csr_definitions` hinzu mit den gewünschten Attributen.
     - Optional: Überschreibe `private_key_size`, `private_key_type` oder füge `private_key_passphrase` für einzelne CSRs hinzu.

2. **Optionale Passphrase**:
   - Wenn ein privater Schlüssel mit einer Passphrase geschützt werden soll, füge sie hinzu, z. B.:
     ```yaml
     private_key_passphrase: "secret_passphrase"
     ```
   - Beachte: Passphrases müssen bei der Verwendung des Schlüssels (z. B. in Webservern) berücksichtigt werden.

3. **Subject Alternative Names (SANs)**:
   - Füge SANs hinzu, um zusätzliche DNS-Namen oder IP-Adressen abzudecken, z. B.:
     ```yaml
     subject_alt_names:
       - "DNS:www.example.com"
       - "IP:10.0.0.10"
     ```

## Schritte zur Ausführung

1. **Vorbereitung**:
   - Stelle sicher, dass die `community.crypto`-Collection installiert ist (siehe Voraussetzungen).
   - Prüfe, ob das Zielverzeichnis (`base_output_directory`) existiert und schreibbar ist:
     ```bash
     mkdir -p /tmp/csrs_and_keys
     chmod 755 /tmp/csrs_and_keys
     ```

2. **Playbook ausführen**:
   - Führe das Playbook mit dem folgenden Befehl aus:
     ```bash
     ansible-playbook generate_csrs.yml
     ```
   - Das Playbook erstellt für jeden definierten CSR einen Ordner mit den Dateien `<common_name>.key` und `<common_name>.csr`.

3. **Ausgabe überprüfen**:
   - Nach der Ausführung zeigt das Playbook die Pfade der generierten Dateien an, z. B.:
     ```
     Privater Schlüssel gespeichert unter: /tmp/csrs_and_keys/webserver1.example.com/webserver1.example.com.key
     CSR gespeichert unter: /tmp/csrs_and_keys/webserver1.example.com/webserver1.example.com.csr
     ```
   - Wenn Dateien bereits existieren, wird ein Hinweis angezeigt, dass sie nicht neu generiert wurden.

4. **CSRs verwenden**:
   - Sende die generierten `.csr`-Dateien an deine Zertifizierungsstelle (CA), um signierte Zertifikate zu erhalten.
   - Speichere die privaten `.key`-Dateien sicher, da sie für die Installation der signierten Zertifikate benötigt werden.

## Sicherheitshinweise

- **Private Schlüssel schützen**:
  - Die generierten `.key`-Dateien enthalten sensible Daten. Stelle sicher, dass sie nur für autorisierte Benutzer zugänglich sind:
    ```bash
    chmod 600 /tmp/csrs_and_keys/*/*.key
    ```
  - Verwende Passphrases für zusätzliche Sicherheit, wenn dies mit deiner Infrastruktur kompatibel ist.

- **Ausgabeverzeichnis sichern**:
  - Wähle ein sicheres Verzeichnis für `base_output_directory`, das nicht öffentlich zugänglich ist.
  - Verschiebe die Dateien nach der Generierung in ein sicheres Backup oder ein Vault-System.

- **Passphrases verwalten**:
  - Wenn du `private_key_passphrase` verwendest, speichere sie sicher (z. B. in Ansible Vault):
    ```bash
    ansible-vault encrypt_string 'dein_passwort' --name 'vault_passphrase'
    ```

## Fehlerbehebung

- **Fehler: „community.crypto nicht gefunden“**:
  - Stelle sicher, dass die Collection installiert ist:
    ```bash
    ansible-galaxy collection install community.crypto
    ```
- **Fehler: „Permission denied“**:
  - Prüfe die Berechtigungen des `base_output_directory`:
    ```bash
    ls -ld /tmp/csrs_and_keys
    ```
  - Passe die Berechtigungen an:
    ```bash
    chown $(whoami) /tmp/csrs_and_keys
    chmod 755 /tmp/csrs_and_keys
    ```
- **Fehler: „Ungültige CSR-Parameter“**:
  - Überprüfe die `csr_definitions` auf fehlende oder ungültige Werte (z. B. `common_name`, `country`).
  - Stelle sicher, dass `subject_alt_names` korrekt formatiert sind (z. B. `DNS:name` oder `IP:address`).
- **Keine neuen Dateien generiert**:
  - Wenn Dateien bereits existieren, werden sie nicht überschrieben (`force: no`). Lösche die bestehenden Dateien oder setze `force: yes` in den Tasks `openssl_privatekey` und `openssl_csr`.

## Erweiterte Anpassungen

- **EC-Schlüssel verwenden**:
  - Ändere `default_private_key_type` zu `EC` oder setze `private_key_type: EC` für einzelne CSRs. Beachte, dass du eine Kurve angeben musst, z. B.:
    ```yaml
    private_key_curve: secp256r1
    ```
- **Zusätzliche CSR-Attribute**:
  - Füge weitere Attribute hinzu, wie z. B. `key_usage` oder `extended_key_usage`, im `openssl_csr`-Task:
    ```yaml
    key_usage: ["digitalSignature", "keyEncipherment"]
    extended_key_usage: ["serverAuth"]
    ```
- **Automatisierung mit Inventar**:
  - Passe das Playbook an, um Hostnamen aus einem Ansible-Inventar zu verwenden, indem du `hosts: all` setzt und `inventory_hostname` in `csr_definitions` verwendest.

## Ressourcen

- Ansible `community.crypto` Dokumentation: [community.crypto](https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html)
- OpenSSL CSR-Anforderungen: [OpenSSL Dokumentation](https://www.openssl.org/docs/manmaster/man1/req.html)
- Subject Alternative Names: [RFC 5280](https://tools.ietf.org/html/rfc5280#section-4.2.1.6)