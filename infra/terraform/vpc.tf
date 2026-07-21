##############################################################################
# infra/terraform/vpc.tf
# VPC, subnets, security groups, and VPE gateways for private IBM Cloud access.
##############################################################################

resource "ibm_is_vpc" "main" {
  name                      = "${var.prefix}-vpc"
  resource_group            = ibm_resource_group.rg.id
  address_prefix_management = "manual"
  tags                      = local.tags
}

resource "ibm_is_vpc_address_prefix" "private" {
  name = "${var.prefix}-prefix"
  vpc  = ibm_is_vpc.main.id
  zone = var.vpc_zone
  cidr = var.vpc_cidr
}

resource "ibm_is_subnet" "private" {
  name            = "${var.prefix}-private"
  vpc             = ibm_is_vpc.main.id
  zone            = var.vpc_zone
  ipv4_cidr_block = var.vpc_cidr
  resource_group  = ibm_resource_group.rg.id
  depends_on      = [ibm_is_vpc_address_prefix.private]
}

# ── Security group: ROKS worker nodes ────────────────────────────────────────

resource "ibm_is_security_group" "workers" {
  name           = "${var.prefix}-workers-sg"
  vpc            = ibm_is_vpc.main.id
  resource_group = ibm_resource_group.rg.id
}

resource "ibm_is_security_group_rule" "workers_egress_all" {
  group     = ibm_is_security_group.workers.id
  direction = "outbound"
  remote    = "0.0.0.0/0"
}

resource "ibm_is_security_group_rule" "workers_ingress_vpc" {
  group     = ibm_is_security_group.workers.id
  direction = "inbound"
  remote    = var.vpc_cidr
}

# WinRM from on-prem Windows subnet via VPN
resource "ibm_is_security_group_rule" "workers_ingress_winrm" {
  group     = ibm_is_security_group.workers.id
  direction = "inbound"
  remote    = var.on_prem_windows_subnet
  tcp {
    port_min = 5985
    port_max = 5986
  }
}

# ── VPE: IBM COS ──────────────────────────────────────────────────────────────

resource "ibm_is_subnet_reserved_ip" "cos_vpe" {
  subnet = ibm_is_subnet.private.id
  name   = "${var.prefix}-cos-vpe-ip"
}

resource "ibm_is_virtual_endpoint_gateway" "cos" {
  name           = "${var.prefix}-cos-vpe"
  vpc            = ibm_is_vpc.main.id
  resource_group = ibm_resource_group.rg.id
  tags           = local.tags
  target {
    resource_type = "provider_cloud_service"
    name          = "ibm-cloud-object-storage"
  }
}

resource "ibm_is_virtual_endpoint_gateway_ip" "cos" {
  gateway     = ibm_is_virtual_endpoint_gateway.cos.id
  reserved_ip = ibm_is_subnet_reserved_ip.cos_vpe.reserved_ip
}

# ── VPE: IBM Secrets Manager ──────────────────────────────────────────────────

resource "ibm_is_subnet_reserved_ip" "sm_vpe" {
  subnet = ibm_is_subnet.private.id
  name   = "${var.prefix}-sm-vpe-ip"
}

resource "ibm_is_virtual_endpoint_gateway" "secrets_manager" {
  name           = "${var.prefix}-sm-vpe"
  vpc            = ibm_is_vpc.main.id
  resource_group = ibm_resource_group.rg.id
  tags           = local.tags
  target {
    resource_type = "provider_cloud_service"
    name          = "secrets-manager"
  }
}

resource "ibm_is_virtual_endpoint_gateway_ip" "secrets_manager" {
  gateway     = ibm_is_virtual_endpoint_gateway.secrets_manager.id
  reserved_ip = ibm_is_subnet_reserved_ip.sm_vpe.reserved_ip
}
