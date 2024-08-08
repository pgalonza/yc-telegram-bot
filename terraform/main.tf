terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.74"
}

provider "yandex" {
  zone = "${var.yc_zone}"
}

resource "yandex_iam_service_account" "sa-telegram-bot" {
  name        = "sa-telegram-bot1"
  description = "service account to manage VMs"
}

resource "yandex_resourcemanager_folder_iam_member" "function-invoker-role" {
  folder_id = "${var.yc_folder_id}"
  role      = "functions.functionInvoker"
  member    = "serviceAccount:${yandex_iam_service_account.sa-telegram-bot.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "image-generation-user-role" {
  folder_id = "${var.yc_folder_id}"
  role      = "ai.imageGeneration.user"
  member    = "serviceAccount:${yandex_iam_service_account.sa-telegram-bot.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "functions-viewer-role" {
  folder_id = "${var.yc_folder_id}"
  role      = "functions.viewer"
  member    = "serviceAccount:${yandex_iam_service_account.sa-telegram-bot.id}"
}

resource "yandex_function" "telegram-bot-silvana" {
  depends_on = [
    yandex_iam_service_account.sa-telegram-bot,
    yandex_resourcemanager_folder_iam_member.function-invoker-role,
    yandex_resourcemanager_folder_iam_member.image-generation-user-role,
    yandex_resourcemanager_folder_iam_member.functions-viewer-role
  ]
  name               = "telegram-bot-silvana"
  user_hash          = "1.0.0"
  runtime            = "python312"
  entrypoint         = "index.handler"
  memory             = "128"
  execution_timeout  = "120"
  service_account_id = "${yandex_iam_service_account.sa-telegram-bot.id}"
  environment = {
    TELEGRAM_TOKEN = "${var.tg_bot_token}"
  }
  content {
    zip_filename = "../index.zip"
  }
}

resource "yandex_api_gateway" "recognizer-bot-api-gw" {
  name        = "recognizer-bot-api-gw"
  spec = <<-EOT
    openapi: 3.0.0
    info:
      title: Sample API
      version: 1.0.0

    paths:
      /bot1:
        post:
          x-yc-apigateway-integration:
            type: cloud_functions
            function_id: ${yandex_function.telegram-bot-silvana.id}
            service_account_id: ${yandex_iam_service_account.sa-telegram-bot.id}
          operationId: for-recognizer-bot-function
  EOT

  provisioner "local-exec" {
    command = "curl --request POST --url https://api.telegram.org/bot${var.tg_bot_token}/setWebhook --header 'content-type: application/json' --data '{\"url\": \"${yandex_api_gateway.recognizer-bot-api-gw.domain}/bot1\"}'"
  }
}

variable "yc_folder_id" {
  type = string
}

variable "yc_zone" {
  type = string
}

variable "tg_bot_token" {
  type = string
}

output "api-gateway-domain" {
  value = yandex_api_gateway.recognizer-bot-api-gw.domain
}