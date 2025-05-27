# Wie man den CMDB-Syncer auf Debian 12 installiert

Dieses HowTo beschreibt, wie man den CMDB-Syncer auf einem Debian 12 System mithilfe des Ansible-Playbooks `install_cmdb_syncer_on_debian_12.yml` aus dem Repository [bh2005/ansible-things](https://github.com/bh2005/ansible-things) installiert. Das Playbook automatisiert die Installation von MongoDB, Python-Abhängigkeiten, Git, und die Einrichtung des CMDB-Syncer-Dienstes. Zusätzlich wird ein spezifischer Hinweis für die Installation auf einem Proxmox-Host mit AVX-Unterstützung bereitgestellt.

## Voraussetzungen
- **Ansible**: Installiert und konfiguriert auf dem Ansible-Controller (Version kompatibel mit dem Playbook).
- **Zielsystem**: Ein Debian 12 System (physisch, virtuell oder als Proxmox-VM).
- **Root-Zugriff**: Root- oder Sudo-Berechtigungen auf dem Zielsystem (das Playbook verwendet `become: true`).
- **Git**: Zugriff auf das Repository [bh2005/ansible-things](https://github.com/bh2005/ansible-things).
- **Internetzugriff**: Für das Herunterladen von Paketen (MongoDB, Python-Pakete, Git).
- **Proxmox (falls zutreffend)**: AVX-Unterstützung auf dem Proxmox-Host für MongoDB (siehe Hinweis unten).
- **Python**: Python 3 auf dem Zielsystem (wird vom Playbook installiert, falls nicht vorhanden).
- **Abhängigkeiten**: Das Playbook installiert alle benötigten Pakete, aber stelle sicher, dass `apt` funktioniert und keine Paketquellen blockiert sind.

## Hinweis: MongoDB auf Proxmox-Host mit AVX-Unterstützung
MongoDB erfordert AVX-Unterstützung auf der CPU. Standard-CPUs in Proxmox-VMs haben diese Funktion oft nicht aktiviert, was zu Fehlern bei der Installation führt.

### Schritt 1: Prüfen, ob AVX auf der Host-CPU verfügbar ist
Führe auf dem Proxmox-Server folgenden Befehl aus, um die verfügbaren CPU-Flags zu überprüfen:
```bash
root@proxmox-server:~# grep -o 'avx[^ ]*' /proc/cpuinfo
```
**Beispielausgabe**:
```plaintext
avx
avx2
avx512f
avx512dq
avx512cd
avx512bw
avx512vl
avx512_vnni
```
Wenn `avx` oder `avx2` nicht angezeigt wird, ist MongoDB nicht lauffähig.

### Lösung: Eigenen CPU-Typ mit AVX definieren
Falls AVX nicht verfügbar ist oder in der VM nicht aktiviert ist, definiere einen benutzerdefinierten CPU-Typ in Proxmox:

1. Erstelle oder bearbeite die Datei `/etc/pve/virtual-guest/cpu-models.conf`:
   ```bash
   root@proxmox-server:~# nano /etc/pve/virtual-guest/cpu-models.conf
   ```

2. Füge folgenden Inhalt hinzu:
   ```plaintext
   cpu-model: x86-64-v2-AES-AVX
       flags +avx;+avx2;+xsave;+aes;+popcnt;+ssse3;+sse4_1;+sse4_2
       phys-bits host
       hidden 0
       hv-vendor-id proxmox
       reported-model kvm64
   ```

3. Weise der VM den neuen CPU-Typ zu:
   - Bearbeite die VM-Konfiguration in Proxmox (z. B. über die Web-Oberfläche oder `/etc/pve/qemu-server/<VMID>.conf`).
   - Setze `cpu: x86-64-v2-AES-AVX` in der VM-Konfiguration.
   - Beispiel für `/etc/pve/qemu-server/<VMID>.conf`:
     ```plaintext
     cpu: x86-64-v2-AES-AVX
     ```

4. Starte die VM neu, um die Änderungen zu übernehmen:
   ```bash
   qm stop <VMID>
   qm start <VMID>
   ```

## Schritte zur Installation des CMDB-Syncer

### 1. Ansible-Playbook herunterladen
Klone das Repository oder kopiere das Playbook `install_cmdb_syncer_on_debian_12.yml` auf deinen Ansible-Controller:

```bash
git clone https://github.com/bh2005/ansible-things.git
cd ansible-things/cmdb-syncer
```

Das Playbook sieht wie folgt aus (Auszug zur Übersicht):
```yaml
---
- name: Install CMDB Syncer on Debian 12 with Apache and uWSGI
  hosts: localhost
  become: true
  vars:
    ansible_python_interpreter: /usr/bin/python3
    cmdbsyncer_install_dir: "/var/www/cmdbsyncer"
    cmdbsyncer_repo_url: "https://github.com/kuhn-ruess/cmdbsyncer.git"
    cmdbsyncer_venv_dir: "{{ cmdbsyncer_install_dir }}/ENV"
    server_ip: "YOUR-IP"
    mongodb_version: "8.0"
    apache_vhost_file: "/etc/apache2/sites-available/cmdbsyncer.conf"
    http_proxy: "YOUR-PROXY:8080"
    https_proxy: "YOUR-PROXY:8080"
    ansible_tmp_dir: "/var/www/cmdbsyncer/.ansible_tmp"
    proxy_cert_dir: "/root"
    no_proxy: "localhost,127.0.0.1"
    uwsgi_socket: "/run/uwsgi/cmdbsyncer.sock"
    ANSIBLE_REMOTE_TMP: "{{ ansible_tmp_dir }}"
  environment:
    http_proxy: "{{ http_proxy | default('') }}"
    https_proxy: "{{ https_proxy | default('') }}"
    no_proxy: "{{ no_proxy }}"
    ANSIBLE_REMOTE_TMP: "{{ ansible_tmp_dir }}"
  pre_tasks:
    - name: Test MongoDB connection
      ansible.builtin.command: "python3 -c 'import pymongo; client = pymongo.MongoClient(\"mongodb://localhost:27017\"); client.admin.command(\"ping\")'"
      register: mongodb_connection_test
      failed_when: mongodb_connection_test.rc != 0
      tags: [mongodb, test]
  tasks:
    - name: Update and upgrade all packages
      ansible.builtin.apt:
        update_cache: true
        upgrade: dist
        cache_valid_time: 3600
      environment:
        http_proxy: "{{ http_proxy }}"
        https_proxy: "{{ https_proxy }}"
      tags: [system]

    - name: Install required dependencies
      ansible.builtin.apt:
        name:
          - git
          - python3
          - python3-pip
          - python3-venv
          - apache2
          - libapache2-mod-proxy-uwsgi
          - uwsgi
          - uwsgi-plugin-python3
          - build-essential
          - python3-dev
          - curl
          - gnupg
          - ufw
          - net-tools
          - sudo
          - ca-certificates
          - ntp
        state: present
      environment:
        http_proxy: "{{ http_proxy }}"
        https_proxy: "{{ https_proxy }}"
      tags: [dependencies]
```

### 2. Inventory anpassen
Erstelle oder bearbeite deine Ansible-Inventory-Datei (z. B. `inventory.yml`), um das Zielsystem zu definieren:

```yaml
all:
  hosts:
    cmdb-syncer:
      ansible_host: <IP-oder-Hostname-des-Zielsystems>
      ansible_user: <SSH-Benutzer>
      ansible_ssh_private_key_file: <Pfad-zum-SSH-Schlüssel>  # Optional
```

Ersetze `<IP-oder-Hostname-des-Zielsystems>` durch die IP-Adresse oder den Hostnamen des Debian 12 Systems und passe den SSH-Benutzer und Schlüssel an.

### 3. Playbook ausführen
Führe das Playbook aus, um den CMDB-Syncer zu installieren:

```bash
ansible-playbook install_cmdb_syncer_on_debian_12.yml -i inventory.yml
```

Wenn du Sudo-Berechtigungen benötigst, füge die Option `--ask-become-pass` hinzu, um das Sudo-Passwort einzugeben:
```bash
ansible-playbook install_cmdb_syncer_on_debian_12.yml -i inventory.yml --ask-become-pass
```

### 4. Aufgaben des Playbooks
Das Playbook führt folgende Schritte aus:
1. **Installation von Paketen**: Installiert `python3`, `python3-pip`, `python3-venv`, `git`, `gnupg` und `curl` über `apt`.
2. **Benutzererstellung**: Erstellt einen Benutzer `cmdb` mit dem Home-Verzeichnis `/opt/cmdb`.
3. **MongoDB-Installation**: Importiert die Aufgabe `install_mongodb.yml`, um MongoDB (Version 8.0) zu installieren.
4. **Repository klonen**: Klont das CMDB-Syncer-Repository von [kuhn-ruess/cmdbsyncer]([https://github.com/kuhn-ruess/cmdbsyncer]) nach `/opt/cmdb/cmdb-syncer`.
5. **Python-Abhängigkeiten**: Installiert die erforderlichen Python-Pakete aus `requirements.txt` in einer virtuellen Umgebung (`/opt/cmdb/venv`).
6. **Systemd-Dienst**: Kopiert die `cmdb-syncer.service`-Datei nach `/etc/systemd/system` und aktiviert/startet den Dienst.

### 5. Überprüfen der Installation
Nach der Ausführung des Playbooks:
1. Prüfe, ob der CMDB-Syncer-Dienst läuft:
   ```bash
   systemctl status cmdbsyncer
   ```
2. Überprüfe die MongoDB-Installation:
   ```bash
   mongod --version
   ```
3. Stelle sicher, dass das Verzeichnis `/opt/cmdb/cmdb-syncer` die geklonte Repository-Struktur enthält:
   ```bash
   ls /var/www/cmdbsyncer
   ```

### 6. Fehlerbehandlung
- **AVX-Fehler bei MongoDB**: Wenn MongoDB nicht startet, überprüfe die AVX-Unterstützung (siehe Hinweis oben). Stelle sicher, dass die VM den korrekten CPU-Typ verwendet.
- **Paketinstallation fehlschlägt**: Überprüfe die `apt`-Quellen und die Internetverbindung des Zielsystems.
- **Git-Fehler**: Stelle sicher, dass die URL `https://github.com/kuhn-ruess/cmdbsyncer` erreichbar ist und keine Authentifizierung erfordert.
- **Systemd-Dienst startet nicht**: Überprüfe die Protokolle (`journalctl -u cmdbsyncer`) und die Berechtigungen der Datei `/etc/systemd/system/cmdbsyncer.service`.
- **Python-Abhängigkeiten**: Stelle sicher, dass `requirements.txt` im geklonten Repository vorhanden ist und die virtuelle Umgebung korrekt erstellt wurde.

## Hinweise
- **Proxmox AVX-Unterstützung**: Ohne AVX-Unterstützung schlägt die MongoDB-Installation fehl. Überprüfe und konfiguriere die CPU-Einstellungen sorgfältig, bevor du das Playbook ausführst.
- **MongoDB-Version**: Das Playbook verwendet MongoDB 6.0. Für andere Versionen passe die Variable `mongodb_version` an und überprüfe die Kompatibilität.
- **Systemd-Dienstdatei**: Stelle sicher, dass die Datei `cmdb-syncer.service` im gleichen Verzeichnis wie das Playbook liegt, da sie vom Playbook kopiert wird.
- **Sicherheit**: Erwäge, sensible Daten (z. B. SSH-Schlüssel oder MongoDB-Zugangsdaten) in einer Ansible Vault-Datei zu speichern.
- **Dokumentation**: Weitere Details zum CMDB-Syncer findest du im Repository [kuhn-ruess/cmdbsyncer](https://github.com/kuhn-ruess/cmdbsyncer). Für Ansible-spezifische Fragen siehe die [Ansible-Dokumentation](https://docs.ansible.com).
- **Anpassungen**: Passe die Variablen `cmdb_dir`, `cmdb_user`, `cmdb_group` oder `cmdb_repo` an, wenn du eine andere Verzeichnisstruktur, einen anderen Benutzer oder ein anderes Repository verwenden möchtest.

## Fazit
Einfacher geht es nicht .... ;)
