########################################
# AI-Shifts-Management — GCP deploy
# Cloud Run + Secret Manager 構成（DB は外部 Supabase を利用）
# 詳細な手順は deploy/DEPLOY.md 参照
########################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

########################################
# Variables
########################################
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-northeast1"
}

variable "image_backend" {
  type = string
}

variable "image_frontend" {
  type = string
}

variable "allowed_google_domain" {
  type    = string
  default = ""
}

variable "llm_provider" {
  type    = string
  default = "none"
}

variable "budget_amount_jpy" {
  description = "月次予算 (JPY) — アラート閾値 50% / 90% / 100% でメール通知"
  type        = number
  default     = 100
}

variable "budget_notification_email" {
  description = "予算アラート通知先メール。空なら通知チャンネルを作らない。"
  type        = string
  default     = ""
}

########################################
# APIs
########################################
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "billingbudgets.googleapis.com",
    "monitoring.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

########################################
# Secret Manager
# NOTE: 値の投入は gcloud secrets versions add で手動実行
########################################
locals {
  secret_names = [
    "secret-key",
    "google-client-id",
    "google-client-secret",
    "anthropic-api-key",
    "openai-api-key",
    "database-url", # Supabase の Postgres 接続 URL を入れる
  ]
}

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = toset(local.secret_names)
  secret_id = each.key
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

########################################
# Cloud Run: backend
########################################
resource "google_cloud_run_v2_service" "backend" {
  name     = "ai-shifts-backend"
  location = var.region

  template {
    containers {
      image = var.image_backend
      ports {
        container_port = 8000
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "FRONTEND_ORIGIN"
        value = google_cloud_run_v2_service.frontend.uri
      }
      env {
        # backend 自身の URI は自己参照(循環)になるため、安定した既知URLを直接指定する。
        name  = "GOOGLE_REDIRECT_URI"
        value = "https://ai-shifts-backend-kc7umdofja-an.a.run.app/api/auth/google/callback"
      }
      env {
        name  = "ALLOWED_GOOGLE_DOMAIN"
        value = var.allowed_google_domain
      }
      env {
        name  = "LLM_PROVIDER"
        value = var.llm_provider
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "database-url"
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "secret-key"
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "google-client-id"
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "google-client-secret"
            version = "latest"
          }
        }
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "anthropic-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "openai-api-key"
            version = "latest"
          }
        }
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
  depends_on = [google_secret_manager_secret.app_secrets]
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

########################################
# Cloud Run: frontend
########################################
resource "google_cloud_run_v2_service" "frontend" {
  name     = "ai-shifts-frontend"
  location = var.region

  template {
    containers {
      image = var.image_frontend
      ports {
        container_port = 80
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

########################################
# Cloud Run runtime SA → Secret Manager access
########################################
data "google_project" "current" {}

resource "google_secret_manager_secret_iam_member" "backend_secret_access" {
  for_each = toset(local.secret_names)

  secret_id  = each.key
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  depends_on = [google_secret_manager_secret.app_secrets]
}

########################################
# Budget alert
########################################
data "google_billing_account" "linked" {
  count           = var.budget_notification_email == "" ? 0 : 1
  billing_account = data.google_project.current.billing_account
}

resource "google_monitoring_notification_channel" "email" {
  count        = var.budget_notification_email == "" ? 0 : 1
  display_name = "Budget alert email"
  type         = "email"
  labels = {
    email_address = var.budget_notification_email
  }
  depends_on = [google_project_service.apis]
}

resource "google_billing_budget" "monthly_cap" {
  count           = var.budget_notification_email == "" ? 0 : 1
  billing_account = data.google_billing_account.linked[0].id
  display_name    = "AI-Shifts monthly budget"

  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }

  amount {
    specified_amount {
      currency_code = "JPY"
      units         = var.budget_amount_jpy
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.email[0].id]
    disable_default_iam_recipients   = false
  }

  depends_on = [google_project_service.apis]
}

########################################
# Outputs
########################################
output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}
