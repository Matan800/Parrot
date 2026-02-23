#!/bin/bash
set -euo pipefail

###############################################################################
# Feature flags (set to 1 to enable, 0 to disable)
###############################################################################
ENABLE_I2S="${ENABLE_I2S:-0}"     # 1 = configure I2S audio output, 0 = skip
DISABLE_USB="${DISABLE_USB:-0}"    # 1 = disable USB at boot (power saving), 0 = keep USB enabled
DISABLE_HDMI="${DISABLE_HDMI:-1}"   # 1 = disable HDMI at boot (power saving), 0 = keep HDMI enabled

# I2S overlay selection (used only if ENABLE_I2S=1)
# Common choices:
#   - hifiberry-dac   (often works for PCM5102A-style DAC modules) [2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)[1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)
#   - max98357a       (I2S amp boards; often paired with dtparam=i2s=on) [3](https://core-electronics.com.au/guides/disable-features-raspberry-pi/)
I2S_OVERLAY="${I2S_OVERLAY:-hifiberry-dac}"
I2S_OVERLAY_OPTS="${I2S_OVERLAY_OPTS:-}"   # e.g. "no-sdmode" for max98357a,no-sdmode [3](https://core-electronics.com.au/guides/disable-features-raspberry-pi/)

###############################################################################
# Helpers
###############################################################################
log() { echo "[power-save] $*"; }

# Choose correct boot config path. Latest Raspberry Pi OS may use /boot/firmware/config.txt. [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)
BOOT_FIRMWARE_DIR="${ROOTFS_DIR}/boot/firmware"

CONFIG_TXT="${BOOT_FIRMWARE_DIR}/config.txt"
CMDLINE_TXT="${BOOT_FIRMWARE_DIR}/cmdline.txt"

ensure_line() {
  local file="$1"
  local line="$2"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if ! grep -Fxq "$line" "$file"; then
    echo "$line" >> "$file"
  fi
}

