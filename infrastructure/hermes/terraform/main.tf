# main.tf - Primary Terraform Resource Definitions
#
# This file defines the LXC container resource for the Hermes AI agent.

resource "proxmox_virtual_environment_container" "hermes" {
  # Container identification
  vm_id        = var.container_vmid
  node_name    = var.proxmox_node
  description  = "Hermes AI Agent"
  unprivileged = !var.enable_privileged_mode
  started      = true
  tags         = local.all_tags

  # OS template
  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  # Initialization: hostname, network IP, and SSH key injection
  initialization {
    hostname = var.container_hostname

    ip_config {
      ipv4 {
        address = local.network_config.dhcp ? "dhcp" : local.network_config.ipv4
        gateway = local.network_config.dhcp ? null : local.network_config.gateway
      }
    }

    user_account {
      keys = [local.ssh_key]
    }
  }

  # Network interface - bridge and VLAN tag only; IP is handled in initialization
  network_interface {
    name    = "eth0"
    bridge  = local.network_config.bridge
    vlan_id = local.network_config.vlan_tag
  }

  # Resource allocation
  cpu {
    cores = var.container_cpu_cores
  }

  memory {
    dedicated = var.container_memory_mb
    swap      = 512
  }

  # Root filesystem
  disk {
    datastore_id = var.container_storage
    size         = var.container_disk_gb
  }

  # LXC features
  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}
