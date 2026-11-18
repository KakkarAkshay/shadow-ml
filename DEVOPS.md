# DEVOPS.md: Shadow-ml DevOps Implementation

Author: Akshay Kakkar
Repository: https://github.com/KakkarAkshay/shadow-ml
Live application (HTTPS via CloudFront): https://d3cmtsxej3xov8.cloudfront.net

---

## 1. Project overview and technology stack

**Shadow-ml** is a text classifier built for the Shadow AI Security and Data Loss Prevention Gateway project. It detects sensitive content (API keys, passwords, emails, phone numbers, payment cards, other PII, source code) in text prompts. For this assignment, the existing machine-learning project was wrapped in a small web service and turned into a DevOps-enabled application: version control, containerisation, automated CI/CD, cloud deployment and CDN delivery.

| Area | Technology |
|---|---|
| Application | Python 3.12, FastAPI, scikit-learn (trained model `final_model.joblib`) |
| Tests | pytest (8 tests: 5 model tests, 3 API tests) |
| Source control | Git and GitHub (private repository) |
| Containers | Docker (`python:3.12-slim` base image, non-root user) |
| CI/CD | Jenkins 2.580.2 with a declarative `Jenkinsfile` |
| Registry | AWS ECR (private repository `shadow-ml`) |
| Hosting | AWS EC2 (Ubuntu 24.04): one Jenkins server, one application server |
| CDN and HTTPS | AWS CloudFront |
| Region | Asia Pacific (Sydney), ap-southeast-2 |

Application endpoints:

| Path | Purpose |
|---|---|
| `/` | Web page with a text box and a Classify button |
| `/health` | Health check, returns `{"status":"ok","version":"<build number>"}` |
| `POST /api/classify` | Returns `label`, `confidence` and `coarse_label` for the submitted text |

---

## 2. DevOps architecture diagram

```mermaid
flowchart LR
    Dev["Developer<br/>Git Bash on PC"] -->|"push, pull request merge"| GH["GitHub<br/>main and develop"]
    GH -->|"webhook on push"| J["Jenkins server (EC2)<br/>Checkout, Install, Test, Build,<br/>Docker Build, Docker Push, Deploy"]
    J -->|"docker push (IAM role)"| ECR[("AWS ECR<br/>shadow-ml")]
    J -->|"SSH over private network<br/>runs deploy.sh"| APP["App server (EC2)<br/>Docker container on port 80"]
    ECR -->|"docker pull"| APP
    User["Users<br/>browser"] -->|"HTTPS"| CF["AWS CloudFront"]
    CF -->|"HTTP port 80"| APP
```

Flow in words: a merge to `main` triggers GitHub to call the Jenkins webhook. Jenkins tests and builds the code, packs a Docker image, pushes it to ECR, and tells the application server (over the private network) to pull and run the new image. Visitors reach the application through CloudFront over HTTPS.

![Architecture diagram](docs/screenshots/00-architecture-diagram.png)

---

## 3. Git repository structure

```
shadow-ml/
├── app/                  FastAPI service (main.py)
├── ml/                   classifier code and model tests
├── static/               web page (index.html, style.css)
├── tests/                API tests
├── deploy/deploy.sh      deployment script with health check and rollback
├── docs/screenshots/     evidence screenshots used in this document
├── Dockerfile
├── .dockerignore
├── Jenkinsfile
├── requirements.txt      pinned library versions
├── final_model.joblib    trained model
├── README.md
├── DEVOPS.md
└── .gitignore, .gitattributes, .env.example
```

Branching model:

- `main`: stable, deployed branch. A push to `main` triggers the pipeline.
- `develop`: integration branch.
- `feature/*`: every change is made on a feature branch and merged by pull request into `develop`, then from `develop` into `main`.

Secrets are never committed: `.env`, keys and tokens are in `.gitignore`, and `.env.example` shows only harmless defaults. Jenkins credentials and AWS roles hold all secrets.

