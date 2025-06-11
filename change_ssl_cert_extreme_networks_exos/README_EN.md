# SSL Certificate Replacement Playbook for Extreme Networks EXOS Switches

This Ansible playbook automates the replacement of SSL certificates on Extreme Networks switches running EXOS for the HTTPS management interface.

## Prerequisites

- Ansible 2.9 or newer
- `community.network` collection (`ansible-galaxy collection install community.network`)
- SSH access to EXOS switches with Enable mode (or HTTP API enabled)
- Certificate files (*.crt) and optionally private keys (*.key) in the input folder on the Ansible Control Host
- Privileged rights (Enable mode) on the switches
- Extreme Networks switches running EXOS that support HTTPS and SSL certificates

## Directory Structure

```plaintext
/path/to/certificate/           # Input folder for new certificates (*.crt, *.key)
/path/to/done_folder/          # Destination folder for processed certificates
```

## File Naming Convention

Certificate files must include the hostname in the filename, e.g.:
- `certificate_hostname.crt` (Certificate in PEM format)
- Optional: `certificate_hostname.key` (Private key in PEM format)
- The hostname is extracted and matched with `inventory_hostname`.

## Playbook Description

1. **Find Certificates**: Searches for `*.crt` files in the input folder on the Control Host.
2. **Extract Hostname**: Extracts the hostname from the certificate filename.
3. **Replace Certificate**:
   - Loads the certificate using `configure ssl certificate`.
   - Loads the private key (if provided) using `configure ssl privkey`.
   - Enables the HTTPS server (`enable web https`).
   - Restarts the web process (`restart process web`).
   - Saves the configuration persistently (`save configuration`).
4. **Move Certificate**: Moves processed certificates to the done folder.
5. **Delete Original**: Removes the original certificates from the input folder.

## Usage

1. Adjust the paths for `cert_input_path` and `cert_done_path` in the playbook.
2. Ensure certificates are in the input folder and filenames include the hostname.
3. Configure the `extreme_switches` inventory group with SSH credentials and Enable password.
4. Run the playbook:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Important Notes

- The playbook checks if the hostname in the certificate filename matches `inventory_hostname`.
- Enable mode is required for configuration changes (`become: yes`, `become_method: enable`).
- Certificates and keys must be in PEM format.
- Test the playbook in a lab environment before deploying in production.
- Ensure the HTTPS server is enabled on the switch (`enable web https`).
- For HTTP API access, change the connection to `ansible_connection: ansible.netcommon.httpapi` and configure API credentials.

## Limitations

- Supports only Extreme Networks switches running EXOS.
- Certificates must be in `.crt` format (PEM); keys in `.key` format (PEM).
- No direct support for PKCS12 files or complex certificate chains.
- Restarting the web process may briefly interrupt HTTPS access.
- Limited flexibility of `exos_command` and `exos_config` modules compared to Cisco modules.

## Error Handling

- If a certificate does not match the current host, it is skipped.
- Errors during certificate import (e.g., invalid format) are logged.
- The configuration is saved only if changes are made, avoiding unnecessary writes.

## Resources

- Ansible Documentation for EXOS: [community.network.exos_command](https://docs.ansible.com/ansible/latest/collections/community/network/exos_command_module.html)
- Extreme Networks EXOS Commands: [Extreme Networks Documentation](https://www.extremenetworks.com/support/documentation/)
- Ansible Extreme Networks Examples: [GitHub extremenetworks/ansible-extreme](https://github.com/extremenetworks/ansible-extreme)