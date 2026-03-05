# outputs.tf - Terraform Output Values

output "container_vmid" {
  description = "Proxmox VM/Container ID"
  value       = proxmox_virtual_environment_container.minio.vm_id
}

output "container_hostname" {
  description = "Hostname assigned to the container"
  value       = proxmox_virtual_environment_container.minio.initialization[0].hostname
}

output "container_node" {
  description = "Physical Proxmox node running this container"
  value       = proxmox_virtual_environment_container.minio.node_name
}

output "container_network_config" {
  description = "Network configuration for reference"
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

output "next_steps" {
  description = "Next steps after container creation"
  value       = <<-EOT

    ============================================================
    MinIO container created successfully!
    ============================================================

    Next steps:

    1. Wait 30-60 seconds for the container to start up.

    2. Verify SSH access:
       ssh root@${local.network_config.ipv4 != null ? local.network_config.ipv4 : "<CONTAINER_IP>"}

    3. Create vault file with MinIO credentials:
       cp ansible/group_vars/vault.yml.example ansible/group_vars/vault.yml
       ansible-vault encrypt ansible/group_vars/vault.yml

    4. Run Ansible provisioning:
       cd ../ansible
       ansible-playbook -i inventory.ini provision.yml --ask-vault-pass

    5. Access the MinIO console:
       http://${local.network_config.ipv4 != null ? split("/", local.network_config.ipv4)[0] : "<CONTAINER_IP>"}:9001

    6. Access the MinIO API:
       http://${local.network_config.ipv4 != null ? split("/", local.network_config.ipv4)[0] : "<CONTAINER_IP>"}:9000

    ============================================================
    EOT
}
