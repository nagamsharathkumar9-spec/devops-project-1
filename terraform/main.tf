

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