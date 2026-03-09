# locals.tf - Computed Values
#
# Computed from input variables; used throughout the configuration to keep things DRY.
# Separate network_config locals for each container since they have distinct IPs.

locals {
  # Read SSH public key from file
  ssh_key = file(pathexpand(var.ssh_public_key_file))

  # Shared VLAN tag (null if 0, so bpg/proxmox omits it entirely)
  vlan_tag = var.vlan_tag > 0 ? var.vlan_tag : null

  # NPM network configuration
  npm_network_config = {
    ipv4     = var.npm_ip
    gateway  = var.npm_gateway
    bridge   = var.network_bridge
    vlan_tag = local.vlan_tag
  }

  # Authelia network configuration
  authelia_network_config = {
    ipv4     = var.authelia_ip
    gateway  = var.authelia_gateway
    bridge   = var.network_bridge
    vlan_tag = local.vlan_tag
  }

  # Umami network configuration — VLAN 50 (Lab Services), not the shared DMZ VLAN 60
  umami_vlan_tag = var.umami_vlan_tag > 0 ? var.umami_vlan_tag : null

  umami_network_config = {
    ipv4     = var.umami_ip
    gateway  = var.umami_gateway
    bridge   = var.network_bridge
    vlan_tag = local.umami_vlan_tag
  }

  # Tags — combined per-container tags with automatic project tags
  npm_tags = concat(
    ["npm", "proxy", "ariadne"],
    ["terraform-managed", "homelab-command"]
  )

  authelia_tags = concat(
    ["authelia", "auth", "sso", "ariadne"],
    ["terraform-managed", "homelab-command"]
  )

  umami_tags = concat(
    ["umami", "analytics", "ariadne"],
    ["terraform-managed", "homelab-command"]
  )
}
