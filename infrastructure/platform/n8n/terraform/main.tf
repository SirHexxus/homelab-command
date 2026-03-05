# main.tf - Primary Terraform Resource Definitions
#
# Defines the n8n LXC container on VLAN 50 (Lab Services, 10.0.50.x)

resource "proxmox_virtual_environment_container" "n8n" {
  node_name    = var.proxmox_node
  description  = "n8n Workflow Automation Server"
  unprivileged = !var.enable_privileged_mode
  started      = true
  tags         = local.all_tags

  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  initialization {
    hostname    = var.container_hostname

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

  network_interface {
    name    = "eth0"
    bridge  = local.network_config.bridge
    vlan_id = local.network_config.vlan_tag
  }

  cpu {
    cores = var.container_cpu_cores
  }

  memory {
    dedicated = var.container_memory_mb
    swap      = 512
  }

  disk {
    datastore_id = var.container_storage
    size         = var.container_disk_gb
  }

  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}
