# SSL-Zertifikat Austausch Playbook für FortiGate Firewalls

Dieses Ansible-Playbook automatisiert den Austausch von SSL-Zertifikaten auf FortiGate Firewalls für Anwendungen wie SSL-VPN, HTTPS-GUI oder SSL-Inspection.

## Voraussetzungen

- Ansible 2.9 oder neuer
- `fortinet.fortios`-Collection (`ansible-galaxy collection install fortinet.fortios`)
- HTTPS-Zugriff auf die FortiGate REST-API (Port 443)
- API-Token oder Benutzername/Passwort für die Authentifizierung
- Zertifikatsdateien (*.crt), private Schlüssel (*.key) und optional Zertifikatsketten (*.chain) im Eingangsordner auf dem Ansible Control Host
- FortiGate mit FortiOS 6.0 oder neuer (getestet mit FortiOS 7.0+)
- VDOM-Konfiguration (Standard: `root`)

## Verzeichnisstruktur

```plaintext
/pfad/zum/zertifikat_ordner/    # Eingangsordner für Zertifikate (*.crt), Schlüssel (*.key) und Ketten (*.chain)
/pfad/zum/erledigt_ordner/      # Zielordner für verarbeitete Dateien
```

## Dateinamenkonvention

Dateien müssen den Hostnamen enthalten, z. B.:
- `hostname.crt` (Zertifikat im PEM-Format)
- `hostname.key` (Privater Schlüssel im PEM-Format)
- Optional: `hostname.chain` (Zertifikatskette im PEM-Format)
- Der Hostname wird mit `inventory_hostname` abgeglichen.

## Playbook-Beschreibung

1. **Zertifikate finden**: Sucht nach `*.crt`, `*.key` und `*.chain` Dateien im Eingangsordner auf dem Control Host.
2. **Validierung**: Prüft, ob Zertifikat und Schlüssel vorhanden sind und im gültigen PEM-Format.
3. **Zertifikat importieren**:
   - Löscht ein bestehendes Zertifikat mit demselben Namen (falls vorhanden).
   - Lädt Zertifikat, Schlüssel und optional die Kette auf die FortiGate (via `fortios_certificate_local`).
   - Weist das Zertifikat z. B. dem SSL-VPN-Portal zu (via `fortios_vpn_ssl_settings`).
4. **Dateien verschieben**: Verschiebt verarbeitete Dateien in den Erledigt-Ordner.
5. **Original löschen**: Entfernt die Originaldateien aus dem Eingangsordner.

## Verwendung

1. Installiere die `fortinet.fortios`-Collection:
   ```bash
   ansible-galaxy collection install fortinet.fortios
   ```
2. Passe die Variablen in `vars` an:
   - `certificate_source_path` und `certificate_done_path`
   - `fortios_access_token` oder `fortios_username`/`fortios_password` (in Ansible Vault speichern)
   - `fortios_vdom` (falls nicht `root`)
3. Verschlüssele sensible Daten mit Ansible Vault:
   ```bash
   ansible-vault encrypt_string 'dein_api_token' --name 'vault_fortios_access_token'
   ansible-vault encrypt_string 'dein_passwort' --name 'vault_fortios_password'
   ```
4. Stelle sicher, dass die Zertifikate im Eingangsordner liegen und die Dateinamen den Hostnamen enthalten.
5. Konfiguriere die Inventargruppe `fortigates` mit den Hostnamen/IP-Adressen der FortiGate-Geräte.
6. Führe das Playbook aus:
   ```bash
   ansible-playbook fortigate_certificate_exchange.yml -i inventory.yml
   ```

## Wichtige Hinweise

- Das Playbook prüft, ob der Hostname im Dateinamen mit `inventory_hostname` übereinstimmt.
- Verwende Ansible Vault für `fortios_access_token`, `fortios_username` und `fortios_password`.
- Stelle sicher, dass die FortiGate REST-API aktiviert ist (System > Netzwerkeinstellungen).
- Passe den Task „Zertifikat für SSL-VPN Portal konfigurieren“ an den Namen deines Portals an.
- Teste das Playbook in einer Laborumgebung, da ein fehlerhaftes Zertifikat den Zugriff (z. B. SSL-VPN) unterbrechen kann.
- Bei mehreren VDOMs passe `fortios_vdom` an.

## Einschränkungen

- Unterstützt nur FortiGate-Geräte mit FortiOS 6.0+.
- Zertifikate und Schlüssel müssen im PEM-Format vorliegen.
- Keine Unterstützung für PKCS12-Dateien.
- Der Zertifikats-Upload wird pro VDOM durchgeführt; Multi-VDOM-Konfigurationen erfordern Anpassungen.

## Fehlerbehandlung

- Wenn kein Zertifikat oder Schlüssel gefunden wird, schlägt das Playbook fehl.
- Ungültige Zertifikate oder Schlüssel führen zu einer klaren Fehlermeldung.
- API-Fehler (z. B. ungültiger Token) werden protokolliert.
- Bestehende Zertifikate werden vor dem Import entfernt, um Konflikte zu vermeiden.

## Quellen

- Fortinet FortiOS Ansible-Dokumentation: [fortinet.fortios](https://docs.ansible.com/ansible/latest/collections/fortinet/fortios/index.html)
- FortiGate REST-API: [Fortinet Developer Network](https://fndn.fortinet.net/)