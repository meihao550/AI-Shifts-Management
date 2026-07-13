########################################
# AI-Shifts-Management — GCP deploy skeleton
# NOTE: Requires you to run `gcloud auth application-default login`
# and set `project_id` / `region` variables.
########################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
  # Configure a GCS backend before applying:
  # backend "gcs" { bucket = "your-tfstate-bucket" prefix = "ai-shifts" }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

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
  description = "Container image for the FastAPI backend (Artifact Registry URL)"
  type        = string
}

variable "image_frontend" {
  description = "Container image for the Vue frontend (Artifact Registry URL)"
  type        = string
}

variable "db_instance_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro"
}

# --- Cloud SQL (PostgreSQL) ------------------------------------------------
resource "google_sql_database_instance" "db" {
  name             = "ai-shifts-db"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier = var.db_instance_tier
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }
  }
  deletion_protection = false
}

resource "google_sql_database" "app" {
  name     = "shifts_db"
  instance = google_sql_database_instance.db.name
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "google_sql_user" "app" {
  name     = "shifts"
  instance = google_sql_database_instance.db.name
  password = random_password.db_password.result
}

# --- Secrets ---------------------------------------------------------------
resource "google_secret_manager_secret" "app_secrets" {
  for_each = toset([
    "database-url",
    "secret-key",
    "google-client-id",
    "google-client-secret",
    "anthropic-api-key",
    "openai-api-key",
  ])
  secret_id = each.key
  replication {
    auto {}
  }
}

# --- Cloud Run: backend ----------------------------------------------------
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
        name  = "DATABASE_URL"
        value = "postgresql+psycopg://${google_sql_user.app.name}:${random_password.db_password.result}@${google_sql_database_instance.db.public_ip_address}:5432/${google_sql_database.app.name}"
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Cloud Run: frontend --------------------------------------------------
resource "google_cloud_run_v2_service" "frontend" {
  name     = "ai-shifts-frontend"
  location = var.region

  template {
    containers {
      image = var.image_frontend
      ports {
        container_port = 80
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "db_public_ip" {
  value = google_sql_database_instance.db.public_ip_address
}
