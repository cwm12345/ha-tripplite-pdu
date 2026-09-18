# Written by Claude, guided by Chris.
"""Constants for the Tripp Lite PDU integration.

OIDs below were confirmed by direct SNMP walk against the live PDU-MEC
hardware on 2026-09-17/18 -- not taken from the MIB file alone, not
guessed. See Home Automation/roadmap.md, goal 3a, for the full diagnostic
history (including the 3-of-4-units metering-zero bug this integration
does NOT attempt to work around -- it reports what the device reports).
"""
from __future__ import annotations

DOMAIN = "tripplite_pdu"

CONF_AUTH_KEY = "auth_key"

DEFAULT_USERNAME = "homeassistant"
DEFAULT_SCAN_INTERVAL = 30  # seconds

MANUFACTURER = "Tripp Lite"
MODEL = "PDUMH15NET"

# Whole-unit metering -- confirmed working on MEC, confirmed genuinely zero
# (not a reporting bug) on REC/Living/Master pending Tripp Lite support case
# [case number removed].
OID_OUTPUT_CURRENT = "1.3.6.1.4.1.850.1.1.3.2.3.2.1.1.5.1.1"  # hundredths of an amp
OID_OUTPUT_POWER = "1.3.6.1.4.1.850.1.1.3.2.3.2.1.1.8.1.1"  # watts, no scaling

# Outlet table: name/state columns share a common row suffix (the outlet
# number, walked as 1..N on MEC -- 16 outlets there, other PDUs may differ,
# so the coordinator discovers the count live rather than hardcoding it).
# State: 1 = off, 2 = on (confirmed via live read-back after toggling,
# matches the existing switch: platform: snmp payload_on/payload_off values
# already in use in configuration.yaml).
OID_OUTLET_NAME_BASE = "1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.2.1"
OID_OUTLET_STATE_BASE = "1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.4.1"
OUTLET_STATE_ON = 2
OUTLET_STATE_OFF = 1
