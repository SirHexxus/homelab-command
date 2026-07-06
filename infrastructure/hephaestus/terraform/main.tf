# main.tf - Primary Terraform Resource Definitions
#
# This file defines the Hephaestus VM — the shared Docker Compose host.
# Unlike the LXC services, this is a full VM booted from an Ubuntu cloud
# image with cloud-init handling hostname, network, and SSH key injection.

# Ubuntu cloud image, downloaded once onto the Proxmox node and reused as
# the VM's root disk source.
resource "proxmox_virtual_environment_download_file" "ubuntu_cloud_image" {
  content_type = "iso"
  datastore_id = "local"
  node_name    = var.proxmox_node
  url          = var.cloud_image_url
  file_name    = "noble-server-cloudimg-amd64.img"
  overwrite    = false
}

# Cloud-init vendor data: installs qemu-guest-agent on first boot so the
# agent { enabled = true } block below doesn't hang Terraform operations.
# Requires 'snippets' content enabled on the datastore:
#   pvesm set local --content backup,iso,vztmpl,snippets
resource "proxmox_virtual_environment_file" "cloud_init_vendor_data" {
  content_type = "snippets"
  datastore_id = var.snippets_datastore
  node_name    = var.proxmox_node

  source_raw {
    file_name = "hephaestus-vendor-data.yaml"
    data      = <<-EOT
      #cloud-config
      package_update: true
      packages:
        - qemu-guest-agent
      runcmd:
        - systemctl enable --now qemu-guest-agent
    EOT
  }
}

resource "proxmox_virtual_environment_vm" "hephaestus" {
  # VM identification
  vm_id       = var.vm_vmid
  node_name   = var.proxmox_node
  name        = var.vm_hostname
  description = "Hephaestus — shared Docker Compose host (Firecrawl, future Nextcloud/Vaultwarden)"
  started     = true
  on_boot     = true
  tags        = local.all_tags

  operating_system {
    type = "l26"
  }

  agent {
    enabled = true
  }

  cpu {
    cores = var.vm_cpu_cores
    type  = var.vm_cpu_type
  }

  memory {
    dedicated = var.vm_memory_mb
    floating  = var.vm_balloon_mb
  }

  scsi_hardware = var.vm_scsi_hw

  disk {
    datastore_id = var.vm_disk_storage
    file_id      = proxmox_virtual_environment_download_file.ubuntu_cloud_image.id
    interface    = "scsi0"
    size         = var.vm_disk_gb
  }

  network_device {
    bridge  = local.network_config.bridge
    model   = "virtio"
    vlan_id = local.network_config.vlan_tag
  }

  # Cloud images route console output to the serial port
  serial_device {}

  # Initialization: hostname, network IP, and SSH key injection via cloud-init
  initialization {
    datastore_id = var.vm_disk_storage

    ip_config {
      ipv4 {
        address = local.network_config.dhcp ? "dhcp" : local.network_config.ipv4
        gateway = local.network_config.dhcp ? null : local.network_config.gateway
      }
    }

    user_account {
      username = var.vm_user
      keys     = [local.ssh_key]
    }

    vendor_data_file_id = proxmox_virtual_environment_file.cloud_init_vendor_data.id
  }

  lifecycle {
    ignore_changes = [initialization[0].user_account[0].keys]
  }
}
