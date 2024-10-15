resource "aws_lambda_function" "spotify_charts" {
  function_name = "spotify-charts"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.spotify_charts_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      SPOTIFY_CLIENT_ID      = var.spotify_client_id
      SPOTIFY_CLIENT_SECRET  = var.spotify_client_secret
      SPOTIFY_USER_ID        = var.spotify_user_id
      ALEX                   = var.alex
      ALEX_MAIL              = var.alex_mail
      ARI                    = var.ari
      LAURA                  = var.laura
      CONOR                  = var.conor
      MICAH                  = var.micah
      SPOTIFY_CHART_USERNAME = var.spotify_chart_username
      SPOTIFY_CHART_PASSWORD = var.spotify_chart_password
      DB_PASSWORD            = var.db_password
    }
  }

}

resource "aws_lambda_function" "velocity" {
  function_name = "velocity"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.velocity_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      SPOTIFY_CLIENT_ID_L2TK     = var.spotify_client_id_l2tk
      SPOTIFY_CLIENT_SECRET_L2TK = var.spotify_client_secret_l2tk
      SPOTIFY_USER_ID_L2TK       = var.spotify_user_id_l2tk
      ALEX                       = var.alex
      ALEX_MAIL                  = var.alex_mail
      ARI                        = var.ari
      LAURA                      = var.laura
      CONOR                      = var.conor
      MICAH                      = var.micah
      DB_PASSWORD                = var.db_password
    }
  }

}

resource "aws_lambda_function" "apple_charts" {
  function_name = "apple-charts"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.apple_charts_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      SPOTIFY_CLIENT_ID_ALENA     = var.spotify_client_id_alena
      SPOTIFY_CLIENT_SECRET_ALENA = var.spotify_client_secret_alena
      SPOTIFY_USER_ID_ALENA       = var.spotify_user_id_alena
      APPLE_TEAM_ID               = var.apple_team_id
      APPLE_KEY_ID                = var.apple_key_id
      APPLE_PRIVATE_KEY           = var.apple_private_key
      ALEX                        = var.alex
      ALEX_MAIL                   = var.alex_mail
      ARI                         = var.ari
      LAURA                       = var.laura
      CONOR                       = var.conor
      MICAH                       = var.micah
      DB_PASSWORD                 = var.db_password
    }
  }

}

resource "aws_lambda_function" "shazam_charts" {
  function_name = "shazam-charts"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.shazam_charts_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      SPOTIFY_CLIENT_ID     = var.spotify_client_id
      SPOTIFY_CLIENT_SECRET = var.spotify_client_secret
      SPOTIFY_USER_ID       = var.spotify_user_id
      ALEX                  = var.alex
      ALEX_MAIL             = var.alex_mail
      ARI                   = var.ari
      LAURA                 = var.laura
      CONOR                 = var.conor
      MICAH                 = var.micah
      DB_PASSWORD           = var.db_password
    }
  }

}


resource "aws_lambda_function" "no_track" {
  function_name = "no-track"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.no_track_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      GOOGLE_CLIENT_EMAIL = var.google_client_email
      GOOGLE_PROJECT_ID   = var.google_project_id
    }
  }
}
resource "aws_secretsmanager_secret" "google_private_key" {
  name        = "google_private_key"
  description = "Google private key for Lambda"
}

resource "aws_secretsmanager_secret_version" "google_private_key_version" {
  secret_id     = aws_secretsmanager_secret.google_private_key.id
  secret_string = <<EOF
${var.google_private_key}
EOF
}

