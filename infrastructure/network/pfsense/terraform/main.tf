# main.tf - pfSense Firewall VM
#
# Provisions the pfSense VM on puppetmaster (10.0.10.2).
# This is RECOVERY IaC — pfSense is already running. Apply only during a
# full Proxmox rebuild. After apply, restore config.xml via pfSense UI.
#
# VM spec confirmed from: qm config 200 on puppetmaster (2026-03-10)
# Recovery sequence: run this FIRST (Phase 0a) — network is down during apply.

resource "proxmox_virtual_environment_vm" "pfsense" {
  vm_id       = var.pfsense_vmid
  node_name   = var.proxmox_node
  name        = local.pfsense_name
  description = local.pfsense_description
  started     = true
  on_boot     = true

  # pfSense must start first — VLANs and routing must be up before other VMs
  startup {
    order    = 1
    up_delay = 60
  }

  operating_system {
    # l26 = Linux 2.6+ kernel — correct for pfSense (FreeBSD kernel, but l26 is standard for
    # custom OS types in Proxmox when no specific BSD type is required)
    type = "l26"
  }

  cpu {
    cores = var.pfsense_cpu_cores
    type  = var.pfsense_cpu_type
  }

  memory {
    dedicated = var.pfsense_memory_mb
    floating  = var.pfsense_balloon_mb
  }

  # Root disk — scsi0 on local-lvm (SSD-backed)
  disk {
    datastore_id = var.pfsense_disk_storage
    size         = var.pfsense_disk_gb
    interface    = "scsi0"
    file_format  = "raw"
  }

  scsi_hardware = var.pfsense_scsi_hw

  # Installer ISO — stays mounted (not ejected) so it's available for recovery
  cdrom {
    enabled   = true
    file_id   = var.pfsense_iso
    interface = "ide2"
  }

  # net0 — WAN NIC (vmbr0, no VLAN tag — untagged WAN uplink)
  network_device {
    bridge = var.pfsense_wan_bridge
    model  = "virtio"
  }

  # net1 — LAN trunk NIC (vmbr1, VLAN-aware — pfSense manages all VLAN subinterfaces)
  network_device {
    bridge = var.pfsense_lan_bridge
    model  = "virtio"
  }

  lifecycle {
    # Prevent Terraform from replacing the VM if boot order or description changes
    ignore_changes = [started]
  }
}
