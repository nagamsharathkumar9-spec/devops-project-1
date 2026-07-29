

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "docker-desktop"
}

resource "kubernetes_job" "ema_backtester" {
  metadata {
    name = "ema-backtester-tf"
    labels = {
      app = "ema-backtester"
    }
  }

  spec {
    ttl_seconds_after_finished = 120

    template {
      metadata {}

      spec {
        container {
          name  = "ema-backtester"
          image = "docker.io/library/ema-backtester:latest"

          image_pull_policy = "Never"
        }

        restart_policy = "Never"
      }
    }
  }

  wait_for_completion = false
}


# ============================================================
# AWS DLM (Data Lifecycle Manager) — Automated EBS Snapshots
# RPO: 24 hours (daily snapshots)
# Retention: 7 days of snapshots
# ============================================================

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# IAM role for DLM to manage snapshots
resource "aws_iam_role" "dlm_lifecycle_role" {
  name = "ema-backtester-dlm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dlm_lifecycle" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
  role       = aws_iam_role.dlm_lifecycle_role.name
}

# DLM policy — daily snapshots, retain 7 days
resource "aws_dlm_lifecycle_policy" "ebs_backup" {
  description        = "EMA Backtester PostgreSQL EBS daily backup"
  execution_role_arn = aws_iam_role.dlm_lifecycle_role.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    schedule {
      name = "Daily snapshots — 7 day retention"

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"]  # 3 AM IST snapshot
      }

      retain_rule {
        count = 7  # keep last 7 snapshots (7 days)
      }

      tags_to_add = {
        SnapshotCreator = "DLM"
        Project         = "ema-backtester"
      }

      copy_tags = true
    }

    target_tags = {
      Project = "ema-backtester"
    }
  }
}