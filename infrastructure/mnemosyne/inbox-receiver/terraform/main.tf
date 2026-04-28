# main.tf - inbox-receiver LXC definition
#
# Minimal one-off LXC for the Mnemosyne interim ingest path.
# Accepts IngestItem payloads from n8n and writes them to wiki/inbox/,
# then pushes to GitHub. No LLM, no agent loop.

resource "proxmox_virtual_environment_container" "inbox_receiver" {
  vm_id        = var.container_vmid
  node_name    = var.proxmox_node
  description  = "Mnemosyne inbox receiver — interim ingest path"
  unprivileged = true
  started      = true
  tags         = local.all_tags

  operating_system {
    template_file_id = var.lxc_template
    type             = "ubuntu"
  }

  initialization {
    hostname = var.container_hostname

    ip_config {
      ipv4 {
        address = local.network_config.ipv4
        gateway = local.network_config.gateway
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
    swap      = 128
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
