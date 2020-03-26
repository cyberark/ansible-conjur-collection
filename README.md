## CyberArk Ansible Conjur Collection

****

### cyberark.conjur

This collection is the CyberArk Ansible Conjur project and can be found on [ansible galaxy](https://galaxy.ansible.com/cyberark/conjur).

### Requirements

- [CyberArk Conjur Open Source](https://www.conjur.org) or
- [CyberArk Dynamic Access Provider](https://docs.cyberark.com/Product-Doc/OnlineHelp/AAM-DAP/Latest/en/Content/Resources/_TopNav/cc_Home.htm)

### Role Variables

None.
<br>
<br>

## Plugins

### conjur_variable Lookup Plugin

- Retrieves credentials from Conjur using the controlling host's Conjur identity or environment variables.
- The controlling host running Ansible has a Conjur identity. (More: U(https://docs.conjur.org/latest/en/Content/Get%20Started/key_concepts/machine_identity.html))
- Environment variables could be CONJUR_ACCOUNT, CONJUR_APPLIANCE_URL, CONJUR_CERT_FILE, CONJUR_AUTHN_LOGIN, CONJUR_AUTHN_API_KEY


### Author Information
- CyberArk Business Development Technical Team 
    - @enunez-cyberark
    - @cyberark-bizdev
    - @jimmyjamcabd