![GitHub repository](docs/screenshots/01-github-repo.png)
![README shown on the repository page](docs/screenshots/01b-readme.png)
![Branches](docs/screenshots/02-github-branches.png)
![Merged pull requests](docs/screenshots/03-github-pull-requests.png)
![Commit history](docs/screenshots/04-github-commits.png)

---

## 4. Docker build and run instructions

The Dockerfile uses `python:3.12-slim`, installs the pinned requirements first (so rebuilds are fast), copies only the files the service needs, runs as a non-root user, exposes port 8000, defines a container `HEALTHCHECK` against `/health`, and reads its settings from environment variables (`APP_PORT`, `MODEL_PATH`, `APP_VERSION`).

Build and run locally:

```bash
docker build -t shadow-ml:local .
docker run -d --name shadow-ml -p 8000:8000 -e APP_VERSION=local-1 shadow-ml:local
docker ps                      # status shows (healthy) after about 30 seconds
curl http://localhost:8000/health
docker stop shadow-ml && docker rm shadow-ml
```

Open http://localhost:8000 to use the application.

![Docker image built](docs/screenshots/05-docker-image.png)
![Container running and healthy](docs/screenshots/06-docker-running.png)
![Docker Desktop showing the container](docs/screenshots/06b-docker-desktop.png)
![Application on localhost](docs/screenshots/07-app-localhost.png)
![Safe text classified as SAFE](docs/screenshots/07b-app-localhost-safe.png)
![Health endpoint from the container](docs/screenshots/07c-health-localhost.png)

---

## 5. Jenkins pipeline stages

Jenkins runs on its own EC2 server. The job `shadow-ml-pipeline` is a "Pipeline script from SCM" that reads the `Jenkinsfile` from the `main` branch. A GitHub webhook (`/github-webhook/`, push events) starts a build automatically on every push to `main`.

| Stage | What it does |
|---|---|
| Checkout | Downloads the latest code from GitHub |
| Install | Creates a virtual environment and installs the pinned requirements |
| Test | Runs `pytest`; a failing test stops the pipeline |
| Build | Byte-compiles the application (`python -m compileall`) to catch build errors |
| Docker Build | Builds the image, tagged with the Jenkins build number |
| Docker Push | Logs in to ECR and pushes the image as `<build number>` and `latest` |
| Deploy | Connects to the app server over SSH, pulls the new image, restarts the container, health-checks it, and rolls back on failure |

Credentials and access:

- `github-token`: fine-grained GitHub token with read-only access to this one repository, stored in Jenkins credentials.
- `app-server-ssh`: SSH private key for deployment, stored in Jenkins credentials.
- AWS access uses an IAM role attached to the Jenkins server (`jenkins-ecr-role`, ECR power-user policy), so no AWS keys are stored anywhere.
- The Deploy stage creates a short-lived ECR login token on Jenkins and passes it to the app server, which therefore stores no long-term credentials.

Any failure in a stage (tests, build, push or deploy) makes the whole build fail.

![Jenkins stages, all green](docs/screenshots/08-jenkins-stages.png)
![First pipeline run (build 1)](docs/screenshots/08b-jenkins-build1-stages.png)
![Console output, Finished: SUCCESS](docs/screenshots/09-jenkins-console-success.png)
![GitHub webhook with a successful delivery](docs/screenshots/10-github-webhook.png)

---

## 6. AWS infrastructure details

All resources are in ap-southeast-2 (Sydney).

| Resource | Details |
|---|---|
| `jenkins-server` | EC2 t3.small, Ubuntu 24.04, 20 GiB, Docker, Java 21, Jenkins, AWS CLI v2, 2 GB swap, Elastic IP |
| `app-server` | EC2 t3.micro, Ubuntu 24.04, 12 GiB, Docker installed through user data at first boot, Elastic IP |
| ECR repository | `shadow-ml` (private, mutable tags) |
| IAM role `jenkins-ecr-role` | ECR power-user policy, attached to the Jenkins server |
| IAM role `app-ecr-read-role` | ECR read-only policy, attached to the app server |
| Security group `jenkins-sg` | SSH (browser connect range only), TCP 8080 for Jenkins and the GitHub webhook |
| Security group `app-sg` | SSH only from `jenkins-sg` and from the browser connect range, HTTP 80 for CloudFront and visitors |
| Elastic IPs | One per server, so addresses survive stop and start |

