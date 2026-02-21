# locals.tf - Local Values and Computed Constants
#
# This file defines values that are computed from variables and used throughout
# the configuration. These aren't input variables (those go in variables.tf),
# but rather values derived from them. This helps keep the configuration DRY
# (Don't Repeat Yourself) and makes it easier to maintain.

locals {
  # Container identification
  container_id = replace(var.container_name, "-", "")
  
  # Safely handle SSH key path expansion
  ssh_key = file(pathexpand(var.ssh_public_key_file))
  
  # Network configuration for DHCP or static IP
  # If container_ip is empty, use DHCP; otherwise use static configuration
  network_config = var.container_ip != "" ? {
    dhcp      = false
    ipv4      = var.container_ip
    gateway   = var.container_gateway
    bridge    = var.network_bridge
    vlan_tag  = var.vlan_tag > 0 ? var.vlan_tag : null
  } : {
    dhcp      = true
    ipv4      = null
    gateway   = null
    bridge    = var.network_bridge
    vlan_tag  = var.vlan_tag > 0 ? var.vlan_tag : null
  }
  
  # LXC features list - always include nesting and keyctl for GPU compatibility
  # Nesting: allows nested containers (useful for Docker or LXD)
  # Keyctl: required for GPU device passthrough
  lxc_features = concat(
    ["nesting=1", "keyctl=1"],
    var.additional_lxc_features
  )
  
  # Resource limits formatted for LXC
  limits = {
    cpu    = "cpuset=${var.container_cpu_cores}"
    memory = "${var.container_memory_mb}"
    disk   = "${var.container_disk_gb}G"
  }
  
  # Common tags applied to all resources
  all_tags = concat(
    var.tags,
    ["terraform-managed", "ollama-inference"]
  )
}
