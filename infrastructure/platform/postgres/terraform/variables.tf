# variables.tf - Input Variables for Postgres Terraform Configuration

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
  description = "Skip TLS certificate verification. Set to true only for self-signed certificates in home labs."
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "The name of the Proxmox node where the LXC container will be created"
  type        = string
}

variable "container_name" {
  description = "Name of the LXC container (must be unique on the node)"
  type        = string
  default     = "postgres"
}

variable "container_hostname" {
  description = "Hostname inside the container"
  type        = string
  default     = "postgres-server"
}

variable "container_cpu_cores" {
  description = "Number of CPU cores to allocate to the container"
  type        = number
  default     = 4

  validation {
    condition     = var.container_cpu_cores > 0 && var.container_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "container_memory_mb" {
  description = "Memory to allocate to the container in megabytes (default: 8GB = 8192 MB)"
  type        = number
  default     = 8192

  validation {
    condition     = var.container_memory_mb >= 2048
    error_message = "Memory must be at least 2GB (2048 MB)."
  }
}

variable "container_disk_gb" {
  description = "Disk size to allocate to the container in gigabytes (default: 40GB)"
  type        = number
  default     = 40

  validation {
    condition     = var.container_disk_gb >= 20
    error_message = "Disk size must be at least 20GB."
  }
}

variable "container_storage" {
  description = "Proxmox storage name where the container's root filesystem will be stored"
  type        = string
  default     = "local-lvm"
}

variable "lxc_template" {
  description = "LXC template to use (Ubuntu 22.04)"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
}

variable "network_bridge" {
  description = "Proxmox network bridge to attach the container to"
  type        = string
  default     = "vmbr1"
}

variable "container_ip" {
  description = "IP address to assign to the container (CIDR notation). Leave empty for DHCP."
  type        = string
  default     = "10.0.50.14/24"
}

variable "container_gateway" {
  description = "Gateway IP for the container network."
  type        = string
  default     = "10.0.50.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the container network interface."
  type        = number
  default     = 50

  validation {
    condition     = var.vlan_tag >= 0 && var.vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

variable "ssh_public_key_file" {
  description = "Path to your SSH public key file for container access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "enable_privileged_mode" {
  description = "Run container in privileged mode (not recommended for security)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to the container for organization"
  type        = list(string)
  default     = ["postgres", "database", "mnemosyne"]
}

variable "additional_lxc_features" {
  description = "Additional LXC features to enable."
  type        = list(string)
  default     = []
}