Notes:

- Jenkins reaches the app server over the private VPC address, which does not change.
- SSH from a personal PC is restricted; administration uses the browser-based EC2 Instance Connect.

![EC2 instances](docs/screenshots/11-ec2-instances.png)
![ECR repository](docs/screenshots/12-ecr-repository.png)
![ECR images with tags](docs/screenshots/12b-ecr-images.png)
![Application served from the EC2 server](docs/screenshots/13-deploy-app-ec2.png)
![Health check on the EC2 address, version 2](docs/screenshots/13b-health-ec2.png)

---

## 7. CloudFront configuration summary

Distribution `E3HTC4R4KFJW5A` (name `shadow-ml-cdn`).

| Setting | Value |
|---|---|
| Origin | The app server's public DNS name |
| Origin protocol | HTTP only, port 80 |
| Viewer protocol | Redirect HTTP to HTTPS (default `*.cloudfront.net` certificate) |
| Default behaviour `*` | Cache policy `CachingDisabled`, all HTTP methods allowed (needed for `POST /api/classify`), origin request policy `AllViewerExceptHostHeader`. The page and the API are never cached. |
| Behaviour `/static/*` | Cache policy `CachingOptimized`, GET and HEAD only. Static assets are cached at edge locations. |

Updated content after a deployment:

- The HTML page and the API come from the default behaviour, which is not cached, so changes appear immediately after a deployment.
- Cached static files (`/static/*`) are refreshed with a CloudFront invalidation of `/static/*`.

Cache check from the command line (first request `Miss`, second `Hit`; `/health` is always `Miss`):

```bash
curl -s -D - -o /dev/null https://d3cmtsxej3xov8.cloudfront.net/static/style.css | grep -i x-cache
curl -s -D - -o /dev/null https://d3cmtsxej3xov8.cloudfront.net/health | grep -i x-cache
```

Limitation: traffic between CloudFront and the origin uses HTTP. For a production deployment, HTTPS should also be configured on the origin, for example with a domain name and certificate or an Application Load Balancer.

![CloudFront behaviours](docs/screenshots/16-cloudfront-behaviors.png)
![Default behaviour settings](docs/screenshots/16b-cloudfront-behaviors-default.png)
![CloudFront origin](docs/screenshots/17-cloudfront-origins.png)
![Application over HTTPS on the CloudFront URL](docs/screenshots/18-cloudfront-https.png)
![Cache headers: Miss and Hit](docs/screenshots/19-cache-headers.png)

---

## 8. Application deployment and rollback procedure

### Normal deployment (automatic)

1. Create a feature branch, make a change, push it, and merge by pull request into `develop`, then into `main`.
2. GitHub calls the Jenkins webhook, and Jenkins runs the pipeline.
3. In the Deploy stage, `deploy/deploy.sh` on the app server:
   - pulls the new image from ECR,
   - starts it with `--restart unless-stopped` (so it also returns after an EC2 reboot),
   - checks `http://localhost/health` for up to 60 seconds.
4. If the health check passes, the deployment is complete and `/health` reports the new build number.

### Automatic rollback

If the new container is not healthy within 60 seconds, the script removes it, starts the previous image again (the image the old container was using), prints `Rolled back to ...`, and exits with an error so the Jenkins build is marked failed.

Tested by deploying a deliberately broken release (`nginx:alpine`, which does not answer `/health`):

```bash
bash /tmp/deploy.sh nginx:alpine broken
```

