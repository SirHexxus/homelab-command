# variables.tf - Input Variables for Ariadne (DMZ) Proxmox Configuration
#
# Covers three containers:
#   NGINX Proxy Manager (10.0.60.10) — VLAN 60 (DMZ)
#   Authelia            (10.0.60.11) — VLAN 60 (DMZ)
#   Umami               (10.0.50.18) — VLAN 50 (Lab Services; shares Postgres)
# All three are deployed atomically via a single apply.

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
  description = "The name of the Proxmox node where the LXC containers will be created"
  type        = string
}

# =============================================================================
# SHARED SETTINGS
# =============================================================================

variable "ssh_public_key_file" {
  description = "Path to SSH public key file for container access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "lxc_template" {
  description = "LXC template to use (Ubuntu 22.04 recommended)"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
}

variable "container_storage" {
  description = "Proxmox storage name for the containers' root filesystems"
  type        = string
  default     = "local-lvm"
}

variable "network_bridge" {
  description = "Proxmox network bridge to attach both containers to"
  type        = string
  default     = "vmbr1"
}

variable "vlan_tag" {
  description = "VLAN tag for DMZ containers (VLAN 60)"
  type        = number
  default     = 60

  validation {
    condition     = var.vlan_tag >= 0 && var.vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

# =============================================================================
# NGINX PROXY MANAGER SETTINGS
# =============================================================================

variable "npm_vmid" {
  description = "Proxmox VM/Container ID for NGINX Proxy Manager"
  type        = number
  default     = 120

  validation {
    condition     = var.npm_vmid >= 100 && var.npm_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "npm_hostname" {
  description = "Hostname inside the NPM container"
  type        = string
  default     = "npm"
}

variable "npm_ip" {
  description = "Static IP address for NPM in CIDR notation (e.g., '10.0.60.10/24')"
  type        = string
  default     = "10.0.60.10/24"
}

variable "npm_gateway" {
  description = "Gateway IP for NPM static IP configuration"
  type        = string
  default     = "10.0.60.1"
}

variable "npm_cpu_cores" {
  description = "Number of CPU cores for NPM"
  type        = number
  default     = 1

  validation {
    condition     = var.npm_cpu_cores > 0 && var.npm_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "npm_memory_mb" {
  description = "Memory in megabytes for NPM"
  type        = number
  default     = 1024

  validation {
    condition     = var.npm_memory_mb >= 512
    error_message = "Memory must be at least 512MB."
  }
}

variable "npm_disk_gb" {
  description = "Disk size in gigabytes for NPM (stores SSL certs, proxy config, logs)"
  type        = number
  default     = 10

  validation {
    condition     = var.npm_disk_gb >= 8
    error_message = "Disk size must be at least 8GB."
  }
}

# =============================================================================
# AUTHELIA SETTINGS
# =============================================================================

variable "authelia_vmid" {
  description = "Proxmox VM/Container ID for Authelia"
  type        = number
  default     = 121

  validation {
    condition     = var.authelia_vmid >= 100 && var.authelia_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "authelia_hostname" {
  description = "Hostname inside the Authelia container"
  type        = string
  default     = "authelia"
}

variable "authelia_ip" {
  description = "Static IP address for Authelia in CIDR notation (e.g., '10.0.60.11/24')"
  type        = string
  default     = "10.0.60.11/24"
}

variable "authelia_gateway" {
  description = "Gateway IP for Authelia static IP configuration"
  type        = string
  default     = "10.0.60.1"
}

variable "authelia_cpu_cores" {
  description = "Number of CPU cores for Authelia"
  type        = number
  default     = 1

  validation {
    condition     = var.authelia_cpu_cores > 0 && var.authelia_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "authelia_memory_mb" {
  description = "Memory in megabytes for Authelia"
  type        = number
  default     = 512

  validation {
    condition     = var.authelia_memory_mb >= 256
    error_message = "Memory must be at least 256MB."
  }
}

variable "authelia_disk_gb" {
  description = "Disk size in gigabytes for Authelia"
  type        = number
  default     = 8

  validation {
    condition     = var.authelia_disk_gb >= 5
    error_message = "Disk size must be at least 5GB."
  }
}

# =============================================================================
# UMAMI SETTINGS
# =============================================================================

variable "umami_vmid" {
  description = "Proxmox VM/Container ID for Umami"
  type        = number
  default     = 122

  validation {
    condition     = var.umami_vmid >= 100 && var.umami_vmid <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "umami_hostname" {
  description = "Hostname inside the Umami container"
  type        = string
  default     = "umami"
}

variable "umami_ip" {
  description = "Static IP address for Umami in CIDR notation (e.g., '10.0.50.18/24')"
  type        = string
  default     = "10.0.50.18/24"
}

variable "umami_gateway" {
  description = "Gateway IP for Umami static IP configuration"
  type        = string
  default     = "10.0.50.1"
}

variable "umami_vlan_tag" {
  description = "VLAN tag for Umami (VLAN 50 — Lab Services; shares Postgres)"
  type        = number
  default     = 50

  validation {
    condition     = var.umami_vlan_tag >= 0 && var.umami_vlan_tag <= 4094
    error_message = "VLAN tag must be between 0 (disabled) and 4094."
  }
}

variable "umami_cpu_cores" {
  description = "Number of CPU cores for Umami"
  type        = number
  default     = 1

  validation {
    condition     = var.umami_cpu_cores > 0 && var.umami_cpu_cores <= 64
    error_message = "CPU cores must be between 1 and 64."
  }
}

variable "umami_memory_mb" {
  description = "Memory in megabytes for Umami"
  type        = number
  default     = 512

  validation {
    condition     = var.umami_memory_mb >= 256
    error_message = "Memory must be at least 256MB."
  }
}

variable "umami_disk_gb" {
  description = "Disk size in gigabytes for Umami"
  type        = number
  default     = 8

  validation {
    condition     = var.umami_disk_gb >= 5
    error_message = "Disk size must be at least 5GB."
  }
}
