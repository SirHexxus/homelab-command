# outputs.tf - Terraform Output Values
#
# These outputs display important information after container creation.

output "container_vmid" {
  description = "Proxmox VM/Container ID"
  value       = proxmox_virtual_environment_container.hermes.vm_id
}

output "container_hostname" {
  description = "Hostname assigned to the container"
  value       = proxmox_virtual_environment_container.hermes.initialization[0].hostname
}

output "container_node" {
  description = "Proxmox node running this container"
  value       = proxmox_virtual_environment_container.hermes.node_name
}

output "container_network_config" {
  description = "Network configuration"
  value = {
    bridge     = local.network_config.bridge
    using_dhcp = local.network_config.dhcp
    static_ip  = local.network_config.ipv4
    gateway    = local.network_config.gateway
  }
}

output "ssh_key_path" {
  description = "SSH public key used for container access"
  value       = var.ssh_public_key_file
}

output "deployment_instructions" {
  description = "Next steps after container creation"
  value       = <<-EOT

    ============================================================
    Hermes Container Created Successfully!
    ============================================================

    Next steps:

    1. Wait 30-60 seconds for the container to boot

    2. Static IP assigned: ${local.network_config.ipv4 != null ? local.network_config.ipv4 : "N/A (using DHCP)"}

    3. Verify SSH access:
       ssh root@10.0.50.17

    4. Run Ansible provisioning:
       cd infrastructure/hermes/ansible/
       ansible-playbook -i inventory.ini provision.yml

    5. Verify Hermes is running:
       curl http://10.0.50.17:8765/health

    ============================================================
    EOT
}
