# main.tf - Primary Terraform Resource Definitions
#
# This file defines the LXC container resource that will be created in Proxmox.
# The configuration includes:
# - Container with specified CPU, memory, and disk resources
# - Network interface with static IP and VLAN tagging
# - SSH key for passwordless access (used by Ansible)
# - LXC features for GPU compatibility and nested containers

resource "proxmox_virtual_environment_container" "ollama" {
  # Container identification on the Proxmox node
  node_name    = var.proxmox_node
  description  = "Ollama LLM Inference Server"
  unprivileged = !var.enable_privileged_mode
  started = true
  tags    = local.all_tags

  # OS template - Ubuntu 22.04 is chosen for stability and Ollama compatibility
  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  # Initialization: hostname, network IP, and SSH key injection
  initialization {
    hostname     = var.container_hostname
    dns_servers  = ["10.0.50.1", "1.1.1.1", "8.8.8.8"]

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

  # Resource allocation - tune these based on your specific hardware
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

  # nesting: Required for Docker-in-LXC or other container runtimes
  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}
