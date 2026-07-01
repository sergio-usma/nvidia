# VPN Setup

This guide covers VPN setup for secure remote access to Jetson AGX Orin.

## WireGuard

```bash
# Install
sudo apt install wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey
```

## WireGuard Server

```bash
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <SERVER_PRIVATE_KEY>
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <CLIENT_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32

# Enable
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

## WireGuard Client

```bash
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <CLIENT_PRIVATE_KEY>
Address = 10.0.0.2/24

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
Endpoint = server.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

## OpenVPN

```bash
# Install
sudo apt install openvpn easy-rsa

# Setup CA
cd /etc/openvpn/easy-rsa
./easyrsa init-pki
./easyrsa build-ca

# Generate server cert
./easyrsa build-server-full server nopass

# Generate client cert
./easyrsa build-client-full client nopass
```

## OpenVPN Server Config

```bash
# /etc/openvpn/server.conf
port 1194
proto udp
dev tun
ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem

server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"

keepalive 10 120
cipher AES-256-GCM
auth SHA256
persist-key
persist-tun
status openvpn-status.log
verb 3
```

## Client Configuration

```bash
# client.ovpn
client
dev tun
proto udp
remote server.example.com 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
verb 3
```

## SSH Tunnel

```bash
# Create tunnel
ssh -D 1080 -f -N user@jetson

# Tunnel with key
ssh -i key.pem -D 1080 -f -N user@jetson
```

## Dynamic DNS

```bash
# Install ddclient
sudo apt install ddclient

# Configure
sudo nano /etc/ddclient.conf
```

```
protocol=Cloudflare
server=api.cloudflare.com
login=your-email@example.com
password=your-api-key
your-domain.com
```

## Firewall Rules for VPN

```bash
# Allow VPN
sudo ufw allow 51820/udp  # WireGuard
sudo ufw allow 1194/udp   # OpenVPN

# NAT for VPN clients
sudo iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE
```
