#!/usr/bin/env bash
# ==============================================================================
# Jio 4K Set-Top Box (JMSB200A) - Firmware & Partition Asset Downloader
# ==============================================================================
# Fetches official firmware archives, partitions, and system APKs from the
# GitHub Release (v25.1.9) without requiring Git LFS or hitting clone bandwidth limits.
# ==============================================================================

set -euo pipefail

REPO="onlyysaurabh/jiostb4k"
TAG="v25.1.9"
BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

OTA_DIR="${ROOT_DIR}/ota_packages"
PARTITIONS_DIR="${OTA_DIR}/extracted/partitions"
EXTRACTED_DIR="${OTA_DIR}/extracted"

mkdir -p "${OTA_DIR}" "${PARTITIONS_DIR}" "${EXTRACTED_DIR}"

usage() {
    cat <<EOF
Usage: $0 [MODE]

Available Modes:
  --all            Download everything: partitions, APKs, raw payload, and OTA zip (~3.9 GB)
  --partitions     Download only the 12 flashable partition images (~1.9 GB)
  --boot           Download only boot components: boot.img, vendor_boot.img, bootloader.img, dtbo.img (~93 MB)
  --apks           Download and unpack the 88 system/carrier APKs (548 MB archive)
  --ota-archive    Download only the raw original loOOGaJIPm.zip OTA package (756 MB)
  --help           Show this message

EOF
    exit "${1:-1}"
}

download_file() {
    local filename="$1"
    local dest_dir="$2"
    local target_path="${dest_dir}/${filename}"

    if [ -f "${target_path}" ]; then
        echo "[+] ${filename} already exists in ${dest_dir}, skipping."
        return 0
    fi

    echo "[*] Downloading ${filename}..."
    if command -v gh &>/dev/null && gh auth status &>/dev/null; then
        gh release download "${TAG}" --repo "${REPO}" --pattern "${filename}" --dir "${dest_dir}"
    else
        curl -fL --progress-bar "${BASE_URL}/${filename}" -o "${target_path}"
    fi
    echo "[✓] Downloaded ${filename}"
}

download_partitions() {
    echo "[*] Fetching partition images to ${PARTITIONS_DIR}..."
    local parts=(
        "bootloader.img"
        "boot.img"
        "vendor_boot.img"
        "dtbo.img"
        "vbmeta_system.img"
        "system.img"
        "product.img"
        "vendor.img"
        "system_ext.img"
        "oem.img"
        "odm_ext.img"
        "odm.img"
    )
    for part in "${parts[@]}"; do
        download_file "${part}" "${PARTITIONS_DIR}"
    done
}

download_boot() {
    echo "[*] Fetching boot & bootloader components to ${PARTITIONS_DIR}..."
    local boot_parts=(
        "bootloader.img"
        "boot.img"
        "vendor_boot.img"
        "dtbo.img"
        "vbmeta_system.img"
    )
    for part in "${boot_parts[@]}"; do
        download_file "${part}" "${PARTITIONS_DIR}"
    done
}

download_apks() {
    echo "[*] Fetching consolidated APKs archive..."
    download_file "jio_stb_apks.tar.gz" "${EXTRACTED_DIR}"
    echo "[*] Unpacking APKs to ${EXTRACTED_DIR}/apks/..."
    tar -xzf "${EXTRACTED_DIR}/jio_stb_apks.tar.gz" -C "${EXTRACTED_DIR}"
    echo "[✓] APKs ready in ${EXTRACTED_DIR}/apks/"
}

download_ota_zip() {
    echo "[*] Fetching raw OTA package..."
    download_file "loOOGaJIPm.zip" "${OTA_DIR}"
}

download_payload() {
    echo "[*] Fetching raw payload binary..."
    download_file "payload.bin" "${EXTRACTED_DIR}"
}

case "${1:-}" in
    --all)
        download_partitions
        download_apks
        download_payload
        download_ota_zip
        ;;
    --partitions)
        download_partitions
        ;;
    --boot)
        download_boot
        ;;
    --apks)
        download_apks
        ;;
    --ota-archive)
        download_ota_zip
        ;;
    --help|-h)
        usage 0
        ;;
    *)
        usage 1
        ;;
esac

echo "[✓] All requested firmware assets downloaded successfully."
