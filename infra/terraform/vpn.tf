##############################################################################
# infra/terraform/vpn.tf
# VPN Gateway — IBM Cloud VPC to on-premises Windows server subnet.
# Agent 2 reaches Windows servers via WinRM over this tunnel.
#
# Before applying: set on_prem_vpn_peer_ip, on_prem_vpn_psk, on_prem_windows_subnet
##############################################################################

resource "ibm_is_ike_policy" "main" {
  name                     = "${var.prefix}-ike"
  authentication_algorithm = "sha256"
  encryption_algorithm     = "aes256"
  dh_group                 = 19
  ike_version              = 2
  resource_group           = ibm_resource_group.rg.id
}

resource "ibm_is_ipsec_policy" "main" {
  name                     = "${var.prefix}-ipsec"
  authentication_algorithm = "sha256"
  encryption_algorithm     = "aes256"
  pfs                      = "group_19"
  resource_group           = ibm_resource_group.rg.id
}

resource "ibm_is_vpn_gateway" "main" {
  name           = "${var.prefix}-vpn"
  subnet         = ibm_is_subnet.private.id
  resource_group = ibm_resource_group.rg.id
  mode           = "route"
  tags           = local.tags
}

resource "ibm_is_vpn_gateway_connection" "on_prem" {
  count          = var.on_prem_vpn_peer_ip != "" ? 1 : 0
  name           = "${var.prefix}-vpn-onprem"
  vpn_gateway    = ibm_is_vpn_gateway.main.id
  peer_address   = var.on_prem_vpn_peer_ip
  preshared_key  = var.on_prem_vpn_psk
  ike_policy     = ibm_is_ike_policy.main.id
  ipsec_policy   = ibm_is_ipsec_policy.main.id
  local_cidrs    = [var.vpc_cidr]
  peer_cidrs     = [var.on_prem_windows_subnet]

  dead_peer_detection {
    action   = "restart"
    interval = 2
    timeout  = 10
  }
}
