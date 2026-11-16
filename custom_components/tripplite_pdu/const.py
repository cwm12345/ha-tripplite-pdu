# Written by Claude, guided by Chris.
"""Constants for the Tripp Lite PDU integration.

OIDs below were confirmed by direct SNMP walk against live PDU hardware,
not taken from the MIB file alone. Some units report zero for metering;
this integration doesn't work around that, it reports what the device
reports.
"""

from __future__ import annotations

DOMAIN = "tripplite_pdu"

CONF_AUTH_KEY = "auth_key"

DEFAULT_USERNAME = "homeassistant"
DEFAULT_SCAN_INTERVAL = 30  # seconds

MANUFACTURER = "Tripp Lite"
MODEL = "PDUMH15NET"

# Whole-unit metering. Some units genuinely report zero here (a device
# issue, not a reporting bug).
OID_OUTPUT_CURRENT = "1.3.6.1.4.1.850.1.1.3.2.3.2.1.1.5.1.1"  # hundredths of an amp
OID_OUTPUT_POWER = "1.3.6.1.4.1.850.1.1.3.2.3.2.1.1.8.1.1"  # watts, no scaling

# Outlet table: name/state/command columns share a common row suffix (the
# outlet number, walked as 1..N; 16 on the PDUMH15NET, other models may
# differ, so the coordinator discovers the count live rather than
# hardcoding it).
# State: 1 = off, 2 = on (confirmed via live read-back after toggling,
# matches the payload_on/payload_off values HA's own `snmp` switch
# platform needs for this PDU).
OID_OUTLET_NAME_BASE = "1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.2.1"
OID_OUTLET_STATE_BASE = "1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.4.1"  # read-only status
# Real root cause of a "notWritable" outlet-control bug found shortly after
# first release: writes must target a SEPARATE "command" column (6), not
# the status column (4) reads use. An earlier version of this integration
# wrote to OID_OUTLET_STATE_BASE for both reads and writes, which is
# read-only on this hardware -- every write failed, regardless of outlet
# or PDU, until this was split out.
OID_OUTLET_COMMAND_BASE = "1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.6.1"  # write target
OUTLET_STATE_ON = 2
OUTLET_STATE_OFF = 1
