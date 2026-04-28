# variables.tf - Input Variables for inbox-receiver LXC

# =============================================================================
# PROXMOX CONNECTION SETTINGS
# =============================================================================

variable "proxmox_endpoint" {
  description = "The base URL of the Proxmox cluster (e.g., https://10.0.10.2:8006/)"
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
  description = "Skip TLS certificate verification (true for self-signed certs)"
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "Proxmox node name"
  type        = string
  default     = "puppetmaster"
}

# =============================================================================
# CONTAINER SETTINGS
# =============================================================================

variable "container_vmid" {
  description = "Proxmox VM/Container ID"
  type        = number
  default     = 103

  validation {
    condition     = var.container_vmid >= 100 && var.container_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "container_hostname" {
  description = "Hostname inside the container"
  type        = string
  default     = "inbox-receiver"
}

variable "container_cpu_cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 1
}

variable "container_memory_mb" {
  description = "Memory in megabytes"
  type        = number
  default     = 512
}

variable "container_disk_gb" {
  description = "Disk size in gigabytes"
  type        = number
  default     = 8
}

variable "container_storage" {
  description = "Proxmox storage name for root filesystem"
  type        = string
  default     = "local-lvm"
}

variable "lxc_template" {
  description = "LXC template"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
}

# =============================================================================
# NETWORK SETTINGS
# =============================================================================

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr1"
}

variable "container_ip" {
  description = "Static IP address in CIDR notation"
  type        = string
  default     = "10.0.50.19/24"
}

variable "container_gateway" {
  description = "Gateway IP"
  type        = string
  default     = "10.0.50.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the container network interface"
  type        = number
  default     = 50
}

variable "ssh_public_key_file" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "tags" {
  description = "Tags to apply to the container"
  type        = list(string)
  default     = ["inbox-receiver", "mnemosyne", "interim"]
}
