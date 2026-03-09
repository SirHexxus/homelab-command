# main.tf - Ariadne DMZ Containers
#
# Provisions three LXC containers:
#   npm      (10.0.60.10, VLAN 60) — NGINX Proxy Manager: SSL termination, subdomain routing
#   authelia (10.0.60.11, VLAN 60) — Authelia: SSO, MFA, forward auth for NPM-protected services
#   umami    (10.0.50.18, VLAN 50) — Umami: privacy-first web analytics; shares Postgres on 10.0.50.14
#
# After apply, run Ansible provisioning from infrastructure/ariadne/ansible/ to
# install and configure the services. See Ariadne Design Doc §13 for full order.

# -----------------------------------------------------------------------------
# NGINX Proxy Manager
# -----------------------------------------------------------------------------

resource "proxmox_virtual_environment_container" "npm" {
  vm_id        = var.npm_vmid
  node_name    = var.proxmox_node
  description  = "NGINX Proxy Manager — reverse proxy, SSL termination, subdomain routing"
  unprivileged = true
  started      = true
  tags         = local.npm_tags

  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  initialization {
    hostname    = var.npm_hostname

    ip_config {
      ipv4 {
        address = local.npm_network_config.ipv4
        gateway = local.npm_network_config.gateway
      }
    }

    user_account {
      keys = [local.ssh_key]
    }
  }

  network_interface {
    name    = "eth0"
    bridge  = local.npm_network_config.bridge
    vlan_id = local.npm_network_config.vlan_tag
  }

  cpu {
    cores = var.npm_cpu_cores
  }

  memory {
    dedicated = var.npm_memory_mb
    swap      = 256
  }

  disk {
    datastore_id = var.container_storage
    size         = var.npm_disk_gb
  }

  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}

# -----------------------------------------------------------------------------
# Authelia
# -----------------------------------------------------------------------------


resource "proxmox_virtual_environment_container" "authelia" {
  vm_id        = var.authelia_vmid
  node_name    = var.proxmox_node
  description  = "Authelia — SSO, MFA, forward auth integration with NPM"
  unprivileged = true
  started      = true
  tags         = local.authelia_tags

  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  initialization {
    hostname    = var.authelia_hostname

    ip_config {
      ipv4 {
        address = local.authelia_network_config.ipv4
        gateway = local.authelia_network_config.gateway
      }
    }

    user_account {
      keys = [local.ssh_key]
    }
  }

  network_interface {
    name    = "eth0"
    bridge  = local.authelia_network_config.bridge
    vlan_id = local.authelia_network_config.vlan_tag
  }

  cpu {
    cores = var.authelia_cpu_cores
  }

  memory {
    dedicated = var.authelia_memory_mb
    swap      = 256
  }

  disk {
    datastore_id = var.container_storage
    size         = var.authelia_disk_gb
  }

  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}

# -----------------------------------------------------------------------------
# Umami
# -----------------------------------------------------------------------------

resource "proxmox_virtual_environment_container" "umami" {
  vm_id        = var.umami_vmid
  node_name    = var.proxmox_node
  description  = "Umami — privacy-first web analytics; uses shared Postgres on 10.0.50.14"
  unprivileged = true
  started      = true
  tags         = local.umami_tags

  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  initialization {
    hostname = var.umami_hostname

    ip_config {
      ipv4 {
        address = local.umami_network_config.ipv4
        gateway = local.umami_network_config.gateway
      }
    }

    user_account {
      keys = [local.ssh_key]
    }
  }

  network_interface {
    name    = "eth0"
    bridge  = local.umami_network_config.bridge
    vlan_id = local.umami_network_config.vlan_tag
  }

  cpu {
    cores = var.umami_cpu_cores
  }

  memory {
    dedicated = var.umami_memory_mb
    swap      = 256
  }

  disk {
    datastore_id = var.container_storage
    size         = var.umami_disk_gb
  }

  features {
    nesting = true
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}
