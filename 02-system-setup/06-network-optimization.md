# Network Optimization

Optimize your Jetson's network settings for better performance, especially important when downloading large models.

## Enable Maximum Performance Mode

First, ensure maximum performance mode is enabled:

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

## Optimize Kernel Parameters

Edit `/etc/sysctl.conf`:

```bash
sudo nano /etc/sysctl.conf
```

Add these lines at the end:

```bash
# Disable IPv6 (avoid latency in name resolution)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1

# Increase TCP buffers for high-speed downloads
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_window_scaling = 1
```

Apply changes:

```bash
sudo sysctl -p
```

## Optimize MTU

Check your current MTU:

```bash
ip link show eth0
```

If needed, adjust MTU to avoid packet fragmentation:

```bash
sudo ip link set dev eth0 mtu 1450
```

## Optimize APT Downloads

Create optimization config:

```bash
sudo nano /etc/apt/apt.conf.d/99parallel
```

Add:

```bash
Acquire::Languages "none";
Acquire::Queue-Mode "access";
Acquire::Retries "3";
Acquire::http::Pipeline-Depth "5";
```

## Install aria2 for Fast Downloads

For very large files, use aria2 with multi-threaded downloads:

```bash
sudo apt install aria2 -y
```

Example usage:

```bash
aria2c -x 16 -s 16 "URL_TO_LARGE_FILE"
```

## Verify Optimization

Test your connection speed:

```bash
ping -c 10 google.com
```

Look for:
- 0% packet loss
- Stable response times

## Next Steps

Now that your system is optimized, proceed to:
- [Docker Basics](part-2-docker/01-docker-basics.md) - Learn containerization
- [Python Environment Setup](part-3-python-environment/01-python-setup.md) - Set up Python
