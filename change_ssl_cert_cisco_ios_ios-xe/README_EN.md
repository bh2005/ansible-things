# SSL Certificate Replacement Playbook for Cisco Switches

This Ansible playbook automates the replacement of SSL certificates on Cisco switches running IOS or IOS-XE for the HTTPS management interface.

## Prerequisites

- Ansible 2.9 or newer
- `cisco.ios` collection (`ansible-galaxy collection install cisco.ios`)
- SSH access to Cisco switches with Enable mode
- Certificate files (*.crt) and optionally private keys (*.p12) in the input folder on the Ansible Control Host
- Privileged rights (Enable mode) on the switches
- Cisco switches running IOS/IOS-XE that support HTTPS and `crypto pki`

## Directory Structure

```plaintext
/path/to/certificate/           # Input folder for new certificates (*.crt, *.p12)
/path/to/done_folder/          # Destination folder for processed certificates
```

## File Naming Convention

Certificate files must include the hostname in the filename, e.g.:
- `certificate_hostname.crt` (Certificate in PEM format)
- Optional: `certificate_hostname.p12` (PKCS12 file containing certificate and key)
- The hostname is extracted and matched with `inventory_hostname`.

## Playbook Description

1. **Find Certificates**: Searches for `*.crt` files in the input folder on the Control Host.
2. **Extract Hostname**: Extracts the hostname from the certificate filename.
3. **Replace Certificate**:
   - Creates or updates a trustpoint (`crypto pki trustpoint`).
   - Imports the certificate (PEM format) and optionally the private key (PKCS12).
   - Configures the HTTPS server with the new trustpoint.
   - Saves the configuration persistently.
4. **Move Certificate**: Moves processed certificates to the done folder.
5. **Delete Original**: Removes the original certificates from the input folder.

## Usage

1. Adjust the paths for `cert_input_path` and `cert_done_path` in the playbook.
2. Ensure certificates are in the input folder and filenames include the hostname.
3. Configure the `cisco_switches` inventory group with SSH credentials and Enable password.
4. Run the playbook:

```bash
ansible-playbook playbook.yml -i inventory.yml
```

## Important Notes

- The playbook checks if the hostname in the certificate filename matches `inventory_hostname`.
- Enable mode is required for configuration changes (`become: yes`, `become_method: enable`).
- Certificates must be in PEM format; private keys are optional in PKCS12 format.
- Test the playbook in a lab environment before deploying in production.
- Ensure the HTTPS server is enabled on the switch (`ip http secure-server`).

## Limitations

- Supports only Cisco switches running IOS/IOS-XE.
- Certificates must be in `.crt` format (PEM); keys optionally in `.p12` format.
- No support for other protocols (e.g., SNMP-based certificate management).
- A switch restart may be required if the HTTPS server does not update correctly.

## Error Handling

- If a certificate does not match the current host, it is skipped.
- Errors during certificate import (e.g., invalid format) are logged.
- The playbook saves the configuration only if changes are made.

## Resources

- Cisco IOS Configuration for Certificates: [Ansible Documentation for cisco.ios](https://docs.ansible.com/ansible/latest/collections/cisco/ios/ios_config_module.html)
- Certificate Import for Cisco Devices: [Cisco Community](https://community.cisco.com/t5/networking-knowledge-base/generating-rsa-keys-certificates-using-ansible/td-p/4683548)