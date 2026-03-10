# locals.tf - Computed locals for pfSense VM
#
# pfSense is not an LXC — no cloud-init, no SSH key injection,
# no IP assignment via Terraform. All network config comes from config.xml restore.

locals {
  pfsense_name        = "pfsense"
  pfsense_description = "pfSense firewall — WAN/LAN routing, VLANs 10/20/30/40/50/60/66/70, firewall rules"
}
