##############################################################################
# infra/terraform/watsonx.tf
# watsonx.ai and watsonx.data service instances.
##############################################################################

resource "ibm_resource_instance" "watsonx_ai" {
  name              = "${var.prefix}-watsonx-ai"
  resource_group_id = ibm_resource_group.rg.id
  service           = "pm-20"
  plan              = var.watsonx_plan
  location          = var.region
  tags              = local.tags
}

resource "ibm_resource_instance" "watsonx_data" {
  name              = "${var.prefix}-watsonx-data"
  resource_group_id = ibm_resource_group.rg.id
  service           = "lakehouse"
  plan              = var.wxdata_plan
  location          = var.region
  tags              = local.tags
}

# watsonx.governance is governed by IBM entitlement.
# Uncomment after confirming your plan:
# resource "ibm_resource_instance" "watsonx_gov" {
#   name              = "${var.prefix}-watsonx-gov"
#   resource_group_id = ibm_resource_group.rg.id
#   service           = "aiopenscale"
#   plan              = "standard"
#   location          = var.region
#   tags              = local.tags
# }
