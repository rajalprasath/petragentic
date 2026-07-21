##############################################################################
# infra/terraform/variables.tf
# All configurable inputs. Sensitive values via -var-file or TF_VAR_* env vars.
##############################################################################

variable "ibmcloud_api_key" {
  description = "IBM Cloud API key for the Terraform IBM provider"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "IBM Cloud region"
  type        = string
  default     = "us-south"
}

variable "resource_group_name" {
  type    = string
  default = "petragentic-prod"
}

variable "prefix" {
  type    = string
  default = "petragentic"
}

variable "vpc_cidr" {
  type    = string
  default = "10.240.0.0/24"
}

variable "vpc_zone" {
  type    = string
  default = "us-south-1"
}

variable "on_prem_vpn_peer_ip" {
  description = "Public IP of the on-premises VPN device"
  type        = string
  default     = ""
}

variable "on_prem_vpn_psk" {
  description = "VPN pre-shared key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "on_prem_windows_subnet" {
  description = "CIDR of the on-prem Windows server subnet"
  type        = string
  default     = "192.168.10.0/24"
}

variable "roks_version" {
  type    = string
  default = "4.14_openshift"
}

variable "roks_flavor" {
  description = "Worker node machine type"
  type        = string
  default     = "bx2.4x16"
}

variable "roks_worker_count" {
  type    = number
  default = 3
}

variable "cos_plan" {
  type    = string
  default = "standard"
}

variable "secrets_manager_plan" {
  type    = string
  default = "standard"
}

variable "watsonx_plan" {
  type    = string
  default = "v2-standard"
}

variable "wxdata_plan" {
  type    = string
  default = "lakehouse-enterprise"
}

variable "icr_namespace" {
  type    = string
  default = "petragentic"
}
