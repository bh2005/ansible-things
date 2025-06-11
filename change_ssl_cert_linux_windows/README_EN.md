# SSL Certificate Replacement Playbook

This Ansible playbook automates the replacement of SSL certificates on various operating systems (Debian/Ubuntu, RHEL/CentOS, SUSE, Windows) for Apache, Nginx, or IIS web servers.

## Prerequisites

- Ansible 2.9 or newer
- SSH or WinRM access to target hosts
- Certificate files (*.crt) in the input folder on the Ansible Control Host
- Root or administrator privileges on target hosts
- Installed packages on target hosts:
  - Debian/Ubuntu: `apache2` or `nginx`
  - RHEL/CentOS: `httpd` or `nginx`
  - SUSE: `apache2` or `nginx`
  - Windows: IIS (W3SVC service)

## Directory Structure

```plaintext
/path/to/certificate/         # Input folder for new certificates (*.crt)
/path/to/done_folder/      # Destination folder for processed certificates
```

## File Naming Convention

Certificate files must include the hostname in the filename, e.g.:
- `certificate_hostname.crt`
- The hostname is extracted and matched with `inventory_hostname`.

## Playbook Description

1. **Find Certificates**: Searches for `*.crt` files in the input folder on the Control Host.
2. **Extract Hostname**: Extracts the hostname from the certificate filename.
3. **Replace Certificate**:
   - **Linux (Debian/Ubuntu, RHEL/CentOS, SUSE)**:
     - Copies the certificate to the appropriate folder (`/etc/apache2/ssl/`, `/etc/httpd/ssl/`, or `/etc/nginx/ssl/`).
     - Restarts the web server (`apache2`, `httpd`, or `nginx`).
   - **Windows**:
     - Checks if IIS (W3SVC) is present.
     - Copies the certificate temporarily to `C:\Windows\Temp\`.
     - Imports the certificate into the `WebHosting` store.
     - Updates the IIS web binding for HTTPS.
     - Restarts IIS.
     - Supports OpenSSH (Port 22) or WinRM (Port 5985) for connectivity.
4. **Move Certificate**: Moves processed certificates to the done folder.
5. **Delete Original**: Removes the original certificates from the input folder.

## Usage

1. Adjust the paths for `/path/to/certificate` and `/path/to/done_folder` in the playbook.
2. Ensure certificates are in the input folder and filenames include the hostname.
3. Run the playbook:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Important Notes

- The playbook checks if the hostname in the certificate filename matches `inventory_hostname`.
- On Windows, it verifies if a connection via OpenSSH or WinRM is possible.
- Errors are logged if no connection to a Windows host can be established.
- The playbook collects facts (`gather_facts: yes`) to identify the operating system and installed packages.
- Ensure target directories exist on hosts (e.g., `/etc/apache2/ssl/` or `/etc/nginx/ssl/`).

## Limitations

- Supports only Apache, Nginx, and IIS.
- Certificates must be in `.crt` format.
- Windows requires either OpenSSH or WinRM for communication.
- No support for custom certificate storage locations or web server configurations.

## Error Handling

- If a certificate does not match the current host, it is skipped.
- If no connection to a Windows host is possible, an error is reported.
- The playbook overwrites existing certificates in the target folder only if they have changed.