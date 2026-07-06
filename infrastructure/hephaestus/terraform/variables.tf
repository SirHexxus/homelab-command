# variables.tf - Input Variables for Hephaestus Proxmox Configuration
#
# Hephaestus is the shared Docker Compose host VM (VLAN 50). Docker-native
# services (Firecrawl, future Nextcloud/Vaultwarden) run here — never in LXCs.
# Values are provided in terraform.tfvars.

# =============================================================================
# PROXMOX CONNECTION SETTINGS
# =============================================================================

variable "proxmox_endpoint" {
  description = "The base URL of your Proxmox cluster (e.g., https://proxmox.example.com:8006/)"
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
  default     = "hephaestus"
}

variable "vm_vmid" {
  description = "Proxmox VM ID"
  type        = number
  default     = 109

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
  default     = 8192

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
  default     = 80

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
  description = "URL of the Ubuntu cloud image to download onto the Proxmox node"
  type        = string
  default     = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
}

variable "snippets_datastore" {
  description = "Proxmox datastore for cloud-init snippets (must have 'snippets' content enabled)"
  type        = string
  default     = "local"
}

# =============================================================================
# NETWORK SETTINGS
# =============================================================================

variable "network_bridge" {
  description = "Proxmox network bridge to attach the VM to"
  type        = string
  default     = "vmbr1"
}

variable "vm_ip" {
  description = "Static IP address in CIDR notation (e.g., '10.0.50.30/24'). Leave empty for DHCP."
  type        = string
  default     = "10.0.50.30/24"
}

variable "vm_gateway" {
  description = "Gateway IP for static IP configuration."
  type        = string
  default     = "10.0.50.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the VM network interface. Set to 0 to disable VLAN tagging."
  type        = number
  default     = 50

  validation {
    condition     = var.vlan_tag >= 0 && var.vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

variable "vm_user" {
  description = "Cloud-init user account created on the VM (Ubuntu cloud images disable root SSH)"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key_file" {
  description = "Path to SSH public key file for VM access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "tags" {
  description = "Tags to apply to the VM"
  type        = list(string)
  default     = ["hephaestus", "docker"]
}
