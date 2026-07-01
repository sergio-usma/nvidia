# Intrusion Detection

This guide covers intrusion detection systems for Jetson AGX Orin.

## AIDE

```bash
# Install
sudo apt install aide

# Initialize database
sudo aideinit

# Move database
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Check integrity
sudo aide --check

# Update database
sudo aide --update
```

## OSSEC

```bash
# Install
sudo apt install ossec-hids-server

# Configure
sudo nano /var/ossec/etc/ossec.conf
```

## RKHunter

```bash
# Install
sudo apt install rkhunter

# Update
sudo rkhunter --update

# Scan
sudo rkhunter --check

# Schedule
sudo rkhunter --cronjob
```

## Logwatch

```bash
# Install
sudo apt install logwatch

# Configure
sudo nano /etc/logwatch/conf/logwatch.conf
```

## Lynis

```bash
# Install
sudo apt install lynis

# Audit
sudo lynis audit system

# Hardening
sudo lynis audit system --hardening
```

## Tripwire

```bash
# Install
sudo apt install tripwire

# Initialize
sudo twadmin --create-polfiles
sudo tripwire --init
```

## Fail2Ban

```bash
# Install
sudo apt install fail2ban

# Configure
sudo nano /etc/fail2ban/jail.local

[DEFAULT]
bantime = 3600
findtime = 600

[sshd]
enabled = true
```

## CrowdSec

```bash
# Install
curl -s https://packagecloud.io/install/repositories/crowdsec/crowdsec/script.deb.sh | sudo bash
sudo apt install crowdsec

# Install firewall bouncer
sudo apt install crowdsec-firewall-bouncer-iptables
```

## Suricata

```bash
# Install
sudo apt install suricata

# Update rules
sudo suricata-update

# Run
sudo suricata -c /etc/suricata/suricata.yaml -i eth0
```

## Automated Alerts

```python
#!/usr/bin/env python3
import subprocess
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'security@localhost'
    msg['To'] = 'admin@localhost'
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)

# Check for rootkits
result = subprocess.run(['rkhunter', '--check'], capture_output=True, text=True)
if 'Warning' in result.stdout or 'Error' in result.stdout:
    send_alert('RKHunter Alert', result.stdout)

# Check failed logins
result = subprocess.run(['last', '-f', '/var/log/btmp'], capture_output=True, text=True)
if result.stdout:
    send_alert('Failed Logins', result.stdout)
```

## Network Intrusion Detection

```yaml
# /etc/suricata/suricata.yaml
af-packet:
  - interface: eth0
    cluster-id: 1

vars:
  address-groups:
    HOME_NET: "[192.168.1.0/24]"

rules:
  - pass ip any any -> any any (msg:" whitelist"; sid:1;)
  - alert tcp any any -> any 22 (msg:"SSH connection"; sid:2;)
```
