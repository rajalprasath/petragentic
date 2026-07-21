##############################################################################
# infra/terraform/secrets.tf
# IBM Secrets Manager instance and secret group.
# Secret VALUES are written by the GitHub Actions deploy pipeline — not here.
##############################################################################

resource "ibm_resource_instance" "secrets_manager" {
  name              = "${var.prefix}-sm"
  resource_group_id = ibm_resource_group.rg.id
  service           = "secrets-manager"
  plan              = var.secrets_manager_plan
  location          = var.region
  tags              = local.tags

  parameters = {
    allowed_network = "private-only"
  }
}

resource "ibm_sm_secret_group" "agents" {
  instance_id = ibm_resource_instance.secrets_manager.guid
  region      = var.region
  name        = "${var.prefix}-agents"
  description = "Credentials for agent1 and agent2 services"
}
