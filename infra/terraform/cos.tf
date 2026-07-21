##############################################################################
# infra/terraform/cos.tf
# IBM Cloud Object Storage instance and buckets.
##############################################################################

resource "ibm_resource_instance" "cos" {
  name              = "${var.prefix}-cos"
  resource_group_id = ibm_resource_group.rg.id
  service           = "cloud-object-storage"
  plan              = var.cos_plan
  location          = "global"
  tags              = local.tags
}

resource "ibm_cos_bucket" "artefacts" {
  bucket_name          = "${var.prefix}-artefacts"
  resource_instance_id = ibm_resource_instance.cos.id
  region_location      = var.region
  storage_class        = "standard"

  noncurrent_version_expiration {
    noncurrent_days = 90
  }
}

resource "ibm_cos_bucket" "data" {
  bucket_name          = "${var.prefix}-data"
  resource_instance_id = ibm_resource_instance.cos.id
  region_location      = var.region
  storage_class        = "standard"
}