ensure_kv() {
  local file="$1"
  local key="$2"
  local value="$3"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if grep -Eq "^[#[:space:]]*${key}=" "$file"; then
    sed -i -E "s|^[#[:space:]]*${key}=.*|${key}=${value}|g" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

ensure_cmdline_token() {
  local file="$1"
  local token="$2"
  touch "$file"
  if ! grep -Eq "(^|[[:space:]])${token}([[:space:]]|$)" "$file"; then
    sed -i -E "s|\$| ${token}|" "$file"
  fi
}

# Disable onboard audio for simplicity in I2S setups by commenting dtparam=audio=on and adding audio=off. [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)[2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)
disable_onboard_audio_param() {
  local file="$1"
  touch "$file"
  if grep -Eq "^[[:space:]]*dtparam=audio=on" "$file"; then
    sed -i -E "s|^[[:space:]]*dtparam=audio=on|#dtparam=audio=on|g" "$file"
  fi
  ensure_line "$file" "dtparam=audio=off"
}

ensure_dtoverlay() {
  local file="$1"
  local overlay="$2"
  local opts="$3"

  local line="dtoverlay=${overlay}"
  [[ -n "$opts" ]] && line="dtoverlay=${overlay},${opts}"

  touch "$file"
  if ! grep -Eq "^[[:space:]]*dtoverlay=${overlay}([,[:space:]]|$)" "$file"; then
    echo "$line" >> "$file"
  else
    # If overlay exists but options differ, normalize to requested line (when opts specified)
    if [[ -n "$opts" ]] && ! grep -Fxq "$line" "$file"; then
      sed -i -E "s|^[[:space:]]*dtoverlay=${overlay}.*|${line}|g" "$file"
    fi
  fi
}

install_unit() {
  local unit_path="$1"
  local unit_content="$2"
  local full_path="${ROOTFS_DIR}${unit_path}"
  mkdir -p "$(dirname "$full_path")"
  printf "%s\n" "$unit_content" > "$full_path"
}

enable_unit() {
  local unit_name="$1"
  local wants_dir="${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
  mkdir -p "$wants_dir"
  ln -sf "../${unit_name}" "${wants_dir}/${unit_name}"
}

disable_unit() {
  local unit_name="$1"
  rm -f "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/${unit_name}"
}

###############################################################################
# Start
###############################################################################
log "Using CONFIG_TXT=${CONFIG_TXT}"
log "Using CMDLINE_TXT=${CMDLINE_TXT}"

# ---------------------------------------------------------------------------
# Base low-power settings (always applied)
# ---------------------------------------------------------------------------
ensure_line "$CONFIG_TXT" ""
ensure_line "$CONFIG_TXT" "# --- custom low-power settings ---"
ensure_line "$CONFIG_TXT" "dtoverlay=disable-bt"
ensure_line "$CONFIG_TXT" "dtparam=act_led_trigger=none"
ensure_line "$CONFIG_TXT" "dtparam=act_led_activelow=on"

# Underclock/undervolt (adjust if needed)
ensure_kv "$CONFIG_TXT" "arm_freq" "1000"
ensure_kv "$CONFIG_TXT" "arm_freq_min" "1000"
ensure_kv "$CONFIG_TXT" "over_voltage" "-6"
ensure_kv "$CONFIG_TXT" "over_voltage_min" "-6"

# CPU core limiting (remove if workload is high). 2 is minimum to enable ONNX for silero-vad
# ensure_cmdline_token "$CMDLINE_TXT" "maxcpus=2"

# ---------------------------------------------------------------------------
# I2S section (guarded by ENABLE_I2S)
# ---------------------------------------------------------------------------
if [[ "$ENABLE_I2S" == "1" ]]; then
  log "ENABLE_I2S=1 → configuring I2S audio output..."

  # Ensure dtparam=i2s=on (common step for I2S audio output). [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)[2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)[3](https://core-electronics.com.au/guides/disable-features-raspberry-pi/)
  sed -i -E '/^[[:space:]]*dtparam=i2s=/d' "$CONFIG_TXT" || true
  ensure_line "$CONFIG_TXT" "dtparam=i2s=on"

  # Disable onboard audio for simpler ALSA device selection. [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)[2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)
  disable_onboard_audio_param "$CONFIG_TXT"

  # Add the DAC/amp overlay. [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)[2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)[3](https://core-electronics.com.au/guides/disable-features-raspberry-pi/)
  ensure_dtoverlay "$CONFIG_TXT" "$I2S_OVERLAY" "$I2S_OVERLAY_OPTS"

  # Optional: Set default ALSA device to card 0 (common for single soundcard setups). [1](https://hackaday.com/2024/10/03/pi-zero-power-optimization-leaves-no-stone-unturned/)[2](https://raspberrypi.stackexchange.com/questions/96606/make-iw-wlan0-set-power-save-off-permanent)
  ASOUND_CONF="${ROOTFS_DIR}/etc/asound.conf"
  if [[ ! -f "$ASOUND_CONF" ]]; then
    cat > "$ASOUND_CONF" <<'EOF'
pcm.!default { type hw card 0 }
ctl.!default { type hw card 0 }
EOF
  fi

else
  log "ENABLE_I2S=0 → skipping I2S audio configuration."
fi

# ---------------------------------------------------------------------------
# USB power-save section (guarded by DISABLE_USB)
# ---------------------------------------------------------------------------
if [[ "$DISABLE_USB" == "1" ]]; then

  sed -i 's/otg_mode=1/otg_mode=0/g' "$CONFIG_TXT"
  
  log "DISABLE_USB=1 → installing/enabling USB unbind service (USB will be disabled)."

  # Unbinding USB bus via sysfs is a known power-saving technique (echo 1-1 > .../unbind). [4](https://blog.himbeer.me/2018/12/27/how-to-connect-a-pcm5102-i2s-dac-to-your-raspberry-pi/)
  install_unit "/etc/systemd/system/usb-unbind.service" \
"[Unit]
Description=Unbind USB bus to save power (disables USB)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo 1-1 > /sys/bus/usb/drivers/usb/unbind || true'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"
  enable_unit "usb-unbind.service"

else
  log "DISABLE_USB=0 → doing nothing"
fi

# ---------------------------------------------------------------------------
# HDMI-off service (guarded by DISABLE_HDMI)
# ---------------------------------------------------------------------------
if [[ "$DISABLE_HDMI" == "1" ]]; then
  log "DISABLE_HDMI=1 → installing/enabling HDMI disable service (HDMI will be disabled)."
  install_unit "/etc/systemd/system/hdmi-off.service" \
  "[Unit]
  Description=Disable HDMI output to save power
  After=multi-user.target

  [Service]
  Type=oneshot
  ExecStart=/bin/sh -c 'if [ -x /opt/vc/bin/tvservice ]; then /opt/vc/bin/tvservice -o; elif command -v tvservice >/dev/null 2>&1; then tvservice -o; fi'
  RemainAfterExit=yes

  [Install]
  WantedBy=multi-user.target
  "
  enable_unit "hdmi-off.service"
else
  log "DISABLE_HDMI=0 → doing nothing"
fi

log "Done."