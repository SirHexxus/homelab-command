# variables.tf - Input Variables for Whisper Proxmox Configuration
#
# These variables allow you to customize the Terraform configuration without
# editing the main resource definitions. Values are provided in terraform.tfvars.

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
  description = "The name of the Proxmox node where the LXC container will be created"
  type        = string
}

# =============================================================================
# CONTAINER SETTINGS
# =============================================================================

variable "container_name" {
  description = "Name of the LXC container"
  type        = string
  default     = "whisper"
}

variable "container_hostname" {
  description = "Hostname inside the container"
  type        = string
  default     = "whisper-server"
}

variable "container_cpu_cores" {
  description = "Number of CPU cores to allocate (Whisper needs fewer than LLMs)"
  type        = number
  default     = 4

  validation {
    condition     = var.container_cpu_cores > 0 && var.container_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "container_memory_mb" {
  description = "Memory in megabytes (8GB is sufficient for Whisper small model)"
  type        = number
  default     = 8192

  validation {
    condition     = var.container_memory_mb >= 2048
    error_message = "Memory must be at least 2GB (2048 MB)."
  }
}

variable "container_disk_gb" {
  description = "Disk size in gigabytes (Whisper models are smaller than LLMs)"
  type        = number
  default     = 20

  validation {
    condition     = var.container_disk_gb >= 10
    error_message = "Disk size must be at least 10GB."
  }
}

variable "container_storage" {
  description = "Proxmox storage name for the container's root filesystem"
  type        = string
  default     = "local-lvm"
}

variable "lxc_template" {
  description = "LXC template to use (Ubuntu 22.04 recommended)"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
}

# =============================================================================
# NETWORK SETTINGS
# =============================================================================

variable "network_bridge" {
  description = "Proxmox network bridge to attach the container to"
  type        = string
  default     = "vmbr1"
}

variable "container_ip" {
  description = "Static IP address in CIDR notation (e.g., '10.0.50.12/24'). Leave empty for DHCP."
  type        = string
  default     = "10.0.50.12/24"
}

variable "container_gateway" {
  description = "Gateway IP for static IP configuration."
  type        = string
  default     = "10.0.50.1"
}

variable "vlan_tag" {
  description = "VLAN tag for the container network interface. Set to 0 to disable VLAN tagging."
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

variable "ssh_public_key_file" {
  description = "Path to SSH public key file for container access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "enable_privileged_mode" {
  description = "Run container in privileged mode (not recommended)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to the container"
  type        = list(string)
  default     = ["whisper", "ai", "stt", "speech-to-text"]
}
