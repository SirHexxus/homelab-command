# locals.tf - Computed Values

locals {
  ssh_key = file(pathexpand(var.ssh_public_key_file))

  network_config = {
    dhcp     = false
    ipv4     = var.container_ip
    gateway  = var.container_gateway
    bridge   = var.network_bridge
    vlan_tag = var.vlan_tag
  }

  all_tags = concat(var.tags, ["terraform-managed", "homelab-command"])
}
