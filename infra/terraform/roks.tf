##############################################################################
# infra/terraform/roks.tf
# Red Hat OpenShift on IBM Cloud (ROKS) cluster + Container Registry namespace.
##############################################################################

resource "ibm_container_vpc_cluster" "roks" {
  name              = "${var.prefix}-roks"
  vpc_id            = ibm_is_vpc.main.id
  flavor            = var.roks_flavor
  kube_version      = var.roks_version
  worker_count      = var.roks_worker_count
  resource_group_id = ibm_resource_group.rg.id
  tags              = local.tags

  disable_public_service_endpoint = false  # set true after VPN confirmed working

  zones {
    subnet_id = ibm_is_subnet.private.id
    name      = var.vpc_zone
  }

  timeouts {
    create = "90m"
    update = "60m"
    delete = "45m"
  }
}

resource "ibm_cr_namespace" "petragentic" {
  name              = var.icr_namespace
  resource_group_id = ibm_resource_group.rg.id
}
