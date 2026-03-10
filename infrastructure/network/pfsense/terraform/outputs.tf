# outputs.tf - pfSense VM Outputs

output "pfsense_vmid" {
  description = "Proxmox VMID for the pfSense VM"
  value       = proxmox_virtual_environment_vm.pfsense.vm_id
}

output "recovery_instructions" {
  description = "Post-apply steps for pfSense recovery"
  value       = <<-EOT

    ============================================================
    pfSense VM Created (VMID ${var.pfsense_vmid})
    ============================================================

    The VM is running but has no configuration yet.

    Recovery steps:

    1. Open Proxmox console for VM ${var.pfsense_vmid}:
       Proxmox UI → puppetmaster → ${var.pfsense_vmid} (pfsense) → Console

    2. Complete the pfSense installer (select defaults — disk will be scsi0)

    3. After first boot, restore configuration:
       pfSense UI → Diagnostics → Backup & Restore → Restore Backup
       File: infrastructure/network/pfsense/config.xml

    4. pfSense will reboot — VLANs, firewall rules, and DHCP will be restored.

    5. Verify network connectivity from Proxmox host:
       ping 10.0.10.1   # pfSense LAN interface
       ping 10.0.20.1   # VLAN 20 (Personal)
       ping 10.0.50.1   # VLAN 50 (Lab Services)

    ============================================================
    EOT
}
