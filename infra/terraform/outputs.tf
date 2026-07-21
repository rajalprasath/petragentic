##############################################################################
# infra/terraform/outputs.tf
# All values needed by GitHub Actions, seed runner, and agents.
# Run `terraform output` after apply to retrieve these.
##############################################################################

output "resource_group_id" {
  value = ibm_resource_group.rg.id
}

output "roks_cluster_id" {
  description = "Set as GitHub Actions secret: OCP_CLUSTER_ID"
  value       = ibm_container_vpc_cluster.roks.id
}

output "roks_cluster_name" {
  value = ibm_container_vpc_cluster.roks.name
}

output "icr_namespace" {
  value = ibm_cr_namespace.petragentic.name
}

output "cos_instance_id" {
  description = "Set in Secrets Manager as: COS_INSTANCE_ID"
  value       = ibm_resource_instance.cos.id
}

output "cos_bucket_artefacts" {
  value = ibm_cos_bucket.artefacts.bucket_name
}

output "cos_bucket_data" {
  value = ibm_cos_bucket.data.bucket_name
}

output "cos_private_endpoint" {
  description = "Set in Secrets Manager as: COS_ENDPOINT"
  value       = "https://s3.private.${var.region}.cloud-object-storage.appdomain.cloud"
}

output "secrets_manager_instance_id" {
  description = "Set as GitHub Actions secret: SECRETS_MANAGER_INSTANCE_ID"
  value       = ibm_resource_instance.secrets_manager.guid
}

output "secrets_manager_private_endpoint" {
  description = "Set as GitHub Actions secret: SECRETS_MANAGER_URL"
  value       = "https://${ibm_resource_instance.secrets_manager.guid}.private.${var.region}.secrets-manager.appdomain.cloud"
}

output "secrets_group_id" {
  value = ibm_sm_secret_group.agents.secret_group_id
}

output "github_actions_api_key" {
  description = "Set as GitHub Actions secret: IBMCLOUD_API_KEY"
  value       = ibm_iam_service_api_key.github_actions.apikey
  sensitive   = true
}

output "agent_runtime_api_key" {
  description = "Store in Secrets Manager as: IBM_CLOUD_API_KEY (for agents)"
  value       = ibm_iam_service_api_key.agent_runtime.apikey
  sensitive   = true
}

output "watsonx_ai_private_endpoint" {
  description = "Set in Secrets Manager as: WATSONX_URL"
  value       = "https://private.${var.region}.ml.cloud.ibm.com"
}

output "vpn_gateway_public_ip" {
  description = "Configure this IP on your on-premises VPN device"
  value       = ibm_is_vpn_gateway.main.public_ip_address
}
