

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
      aws_access_key_id      = var.aws_access_key_id
      aws_secret_access_key  = var.aws_secret_access_key
      ALEX                   = var.alex
      ARI                    = var.ari
      LAURA                  = var.laura
      CONOR                  = var.conor
      SPOTIFY_CHART_USERNAME = var.spotify_chart_username
      SPOTIFY_CHART_PASSWORD = var.spotify_chart_password
      DB_PASSWORD            = var.db_password
    }
  }

}


