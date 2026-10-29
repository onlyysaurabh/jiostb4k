#!/bin/bash
# Pull all installed APKs from JioSTB via ADB over Wi-Fi/Ethernet

STB_IP="192.168.2.137"
PORT="5555"
OUT_DIR="./dumped_apks"

echo "=========================================================="
echo " Jio STB APK & Asset Extraction Utility"
echo " Target IP: $STB_IP:$PORT"
echo " Destination: $OUT_DIR"
echo "=========================================================="

mkdir -p "$OUT_DIR"

echo "[+] Connecting to $STB_IP:$PORT..."
adb connect "$STB_IP:$PORT"

if ! adb devices | grep -q "$STB_IP:$PORT.*device"; then
    echo "[-] Device not connected or unauthorized."
    echo "[!] Ensure Developer Options -> USB/Network Debugging is enabled on the STB."
    exit 1
fi

echo "[+] Device connected successfully!"
echo "[+] Listing installed packages..."
adb shell pm list packages -f > "$OUT_DIR/package_list.txt"

echo "[+] Pulling system and operator (Jio) APKs..."
grep -E "jio|skyworth|amlogic|launcher|ott|tv" "$OUT_DIR/package_list.txt" | while read -r line; do
    apk_path=$(echo "$line" | sed 's/package://' | sed 's/=[^=]*$//')
    pkg_name=$(echo "$line" | awk -F'=' '{print $NF}')
    echo "[*] Pulling $pkg_name ($apk_path)..."
    adb pull "$apk_path" "$OUT_DIR/${pkg_name}.apk"
done

echo "[+] Completed! APKs saved to $OUT_DIR/"
