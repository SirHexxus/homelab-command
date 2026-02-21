# locals.tf - Computed Values
#
# These local values are computed from input variables and used throughout
# the configuration to keep the code DRY.

locals {
  # Read SSH public key from file
  ssh_key = file(pathexpand(var.ssh_public_key_file))

  # Network configuration: DHCP vs static IP
  network_config = var.container_ip != "" ? {
    dhcp     = false
    ipv4     = var.container_ip
    gateway  = var.container_gateway
    bridge   = var.network_bridge
    vlan_tag = var.vlan_tag > 0 ? var.vlan_tag : null
  } : {
    dhcp     = true
    ipv4     = null
    gateway  = null
    bridge   = var.network_bridge
    vlan_tag = var.vlan_tag > 0 ? var.vlan_tag : null
  }

  # Combined tags including automatic ones
  all_tags = concat(
    var.tags,
    ["terraform-managed", "whisper-inference"]
  )
}
