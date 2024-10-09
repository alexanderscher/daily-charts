resource "aws_ecr_repository" "spotify_charts_ecr" {
  name = "spotify-charts-ecr"
}


data "aws_ecr_image" "spotify_charts_ecr" {
  repository_name = aws_ecr_repository.spotify_charts_ecr.name
  image_tag       = "latest"
}


resource "aws_ecr_repository" "velocity_ecr" {
  name = "velocity-ecr"
}

data "aws_ecr_image" "velocity_ecr" {
  repository_name = aws_ecr_repository.velocity_ecr.name
  image_tag       = "latest"
}
