# Network Monitoring

This guide covers network monitoring for Jetson AGX Orin.

## Bandwidth Monitoring

```bash
# Install nload
sudo apt install nload

# Monitor bandwidth
nload
nload -u m eth0  # Megabits

# iptraf
sudo apt install iptraf-ng
sudo iptraf-ng
```

## nethogs

```bash
sudo apt install nethogs

# Monitor per-process bandwidth
sudo nethogs
sudo nethogs eth0
```

## iftop

```bash
sudo apt install iftop

# Show bandwidth
sudo iftop
sudo iftop -P -n
```

## bmon

```bash
sudo apt install bmon

# Show bandwidth
bmon -p eth0
```

## Network Stats

```bash
# Network statistics
netstat -s

# Active connections
ss -tunapl

# Connection count
ss -state established | wc -l
```

## Prometheus Network Exporter

```yaml
# node_network_receive_bytes_total
# node_network_transmit_bytes_total
```

```python
from prometheus_client import start_http_server, Gauge
import time

network_receive = Gauge('network_receive_bytes', 'Network receive bytes')
network_transmit = Gauge('network_transmit_bytes', 'Network transmit bytes')

def collect_network():
    with open('/proc/net/dev') as f:
        for line in f:
            if 'eth0' in line:
                fields = line.split()
                receive = int(fields[1])
                transmit = int(fields[9])
                network_receive.set(receive)
                network_transmit.set(transmit)
```

## iPerf

```bash
# Server
iperf -s

# Client
iperf -c server_ip
iperf -c server_ip -t 30 -i 1  # 30 seconds
```

## Network Latency

```bash
# Ping
ping -c 10 google.com

# MTR
sudo apt install mtr-tiny
mtr google.com
```

## TCP Tuning

```bash
# Increase TCP buffer
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# Make permanent
echo "net.core.rmem_max=16777216" >> /etc/sysctl.conf
```

## Connection Tracking

```bash
# Check connection tracking
cat /proc/net/nf_conntrack | wc -l

# Max connections
cat /proc/sys/net/netfilter/nf_conntrack_max
```

## Firewall Monitoring

```bash
# View firewall rules
sudo iptables -L -n -v

# Connection states
sudo conntrack -L
sudo conntrack -L -p tcp --state ESTABLISHED | wc -l
```

## DNS Monitoring

```bash
# Check DNS
nslookup google.com
dig google.com

# DNS performance
dig +stats google.com
```

## Web Server Logs

```bash
# Apache/Nginx access log
tail -f /var/log/nginx/access.log

# Popular URLs
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Response codes
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
```

## API Monitoring

```python
from prometheus_client import Counter, Histogram

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'status']
)

request_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

@app.middleware("http")
async def monitor(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).observe(duration)
    
    request_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response
```

## Network Troubleshooting

```bash
# Check open ports
netstat -tulpn

# Check routes
ip route

# Check DNS
cat /etc/resolv.conf

# Check MTU
ip link show eth0
```
