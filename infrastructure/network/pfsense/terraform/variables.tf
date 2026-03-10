# variables.tf - Input Variables for pfSense VM
#
# pfSense is the network backbone — WAN/LAN routing, VLANs, firewall.
# This Terraform config defines it as code for recovery scenarios.
# On a fresh Proxmox node, apply this first (before any other VMs),
# then restore config.xml via pfSense UI → Diagnostics → Backup & Restore.
#
# VM spec confirmed from: qm config 200 on puppetmaster (2026-03-10)

# =============================================================================
# PROXMOX CONNECTION SETTINGS
# =============================================================================

variable "proxmox_endpoint" {
  description = "Proxmox API endpoint URL (e.g., https://10.0.10.2:8006/)"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID (format: user@realm!tokenname)"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS certificate verification (true for self-signed certs)"
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "Proxmox node name where the VM will be created"
  type        = string
  default     = "puppetmaster"
}

# =============================================================================
# PFSENSE VM SPEC
# All defaults confirmed from: qm config 200 on puppetmaster (2026-03-10)
# =============================================================================

variable "pfsense_vmid" {
  description = "Proxmox VMID for the pfSense VM"
  type        = number
  default     = 200

  validation {
    condition     = var.pfsense_vmid >= 100 && var.pfsense_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "pfsense_cpu_cores" {
  description = "Number of CPU cores for pfSense"
  type        = number
  default     = 2
}

variable "pfsense_cpu_type" {
  description = "CPU type for pfSense VM (host = pass-through host CPU flags)"
  type        = string
  default     = "host"
}

variable "pfsense_memory_mb" {
  description = "Dedicated memory in MB for pfSense"
  type        = number
  default     = 4096
}

variable "pfsense_balloon_mb" {
  description = "Balloon (minimum/floating) memory in MB for pfSense"
  type        = number
  default     = 2048
}

variable "pfsense_disk_gb" {
  description = "Root disk size in GB (scsi0 on local-lvm)"
  type        = number
  default     = 32
}

variable "pfsense_disk_storage" {
  description = "Proxmox storage pool for the pfSense root disk"
  type        = string
  default     = "local-lvm"
}

variable "pfsense_scsi_hw" {
  description = "SCSI controller hardware type"
  type        = string
  default     = "virtio-scsi-pci"
}

variable "pfsense_wan_bridge" {
  description = "Proxmox bridge for WAN NIC (net0 — eno8303 uplink)"
  type        = string
  default     = "vmbr0"
}

variable "pfsense_lan_bridge" {
  description = "Proxmox bridge for LAN trunk NIC (net1 — eno8403 uplink, VLAN-aware)"
  type        = string
  default     = "vmbr1"
}

variable "pfsense_iso" {
  description = "Path to pfSense installer ISO on the Proxmox node"
  type        = string
  default     = "local:iso/netgate-installer-v1.1.1-RELEASE-amd64.iso"
}
