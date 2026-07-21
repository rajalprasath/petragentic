##############################################################################
# infra/terraform/variables.tf
##############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = ">= 1.63"
    }
  }
}

provider "ibm" {
  ibmcloud_api_key = var.ibmcloud_api_key
  region           = var.region
}

resource "ibm_resource_group" "rg" {
  name = var.resource_group_name
}

locals {
  tags = [
    "project:petragentic",
    "env:production",
    "region:${var.region}",
    "managed-by:terraform",
  ]
}
