# locals.tf - Local Values and Computed Constants

locals {
  container_id = replace(var.container_name, "-", "")

  ssh_key = file(pathexpand(var.ssh_public_key_file))

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

  all_tags = concat(
    var.tags,
    ["terraform-managed"]
  )
}