The script reported `Health check failed - rolling back`, then `Rolled back to ...shadow-ml:2`, and `/health` returned the previous version.

### Manual rollback

On the app server, run a previous image tag:

```bash
docker rm -f shadow-ml
docker run -d --name shadow-ml --restart unless-stopped -p 80:8000 \
  -e APP_VERSION=<old build number> <account>.dkr.ecr.ap-southeast-2.amazonaws.com/shadow-ml:<old build number>
```

### Restart after reboot

After stopping and starting the app server, the container came back automatically (`Up ... (healthy)`) without any new deployment.

![Rollback test](docs/screenshots/14-rollback-test.png)
![Reboot test](docs/screenshots/15-reboot-test.png)

---

## 9. End-to-end demonstration (Task 6)

With the application live behind CloudFront, the page heading was changed to "Shadow-ml Classifier - CI/CD Demo" and a blue colour was added in `static/style.css`. The change was committed on a feature branch and merged into `main`. Without any manual build or file copy:

1. GitHub triggered Jenkins (console starts with "Started by GitHub push").
2. Jenkins ran the tests, built the image, pushed it to ECR and deployed it to the app server.
3. The CloudFront URL showed the new heading immediately and `/health` showed the new build number.
4. After a CloudFront invalidation of `/static/*`, the new stylesheet (blue heading) was served.

![Webhook-triggered build](docs/screenshots/20-demo-webhook-trigger.png)
![Pipeline green, including Deploy](docs/screenshots/21-demo-pipeline-green.png)
![New page on the CloudFront URL](docs/screenshots/22-demo-new-page.png)
![Health endpoint with the new build number](docs/screenshots/22b-demo-health-version.png)
![Invalidation completed](docs/screenshots/23-demo-invalidation.png)
![Blue heading after the invalidation](docs/screenshots/23b-demo-new-style.png)

---

## 10. Challenges encountered and solutions

| Challenge | Solution |
|---|---|
| Project folder was inside OneDrive, which can lock Git files and carried a Python environment tied to the old path | Copied the project to `C:\dev\shadow-ml` and recreated the environment from a pinned `requirements.txt` |
| Docker Desktop installation failed because a Windows feature was missing | Reinstalled as administrator with the all-users option and installed WSL |
| The model file depends on exact library versions | Pinned scikit-learn, numpy, scipy and joblib to the versions used for training, and used the same Python version (3.12) in Docker and Jenkins |
| The AWS Free plan only allows the account's home region | Used Sydney (ap-southeast-2) for every resource |
| Online guides used an expired Jenkins repository signing key | Used the current key published in Jenkins' own documentation |
| SSH from a personal PC timed out | Used the browser-based EC2 Instance Connect with a narrow security group rule |
| Server public addresses changed after stopping and starting, which broke the webhook | Attached Elastic IPs to both servers and updated the webhook URL |
| `/tmp` is cleared on reboot, so the deploy script disappeared from the app server | The pipeline copies `deploy.sh` to the server on every deployment |
| The Classify button needs POST requests, which CloudFront blocks by default | Allowed all HTTP methods on the default behaviour and disabled caching there; only `/static/*` is cached |
| Jenkins needs a way to authenticate to a private repository and to AWS | Fine-grained read-only GitHub token in Jenkins credentials, and an IAM role instead of stored AWS keys |

---

## 11. Acceptance criteria checklist

| Criterion | Status |
|---|---|
| Project stored in GitHub with version control | Done |
| Application runs in a Docker container | Done |
| Pipeline defined in a `Jenkinsfile` | Done |
| A Git push automatically triggers Jenkins | Done (webhook) |
| Automated tests run before deployment | Done (Test stage) |
| Image published to AWS ECR | Done |
| Jenkins deploys the latest successful image to EC2 | Done |
| Application accessible over HTTPS through CloudFront | Done |
| A code change appears in the deployed application after the pipeline runs | Done (Section 9) |
| Documentation and deployment evidence submitted | This document and the screenshots |
