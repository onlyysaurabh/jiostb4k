#!/bin/bash
# Capture HTTP URLs and DNS queries originating from JioSTB (192.168.2.137) via OpenWrt router

ROUTER_IP="192.168.2.1"
STB_IP="192.168.2.137"
PCAP_REMOTE="/tmp/stb_capture.pcap"
PCAP_LOCAL="./stb_capture.pcap"

echo "=========================================================="
echo " Jio STB Live Traffic & Package URL Interceptor"
echo " Target STB IP: $STB_IP"
echo " OpenWrt Gateway: $ROUTER_IP"
echo "=========================================================="

echo "[+] Starting live packet capture on OpenWrt ($ROUTER_IP)..."
echo "[+] Listening for HTTP GET requests and DNS queries..."
echo "[!] TIP: Trigger 'Check for Software Update' or reboot the STB now."
echo "----------------------------------------------------------"

# Stream tcpdump output from OpenWrt to extract HTTP URLs and DNS queries in real-time
ssh root@"$ROUTER_IP" "tcpdump -i br-lan -s 0 -l -A -n 'host $STB_IP and (tcp port 80 or udp port 53)'" | while IFS= read -r line; do
    if echo "$line" | grep -q "GET "; then
        echo -e "\n\033[1;32m[HTTP REQUEST]\033[0m $line"
    elif echo "$line" | grep -q -i "^Host:"; then
        echo -e "\033[1;36m[HTTP HOST]\033[0m    $line"
    elif echo "$line" | grep -q -E "A\? |AAAA\? "; then
        dns_query=$(echo "$line" | grep -o -E "A\? [^ ]+|AAAA\? [^ ]+")
        echo -e "\033[1;33m[DNS QUERY]\033[0m    $dns_query"
    fi
done
