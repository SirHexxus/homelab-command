# variables.tf - Input Variables for the Recon detonation box
#
# Recon is a full VM (NOT an LXC) on the Sandbox/quarantine VLAN (66). It runs a
# CLONE of a compromised WordPress site for security review, so it is deliberately
# a hardware-isolated VM rather than the repo's usual unprivileged LXC. Values are
# provided in terraform.tfvars.

# =============================================================================
# PROXMOX CONNECTION SETTINGS
# =============================================================================

variable "proxmox_endpoint" {
  description = "The base URL of your Proxmox cluster (e.g., https://10.0.10.2:8006/)"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID in format 'username@pam!tokenname'"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS certificate verification. Set to true for self-signed certificates."
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "The name of the Proxmox node where the VM will be created"
  type        = string
  default     = "puppetmaster"
}

variable "proxmox_ssh_private_key_file" {
  description = "SSH private key for root on the Proxmox node (snippet uploads). puppetmaster only accepts id_ed25519."
  type        = string
  default     = "~/.ssh/id_ed25519"
}

# =============================================================================
# VM SETTINGS
# =============================================================================

variable "vm_hostname" {
  description = "Hostname of the VM"
  type        = string
  default     = "recon"
}

variable "vm_vmid" {
  description = "Proxmox VM ID. 6601 encodes 'VLAN 66, not a normal VM'."
  type        = number
  default     = 6601

  validation {
    condition     = var.vm_vmid >= 100 && var.vm_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "vm_cpu_cores" {
  description = "Number of CPU cores to allocate"
  type        = number
  default     = 4

  validation {
    condition     = var.vm_cpu_cores > 0 && var.vm_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "vm_cpu_type" {
  description = "CPU type for the VM (host = pass-through host CPU flags)"
  type        = string
  default     = "host"
}

variable "vm_memory_mb" {
  description = "Dedicated memory in megabytes"
  type        = number
  default     = 6144

  validation {
    condition     = var.vm_memory_mb >= 1024
    error_message = "Memory must be at least 1GB (1024 MB)."
  }
}

variable "vm_balloon_mb" {
  description = "Balloon (minimum/floating) memory in MB"
  type        = number
  default     = 4096
}

variable "vm_disk_gb" {
  description = "Root disk size in gigabytes"
  type        = number
  default     = 40

  validation {
    condition     = var.vm_disk_gb >= 10
    error_message = "Disk size must be at least 10GB."
  }
}

variable "vm_disk_storage" {
  description = "Proxmox storage pool for the VM root disk"
  type        = string
  default     = "local-lvm"
}

variable "vm_scsi_hw" {
  description = "SCSI controller hardware type"
  type        = string
  default     = "virtio-scsi-pci"
}

variable "cloud_image_url" {
  description = "URL of the Debian 12 cloud image to download onto the Proxmox node"
  type        = string
  default     = "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
}

variable "cloud_image_file_name" {
  description = "Local file name for the downloaded cloud image. Must end in .img/.iso for Proxmox's 'iso' content type; Debian ships .qcow2, so we store it as .img (qemu auto-detects the real qcow2 format on disk import)."
  type        = string
  default     = "debian-12-genericcloud-amd64.img"
}

variable "snippets_datastore" {
  description = "Proxmox datastore for cloud-init snippets (must have 'snippets' content enabled)"
  type        = string
  default     = "local"
}

# =============================================================================
# NETWORK SETTINGS  (Sandbox / quarantine VLAN 66)
# =============================================================================

variable "network_bridge" {
  description = "Proxmox network bridge to attach the VM to"
  type        = string
  default     = "vmbr1"
}

variable "vm_ip" {
  description = "Static IP address in CIDR notation. Leave empty for DHCP."
  type        = string
  default     = "10.0.66.10/24"
}

variable "vm_gateway" {
  description = "Gateway IP for static IP configuration."
  type        = string
  default     = "10.0.66.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the VM network interface. Set to 0 to disable VLAN tagging."
  type        = number
  default     = 66

  validation {
    condition     = var.vlan_tag >= 0 && var.vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

variable "dns_servers" {
  description = "DNS resolvers for the VM (needed during the provisioning egress window; VLAN 66 has no local resolver reachable under lockdown)."
  type        = list(string)
  default     = ["1.1.1.1", "8.8.8.8"]
}

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

variable "vm_user" {
  description = "Cloud-init user account created on the VM (Debian cloud images disable root SSH)"
  type        = string
  default     = "debian"
}

variable "ssh_public_key_file" {
  description = "Path to SSH public key file for VM access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "tags" {
  description = "Tags to apply to the VM"
  type        = list(string)
  default     = ["recon", "sandbox", "security", "quarantine"]
}
