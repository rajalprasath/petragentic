##############################################################################
# infra/terraform/iam.tf
# Service IDs and IAM policies — least privilege for GitHub Actions and agents.
##############################################################################

# ── GitHub Actions service ID ─────────────────────────────────────────────────

resource "ibm_iam_service_id" "github_actions" {
  name        = "${var.prefix}-github-actions"
  description = "Used by GitHub Actions to push images to ICR and deploy to ROKS"
}

resource "ibm_iam_service_api_key" "github_actions" {
  name           = "${var.prefix}-github-actions-key"
  iam_service_id = ibm_iam_service_id.github_actions.iam_id
  description    = "Stored as GitHub Actions secret IBMCLOUD_API_KEY"
}

resource "ibm_iam_service_policy" "github_icr" {
  iam_service_id = ibm_iam_service_id.github_actions.id
  roles          = ["Manager", "Writer"]
  resources {
    service = "container-registry"
  }
}

resource "ibm_iam_service_policy" "github_roks" {
  iam_service_id = ibm_iam_service_id.github_actions.id
  roles          = ["Administrator", "Manager"]
  resources {
    service           = "containers-kubernetes"
    resource_group_id = ibm_resource_group.rg.id
  }
}

resource "ibm_iam_service_policy" "github_secrets" {
  iam_service_id = ibm_iam_service_id.github_actions.id
  roles          = ["SecretsReader"]
  resources {
    service              = "secrets-manager"
    resource_instance_id = ibm_resource_instance.secrets_manager.guid
  }
}

# ── Agent runtime service ID ──────────────────────────────────────────────────

resource "ibm_iam_service_id" "agent_runtime" {
  name        = "${var.prefix}-agent-runtime"
  description = "Runtime identity for agent1 and agent2 pods in ROKS"
}

resource "ibm_iam_service_api_key" "agent_runtime" {
  name           = "${var.prefix}-agent-runtime-key"
  iam_service_id = ibm_iam_service_id.agent_runtime.iam_id
  description    = "Stored in Secrets Manager; injected into pods as IBM_CLOUD_API_KEY"
}

resource "ibm_iam_service_policy" "agent_cos" {
  iam_service_id = ibm_iam_service_id.agent_runtime.id
  roles          = ["Writer", "Reader"]
  resources {
    service              = "cloud-object-storage"
    resource_instance_id = ibm_resource_instance.cos.guid
  }
}

resource "ibm_iam_service_policy" "agent_secrets" {
  iam_service_id = ibm_iam_service_id.agent_runtime.id
  roles          = ["SecretsReader"]
  resources {
    service              = "secrets-manager"
    resource_instance_id = ibm_resource_instance.secrets_manager.guid
  }
}

resource "ibm_iam_service_policy" "agent_watsonx" {
  iam_service_id = ibm_iam_service_id.agent_runtime.id
  roles          = ["Viewer"]
  resources {
    service = "pm-20"
  }
}
