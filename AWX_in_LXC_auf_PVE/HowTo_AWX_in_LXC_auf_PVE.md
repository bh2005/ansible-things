# AWX in einem LXC-Container (Debian 12) auf Proxmox VE installieren

Diese Anleitung beschreibt die Einrichtung eines **privilegierten LXC-Containers** auf Proxmox VE und die Installation von **AWX** mit **Docker Compose** und einem **Nginx Reverse Proxy** innerhalb des Containers.

## Wichtige Hinweise
- Diese Anleitung verwendet die Docker Compose-basierte Installation von AWX, die für kleinere Umgebungen oder Tests geeignet ist. Für Produktionsumgebungen wird die AWX Operator-Installation auf Kubernetes/OpenShift empfohlen.
- Privilegierte LXC-Container bieten weniger Isolation als unprivilegierte Container. Verwenden Sie sie nur in vertrauenswürdigen Umgebungen.
- Die Konfiguration enthält **kein SSL** für Nginx. Für den Produktionseinsatz ist SSL (z. B. mit Let’s Encrypt) erforderlich.
- Aktualisieren Sie die **AWX-Version** (`awx_version`) im Playbook auf die neueste stabile Version von den [offiziellen AWX GitHub Releases](https://github.com/ansible/awx/releases).

---

## Schritt 1: LXC-Container auf Proxmox VE erstellen und konfigurieren

1. **Melden Sie sich an der Proxmox VE GUI an.**
2. **Laden Sie ein Debian 12 Template herunter:**
   - Navigieren Sie zu Ihrem Proxmox VE Host im linken Baummenü.
   - Wählen Sie den Bereich **"Local"** (oder Ihren Speicher für Templates).
   - Gehen Sie zum Tab **"CT Templates"**.
   - Klicken Sie auf **"Templates"**, suchen Sie nach `debian-12-standard`, wählen Sie es aus und klicken Sie auf **"Download"**.
3. **Erstellen Sie einen neuen Container (CT):**
   - Klicken Sie in der Proxmox GUI auf **"Create CT"**.
   - **General:**
     - **Host Name:** z. B. `awx-lxc`.
     - **Password:** Vergeben Sie ein starkes Root-Passwort.
   - **Template:** Wählen Sie das `debian-12-standard` Template.
   - **Disk size:** Mindestens **20 GB** (mehr für größere Installationen).
   - **CPU:** Mindestens **2** Cores.
   - **Memory:** Mindestens **4096 MiB (4 GB)** RAM.
   - **Network:** Konfigurieren Sie eine **statische IP-Adresse** für Netzwerkzugriff.
   - **DNS:** Standardeinstellungen sind ausreichend.
   - **Confirm:** Überprüfen Sie die Einstellungen und klicken Sie auf **"Finish"**. Aktivieren Sie **"Start after created"**.
4. **Container-Features konfigurieren:**
   - Wählen Sie den erstellten Container (z. B. `101 (awx-lxc)`) im Baummenü.
   - Gehen Sie zum Tab **"Options"** → **"Features"**.
   - Aktivieren Sie die Checkbox **"Nesting"** und klicken Sie auf **"OK"**.
   - Für Docker-Kompatibilität:
     - Gehen Sie zu **"Options"** → **"LXC Container"** → **"Edit"**.
     - Fügen Sie am Ende der Konfigurationsdatei hinzu:
       ```ini
       lxc.apparmor.profile: unconfined
       lxc.cgroup.devices.allow: a
       lxc.cap.keep: sys_admin
       lxc.mount.auto: cgroup:rw
       lxc.mount.entry: /sys/fs/cgroup cgroup cgroup defaults 0 0
       ```
     - Klicken Sie auf **"OK"**.
5. **Starten Sie den Container:**
   - Klicken Sie auf **"Start"** (grüner Pfeil).
6. **Ermitteln Sie die IP-Adresse:**
   - Gehen Sie zum Tab **"Summary"** des Containers, um die IP-Adresse zu sehen.

---

## Schritt 2: SSH-Zugriff auf den LXC-Container einrichten

1. **Öffnen Sie die Konsole des Containers:**
   - Wählen Sie den Container im Baummenü und gehen Sie zum Tab **"Console"**.
   - Melden Sie sich als `root` mit dem festgelegten Passwort an.
2. **System aktualisieren und SSH-Server installieren:**
   ```bash
   apt update && apt upgrade -y
   apt install -y openssh-server
   ```
3. **Optional: Neuen Benutzer erstellen (empfohlen):**
   ```bash
   adduser <Ihr_Benutzername>
   usermod -aG sudo <Ihr_Benutzername>
   ```
   Ersetzen Sie `<Ihr_Benutzername>` durch Ihren gewünschten Benutzernamen.
4. **SSH-Dienst starten und aktivieren:**
   ```bash
   systemctl start ssh
   systemctl enable ssh
   ```
5. **Verlassen Sie die Konsole.**
6. **Testen Sie den SSH-Zugriff:**
   ```bash
   ssh <Ihr_Benutzername>@<IP_des_LXC_Containers>
   ```

---

## Schritt 3: Ansible Playbook und Nginx-Template vorbereiten

1. **Erstellen Sie das Ansible-Playbook auf Ihrem lokalen Rechner:**
   - Erstellen Sie ein Verzeichnis, z. B. `~/ansible_awx_lxc/`.
   - Speichern Sie das Playbook als `install_awx_lxc.yml`:

     ```yaml
     ---
     - name: Install AWX on LXC (Debian 12) with Docker Compose and Nginx Reverse Proxy
       hosts: localhost
       connection: local
       become: yes
       vars:
         awx_version: "24.6.1"
         awx_install_dir: "/opt/awx"
         awx_extracted_dir: "{{ awx_install_dir }}/awx-{{ awx_version }}"
         awx_installer_path: "{{ awx_extracted_dir }}/installer"
         awx_admin_password: "YOUR_VERY_STRONG_ADMIN_PASSWORD"
         awx_secret_key: "YOUR_VERY_LONG_RANDOM_SECRET_KEY"
         nginx_awx_port: 80
         nginx_listen_port: 80
       tasks:
         - name: Ensure Python and pip are installed
           ansible.builtin.apt:
             name:
               - python3
               - python3-pip
               - virtualenv
             state: present
             update_cache: yes
           tags:
             - setup
         - name: Update apt cache and upgrade packages
           ansible.builtin.apt:
             update_cache: yes
             upgrade: dist
           tags:
             - setup
         - name: Install essential packages
           ansible.builtin.apt:
             name:
               - curl
               - gnupg
               - lsb-release
               - git
             state: present
           tags:
             - setup
         - name: Add Docker GPG apt key
           ansible.builtin.apt_key:
             url: https://download.docker.com/linux/debian/gpg
             state: present
             keyring: /etc/apt/keyrings/docker.gpg
           tags:
             - docker
         - name: Add Docker apt repository
           ansible.builtin.apt_repository:
             repo: "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian {{ ansible_distribution_release }} stable"
             state: present
             filename: /etc/apt/sources.list.d/docker.list
             update_cache: yes
           tags:
             - docker
         - name: Install Docker Engine and Docker Compose Plugin
           ansible.builtin.apt:
             name:
               - docker-ce
               - docker-ce-cli
               - containerd.io
               - docker-buildx-plugin
               - docker-compose-plugin
             state: present
           tags:
             - docker
         - name: Ensure docker service is running and enabled
           ansible.builtin.systemd:
             name: docker
             state: started
             enabled: yes
           tags:
             - docker
         - name: Add current user to docker group
           ansible.builtin.user:
             name: "{{ ansible_user_id }}"
             groups: docker
             append: yes
           notify:
             - Restart Docker for group changes
           when: ansible_user_id != "root"
           tags:
             - docker
         - name: Create AWX installation base directory
           ansible.builtin.file:
             path: "{{ awx_install_dir }}"
             state: directory
             mode: '0755'
           tags:
             - awx_install
         - name: Download and extract AWX source code
           ansible.builtin.unarchive:
             src: "https://github.com/ansible/awx/archive/refs/tags/{{ awx_version }}.tar.gz"
             dest: "{{ awx_install_dir }}"
             remote_src: yes
             creates: "{{ awx_extracted_dir }}"
           tags:
             - awx_install
         - name: Verify AWX installer directory exists
           ansible.builtin.stat:
             path: "{{ awx_installer_path }}"
           register: awx_installer_dir_check
           failed_when: not awx_installer_dir_check.stat.exists or not awx_installer_dir_check.stat.isdir
           changed_when: false
           tags:
             - awx_install
         - name: Verify AWX inventory file exists
           ansible.builtin.stat:
             path: "{{ awx_installer_path }}/inventory"
           register: awx_inventory_file_check
           failed_when: not awx_inventory_file_check.stat.exists or not awx_inventory_file_check.stat.isreg
           changed_when: false
           tags:
             - awx_config
         - name: Copy AWX inventory file template
           ansible.builtin.copy:
             src: "{{ awx_installer_path }}/inventory"
             dest: "{{ awx_installer_path }}/inventory.bak"
             remote_src: yes
           tags:
             - awx_config
         - name: Configure AWX inventory file
           ansible.builtin.blockinfile:
             path: "{{ awx_installer_path }}/inventory"
             block: |
               [all:vars]
               container_engine=docker
               pg_hostname=localhost
               pg_port=5432
               pg_database=awx
               pg_username=awx
               pg_password=awx
               admin_user=admin
               admin_password={{ awx_admin_password }}
               secret_key={{ awx_secret_key }}
               awx_port={{ nginx_awx_port }}
             marker: "# {mark} ANSIBLE MANAGED BLOCK - AWX CONFIGURATION"
           tags:
             - awx_config
         - name: Run AWX installer playbook
           ansible.builtin.command: "ansible-playbook -i inventory install.yml"
           args:
             chdir: "{{ awx_installer_path }}"
           register: awx_install_result
           changed_when: awx_install_result.rc == 0 and "PLAY RECAP" in awx_install_result.stdout
           tags:
             - awx_install
         - name: Display AWX installation result
           ansible.builtin.debug:
             msg: "{{ awx_install_result.stdout }}"
           when: awx_install_result is defined
           tags:
             - awx_install
         - name: Install Nginx
           ansible.builtin.apt:
             name: nginx
             state: present
           tags:
             - nginx
         - name: Remove default Nginx site configuration
           ansible.builtin.file:
             path: /etc/nginx/sites-enabled/default
             state: absent
           notify:
             - Restart Nginx
           tags:
             - nginx
         - name: Configure Nginx for AWX
           ansible.builtin.template:
             src: awx_nginx.conf.j2
             dest: /etc/nginx/sites-available/awx.conf
             mode: '0644'
           notify:
             - Restart Nginx
           tags:
             - nginx
         - name: Enable AWX Nginx site
           ansible.builtin.file:
             src: /etc/nginx/sites-available/awx.conf
             dest: /etc/nginx/sites-enabled/awx.conf
             state: link
           notify:
             - Restart Nginx
           tags:
             - nginx
         - name: Ensure Nginx service is running and enabled
           ansible.builtin.systemd:
             name: nginx
             state: started
             enabled: yes
           tags:
             - nginx
         - name: Enable AWX Docker Compose to start on boot
           ansible.builtin.copy:
             content: |
               [Unit]
               Description=AWX service (Docker Compose)
               Requires=docker.service
               After=docker.service
               [Service]
               User=root
               WorkingDirectory={{ awx_installer_path }}
               ExecStart=/usr/local/bin/docker compose -f inventory up
               ExecStop=/usr/local/bin/docker compose -f inventory down
               Restart=always
               RestartSec=3
               [Install]
               WantedBy=multi-user.target
             dest: /etc/systemd/system/awx.service
             mode: '0644'
           notify:
             - Reload systemd daemon
             - Start and enable AWX service
           tags:
             - systemd
       handlers:
         - name: Restart Docker for group changes
           ansible.builtin.systemd:
             name: docker
             state: restarted
         - name: Restart Nginx
           ansible.builtin.systemd:
             name: nginx
             state: restarted
         - name: Reload systemd daemon
           ansible.builtin.systemd:
             daemon_reload: yes
         - name: Start and enable AWX service
           ansible.builtin.systemd:
             name: awx
             state: started
             enabled: yes
     ```

2. **Erstellen Sie die Nginx-Template-Datei:**
   - Speichern Sie die folgende Datei als `awx_nginx.conf.j2` im gleichen Verzeichnis:

     ```jinja2
     server {
         listen {{ nginx_listen_port }};
         server_name localhost;
         client_max_body_size 100M;
         location / {
             proxy_pass http://localhost:{{ nginx_awx_port }};
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
             proxy_set_header X-Forwarded-Proto $scheme;
             proxy_redirect off;
         }
         error_page 500 502 503 504 /50x.html;
         location = /50x.html {
             root /usr/share/nginx/html;
         }
     }
     ```

3. **Kopieren Sie die Dateien in den LXC-Container:**
   - Wechseln Sie auf Ihrem lokalen Rechner in das Verzeichnis (`cd ~/ansible_awx_lxc/`) und kopieren Sie die Dateien:
     ```bash
     scp -r . <Ihr_Benutzername>@<IP_des_LXC_Containers>:/home/<Ihr_Benutzername>/awx_install_files/
     ```

---

## Schritt 4: Ansible im LXC-Container ausführen

1. **Melden Sie sich per SSH am Container an:**
   ```bash
   ssh <Ihr_Benutzername>@<IP_des_LXC_Containers>
   ```

2. **Navigieren Sie zum Verzeichnis mit den Ansible-Dateien:**
   ```bash
   cd /home/<Ihr_Benutzername>/awx_install_files/
   ```

3. **Installieren Sie Ansible im Container:**
   ```bash
   sudo apt update
   sudo apt install -y ansible python3-apt
   ```

4. **Führen Sie das Ansible-Playbook aus:**
   - Passen Sie `awx_version`, `awx_admin_password` und `awx_secret_key` in `install_awx_lxc.yml` an.
   - Führen Sie das Playbook aus:
     ```bash
     ansible-playbook install_awx_lxc.yml --ask-become-pass
     ```

---

## Schritt 5: AWX-Installation überprüfen

1. **Überprüfen Sie die Dienste:**
   ```bash
   sudo systemctl status docker
   sudo systemctl status nginx
   sudo systemctl status awx
   sudo docker ps
   ```
   Alle Dienste sollten als `running` oder `active` angezeigt werden.

2. **Zugriff auf die AWX-Weboberfläche:**
   - Öffnen Sie einen Browser und navigieren Sie zu:
     ```
     http://<IP_des_LXC_Containers>
     ```

3. **Anmelden bei AWX:**
   - **Benutzername:** `admin`
   - **Passwort:** Das in `awx_admin_password` festgelegte Passwort.

---

## Nächste Schritte
- Konfigurieren Sie **SSL/TLS** für eine sichere Verbindung (z. B. mit Let’s Encrypt).
- Überwachen Sie die AWX-Instanz und planen Sie regelmäßige Backups.
- Erwägen Sie die Migration zu einer Kubernetes-basierten AWX-Installation für Produktionsumgebungen.