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

resource "aws_lambda_function" "apple_charts" {
  function_name = "apple-charts"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.apple_charts_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048

  environment {
    variables = {
      SPOTIFY_CLIENT_ID     = var.spotify_client_id
      SPOTIFY_CLIENT_SECRET = var.spotify_client_secret
      SPOTIFY_USER_ID       = var.spotify_user_id
      APPLE_TEAM_ID         = var.apple_team_id
      APPLE_KEY_ID          = var.apple_key_id
      APPLE_PRIVATE_KEY     = var.apple_private_key
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



resource "aws_lambda_function" "soundcloud_charts" {
  function_name = "soundcloud-charts"
  role          = aws_iam_role.charts_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.soundcloud_charts_ecr.repository_url}:latest"
  timeout       = 480
  memory_size   = 2048


}
