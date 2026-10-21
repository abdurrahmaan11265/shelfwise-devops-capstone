# ShelfWise: library management, from laptop to monitored Kubernetes

[![ci-cd](https://github.com/abdurrahmaan11265/shelfwise-devops-capstone/actions/workflows/ci-cd.yml/badge.svg?branch=main)](https://github.com/abdurrahmaan11265/shelfwise-devops-capstone/actions/workflows/ci-cd.yml)
· **Evidence for every grading module: [Grading evidence](#17-grading-evidence)** · **Presentation: [slides (PDF)](docs/shelfwise-capstone-presentation.pdf) · [narrated walkthrough (MP4, 11 min)](docs/shelfwise-capstone-walkthrough.mp4)**

**ShelfWise** is a library management system: a catalogue of books, the copies on each shelf,
and who has borrowed what. Librarians search and filter the catalogue, add and edit books,
lend copies to borrowers, take them back, and see what is on loan or overdue at a glance.

This repository is my DevOps capstone. The application is mine; around it sits the full
delivery path from the course:

```text
Developer → Git/GitHub → GitHub Actions (pytest · build · Trivy · GHCR · Helm deploy + smoke test)
          → Terraform (AWS VPC + EKS) → Helm → Kubernetes (Ingress · HPA · probes)
          → Prometheus + Grafana → troubleshooting
```

**Author:** Mohammed Abdurrahman (24BCS10130)

![ShelfWise dashboard](docs/screenshots/m1-app-dashboard.png)

---

## Contents

1. [Architecture](#1-architecture)
2. [Tech stack](#2-tech-stack)
3. [Repository layout](#3-repository-layout)
4. [Run it locally with Docker Compose](#4-run-it-locally-with-docker-compose)
5. [The application: features and REST API](#5-the-application)
6. [Tests](#6-tests)
7. [Docker images](#7-docker-images)
8. [CI/CD pipeline](#8-cicd-pipeline)
9. [Security scanning (Trivy)](#9-security-scanning-trivy)
10. [Kubernetes + Helm](#10-kubernetes--helm)
11. [Terraform: AWS VPC + EKS](#11-terraform-aws-vpc--eks)
12. [Monitoring: Prometheus + Grafana](#12-monitoring-prometheus--grafana)
13. [Autoscaling demo](#13-autoscaling-demo)
14. [Troubleshooting labs](#14-troubleshooting-labs)
15. [Demo: commit to deployment](#15-demo-commit-to-deployment)
16. [Design decisions](#16-design-decisions)
17. [Grading evidence](#17-grading-evidence)

---

## 1. Architecture

```mermaid
flowchart LR
    dev([Developer]) -->|git push| gh[GitHub]
    gh --> ci{{GitHub Actions}}
    ci -->|pytest · npm build| test[Test gate]
    test --> build[docker build x2]
    build --> trivy[Trivy scan<br/>fail on fixable HIGH/CRITICAL]
    trivy --> ghcr[(GHCR<br/>image:git-sha<br/>amd64 + arm64)]
    ghcr -->|helm upgrade --install<br/>+ smoke test| k8s

    tf[Terraform] -.->|VPC + EKS| aws[(AWS ap-south-1)]

    subgraph k8s[Kubernetes - namespace shelfwise]
      ing[Ingress<br/>shelfwise.local] -->|/| fe[Frontend x2..4<br/>React + nginx · HPA]
      ing -->|/api · /docs| be[Backend x2..6<br/>FastAPI · HPA]
      fe -.->|/api proxy| be
      be --> pg[(PostgreSQL<br/>StatefulSet + PVC)]
      prom[Prometheus] -->|ServiceMonitor<br/>/metrics| be
      graf[Grafana] --> prom
    end
    user([Browser]) --> ing
```

* The browser only calls **relative `/api/...` URLs**. Through the Ingress, `/api` goes straight
  to the backend Service; under Docker Compose the frontend's nginx proxies `/api` to the
  backend. The browser never needs an internal hostname.
* The backend runs `alembic upgrade head` on start, guarded by a PostgreSQL advisory lock so
  several replicas starting together migrate one at a time, then starts Uvicorn.

## 2. Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, hand-written responsive CSS, served by unprivileged nginx |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.1, Pydantic, Uvicorn |
| Database | PostgreSQL 16, Alembic migrations |
| Tests | pytest with an in-memory SQLite database |
| Containers | non-root backend image, multi-stage frontend image, Docker Compose |
| CI/CD | GitHub Actions, Trivy, GHCR, multi-arch images, kind deploy + smoke test |
| Infrastructure | Terraform (AWS provider 5.x): VPC, subnets, NAT, IAM, EKS + managed node group |
| Kubernetes | Helm chart, nginx Ingress, HPA (metrics-server), startup/readiness/liveness probes |
| Observability | prometheus-fastapi-instrumentator, kube-prometheus-stack (Prometheus + Grafana) |

## 3. Repository layout

```text
.
├── backend/                  FastAPI service
│   ├── app/                  config, db, models, schemas, routes (main.py)
│   ├── alembic/versions/     0001_create_books_and_loans, 0002_seed_catalogue
│   ├── tests/                12 pytest cases, in-memory SQLite
│   ├── Dockerfile            non-root (uid 10001), HEALTHCHECK on /health
│   └── requirements*.txt     runtime / dev dependencies (pinned)
├── frontend/                 React + Vite dashboard
│   ├── src/                  App, API client, styles
│   ├── nginx.conf.template   proxies /api to $BACKEND_URL
│   └── Dockerfile            node build stage → nginx-unprivileged runtime (uid 101)
├── docker-compose.yml        postgres + backend + frontend
├── .github/workflows/        ci-cd.yml: test → build, scan, push → deploy + smoke test
├── terraform/                AWS VPC + EKS, tfvars example (see Section 11)
├── k8s/                      namespace manifest
├── helm/shelfwise/           chart: deployments, services, PostgreSQL, ingress, HPA, ServiceMonitor
├── monitoring/               kube-prometheus-stack values, Grafana dashboard
├── troubleshooting/          3 deliberately broken manifests
├── scripts/                  load generator for the HPA and dashboards
└── docs/screenshots/         evidence for every module
```

## 4. Run it locally with Docker Compose

Requirements: Docker Desktop (or Docker Engine + Compose v2).

```bash
docker compose up --build
```

| URL | What |
|-----|------|
| http://localhost:3000 | ShelfWise UI (a starter catalogue is seeded by migration 0002) |
| http://localhost:8000/docs | Swagger UI: try every endpoint |
| http://localhost:8000/health · /ready · /metrics | liveness · readiness · Prometheus metrics |

```bash
docker compose down          # stop
docker compose down -v       # stop and delete the database volume
```

Ports are configurable (`FRONTEND_PORT=3300 BACKEND_PORT=8800 docker compose up --build`) for
machines where 3000/8000 are taken, which is how the screenshots were taken.

<details>
<summary>Run the backend and frontend without Docker</summary>

```bash
# backend (needs PostgreSQL, e.g. `docker compose up -d postgres`)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://shelfwise:shelfwise@localhost:5432/shelfwise'
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend (Vite proxies /api to localhost:8000)
cd frontend && npm ci && npm run dev
```
</details>

## 5. The application

**UI features:** dark sidebar with the running build's commit SHA · KPI cards (titles, copies,
on loan, overdue) · catalogue table with search by title, author or ISBN and genre/availability
filters · add/edit book modal · lend and return actions · count by genre · recent activity
feed · toasts · responsive layout that works on a phone.

| Add a book | Mobile |
|---|---|
| ![add book](docs/screenshots/m1-app-add-book.png) | ![mobile](docs/screenshots/m1-app-mobile.png) |

**Domain rules enforced by the API**

* ISBNs are unique: a duplicate returns **409 Conflict**; invalid input returns **422**.
* Total copies cannot drop below the copies currently on loan.
* A book cannot be deleted while any of its copies are on loan.
* Lending fails when no copies are left.
* Check constraints keep `available_copies` between 0 and `total_copies` in the database
  itself, not only in Python.

**REST API** (full interactive docs at `/docs`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/books` | list; filters `?q=` (search), `?genre=`, `?available=` |
| GET | `/api/books/{id}` | one book |
| POST | `/api/books` | add a book (409 on duplicate ISBN, 422 on invalid input) |
| PUT | `/api/books/{id}` | update; total copies cannot drop below copies on loan |
| DELETE | `/api/books/{id}` | delete; refused while copies are on loan |
| GET | `/api/books/stats` | titles, copies, on loan, overdue, count by genre |
| POST | `/api/books/{id}/checkout` | lend a copy to a borrower |
| POST | `/api/loans/{id}/return` | return it |
| GET | `/api/loans` | recent loans for the activity feed |
| GET | `/api/info` | library name and the **commit SHA of the running build** |
| GET | `/health` | liveness: the process is up (does not touch the DB) |
| GET | `/ready` | readiness: 503 until PostgreSQL answers |
| GET | `/metrics` | Prometheus metrics (requests, latency histograms) |

**Database** (`backend/alembic/versions/`): two tables, `books` and `loans`, created by migration
`0001`. Migration `0002` seeds a starter catalogue so a fresh install is not an empty page.

## 6. Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v                              # 12 tests over 8 endpoints
```

| Area | Tests in `tests/test_api.py` |
|------|------------------------------|
| System | `/health`, `/ready` checks the database, `/metrics`, `/api/info` reports the version |
| Books CRUD | create and get, list and search, update, delete |
| Validation | duplicate ISBN rejected (409), invalid input (422) |
| Lending | checkout, return and stats; lending fails with no copies left |

**The tests never touch the real database.** `tests/conftest.py` overrides the FastAPI `get_db`
dependency so every test runs against a fresh in-memory SQLite database. Configuration lives
in `backend/pytest.ini` and `backend/tests/conftest.py`.

## 7. Docker images

| Image | Build | Runtime user |
|-------|-------|--------------|
| `shelfwise-backend` | `python:3.12-slim`, OS packages upgraded at build time, dependencies installed before the code is copied (better layer caching), `HEALTHCHECK` on `/health` | uid **10001** |
| `shelfwise-frontend` | **multi-stage**: `node:22-alpine` runs `npm ci && npm run build` → `nginxinc/nginx-unprivileged` serves only `dist/` on port 8080 | uid **101** |

Node never reaches the frontend runtime image. nginx gets the backend address from
`BACKEND_URL` through its template mechanism, so the same image works in Compose and in Kubernetes.

```bash
docker build -t shelfwise-backend:local ./backend
docker build -t shelfwise-frontend:local ./frontend
```

## 8. CI/CD pipeline

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) runs on every push and pull request to `main`.

```text
test ──▶ build (backend, frontend in parallel) ──▶ deploy
pytest    docker build → Trivy gate → push to GHCR    kind cluster → helm upgrade --install → smoke test
npm build
```

| Job | Fails the build when… |
|-----|----------------------|
| `test` | any pytest case fails, or `npm ci` / `npm run build` fails |
| `build` | the image does not build, or **Trivy finds a fixable HIGH/CRITICAL CVE**; only then is it pushed to `ghcr.io/abdurrahmaan11265/shelfwise-{backend,frontend}:<commit SHA>`, multi-arch (amd64 + arm64), never `latest` |
| `deploy` | the chart does not install on a fresh kind cluster (nginx ingress + metrics-server), or the smoke test through the Ingress fails: read stats, load the UI, create a book, read it back |

Because the image tag is the commit SHA, every running pod traces back to an exact commit, and
the UI sidebar shows it.

Two real bugs were caught by this pipeline during development, both visible in the run history:

* the Ingress was rejected by ingress-nginx's strict path validation (`/openapi.json` with `pathType: Exact`);
* the migrations were silently rolled back because the advisory-lock query had opened the
  transaction Alembic ran inside. The smoke test caught it as a 500 from `/api/books/stats`;
  it is fixed by committing explicitly after the migrations.

## 9. Security scanning (Trivy)

```bash
trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 <image>
```

Trivy inspects the OS packages of each image (Debian for the backend, Alpine for the frontend)
and the language packages installed in it (the Python wheels in the backend) against
vulnerability databases. `--exit-code 1` makes any HIGH or CRITICAL finding with an available
fix fail the job, and because the push step comes after the scan, a failing image is never
published. `--ignore-unfixed` keeps the gate actionable: findings with no upstream fix are
reported but cannot block a release.

**Result: both images are clean**, with zero fixable HIGH or CRITICAL findings. That is by design
rather than luck: both Dockerfiles upgrade the base image's OS packages at build time
(`apt-get upgrade` / `apk upgrade`), because base images routinely trail the distribution's
security fixes by days, and the Python dependencies are pinned to current releases. A clean scan
means no known, fixable, serious vulnerability at build time. It is not a guarantee of security,
which is why it sits alongside tests, non-root containers and least-privilege defaults.

Other controls: non-root containers · PostgreSQL password generated by Helm, never committed ·
`.env` and `terraform.tfvars` git-ignored · AWS credentials only from the environment.

## 10. Kubernetes + Helm

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install shelfwise ./helm/shelfwise -n shelfwise \
  --set backend.image.tag=<commit SHA> --set frontend.image.tag=<commit SHA> --wait

kubectl get pods,svc,ingress,hpa -n shelfwise
helm list -n shelfwise
```

**What the chart (`helm/shelfwise`) creates**

| Object | Details |
|--------|---------|
| Deployment `backend` | 2 replicas, startup + liveness `/health`, readiness `/ready`, non-root, requests and limits |
| Deployment `frontend` | 2 replicas, nginx serving the React build |
| Services (ClusterIP) | backend, frontend, PostgreSQL |
| HPA | backend 2 → 6 pods at 60% CPU · frontend 2 → 4 pods at 70% CPU |
| StatefulSet PostgreSQL | PersistentVolumeClaim (1Gi); password generated once, kept across upgrades |
| Ingress (`nginx`, `shelfwise.local`) | `/api`, `/docs`, `/openapi.json` → backend · `/` → frontend |
| ServiceMonitor | Prometheus scrapes `/metrics` on every backend pod |

## 11. Terraform: AWS VPC + EKS

| File | Contents |
|------|----------|
| `versions.tf` | terraform >= 1.5, AWS provider ~> 5.80 |
| `providers.tf` | region from a variable; credentials from the environment, never the repo |
| `variables.tf` | region (`ap-south-1`), CIDRs, Kubernetes version, node sizes |
| `vpc.tf` | VPC, IGW, **2 public + 2 private subnets** across 2 AZs, NAT gateway, route tables |
| `eks.tf` | IAM roles and policies, **EKS cluster** (Kubernetes 1.36), **managed node group** in the private subnets |
| `outputs.tf` | ids, cluster endpoint, and the `aws eks update-kubeconfig` command |
| `terraform.tfvars.example` | copy to `terraform.tfvars` (git-ignored) |

Subnets carry the `kubernetes.io/role/elb` and `internal-elb` tags so the AWS load balancer
controller can place load balancers for the Ingress. Worker nodes live in the private subnets and
reach the internet through the NAT gateway.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan -out=tfplan && terraform apply tfplan     # 22 resources
aws eks update-kubeconfig --region ap-south-1 --name shelfwise-eks
terraform destroy
```

> **How the recorded run was done.** The screenshots below come from a real run against AWS
> account `592050574278` in `ap-south-1` on 16 October 2026. `terraform apply` created all
> 22 resources: the VPC, four subnets, Internet and NAT gateways, route tables, the two IAM roles,
> the EKS 1.36 control plane and a managed node group of two `t3.medium` workers.
> `kubectl get nodes` reached the real cluster, and `terraform destroy` removed everything.
> The whole run, from the first `apply` call to the last `destroy` call, took 23 minutes and cost
> well under US$1; a US$1 AWS Budget was set up as a guardrail before the run.
>
> The Kubernetes version was moved from 1.31 to 1.36 before the run because 1.31 is now in EKS
> extended support, which bills the control plane at six times the standard rate.
>
> The application itself (Section 10) is deployed on a local minikube cluster to keep the cloud
> run short; on EKS the same Helm command applies after `aws eks update-kubeconfig`.

### Module 7 evidence

| Step | Screenshot |
|---|---|
| `terraform init`, `fmt -check`, `validate` | [m7-01](docs/screenshots/m7-01-terraform-init-validate.png) |
| `terraform plan -out=tfplan`, 22 to add | [m7-02](docs/screenshots/m7-02-terraform-plan.png) |
| `terraform apply tfplan`, 22 added | [m7-03](docs/screenshots/m7-03-terraform-apply.png) |
| VPC resource map: subnets, route tables, IGW, NAT | [m7-04](docs/screenshots/m7-04-aws-vpc-resource-map.png) |
| Subnets with CIDRs across two AZs | [m7-05](docs/screenshots/m7-05-aws-subnets.png) |
| NAT gateway, available | [m7-06](docs/screenshots/m7-06-aws-nat-gateway.png) |
| Elastic IP attached to the NAT gateway | [m7-07](docs/screenshots/m7-07-aws-elastic-ip.png) |
| IAM node role with the three worker policies | [m7-08](docs/screenshots/m7-08-aws-iam-node-role.png) |
| EKS cluster, active, Kubernetes 1.36 | [m7-09](docs/screenshots/m7-09-aws-eks-cluster.png) |
| EKS compute: managed node group, 2 nodes, active | [m7-10](docs/screenshots/m7-10-aws-eks-nodegroup.png) |
| EC2 instances backing the node group | [m7-11](docs/screenshots/m7-11-aws-ec2-instances.png) |
| `aws eks update-kubeconfig`, `kubectl get nodes`, system pods | [m7-12](docs/screenshots/m7-12-kubectl-get-nodes.png) |
| `terraform destroy`, 22 destroyed, then CLI checks showing nothing left | [m7-13](docs/screenshots/m7-13-terraform-destroy.png) |
| EKS console after destroy, no clusters | [m7-14](docs/screenshots/m7-14-aws-eks-after-destroy.png) |
| AWS Budget of US$1 set as the guardrail for the run | [m7-15](docs/screenshots/m7-15-aws-budget.png) |

## 12. Monitoring: Prometheus + Grafana

```bash
kubectl create secret generic grafana-admin -n monitoring \
  --from-literal=admin-user=admin --from-literal=admin-password="$(openssl rand -hex 12)"
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f monitoring/kube-prometheus-stack-values.yaml
kubectl apply -f monitoring/grafana-dashboard.yaml
```

* The backend exposes `/metrics` through `prometheus-fastapi-instrumentator`: request counts by
  method, handler and status class, and latency histograms.
* Prometheus discovers the backend pods through the chart's **ServiceMonitor**.
* The **"ShelfWise API"** Grafana dashboard is provisioned from a ConfigMap:

| Row | Panels |
|-----|--------|
| Golden signals | requests/second · p95 latency · 5xx error rate · backend pods available |
| Per endpoint | requests/second by endpoint · latency by endpoint (p50 / p95) |
| Health | responses by status class · backend CPU per pod (the HPA's input) |

![Grafana dashboard](docs/screenshots/m9-grafana-dashboard.png)

## 13. Autoscaling demo

```bash
kubectl get hpa -n shelfwise -w      # terminal 1
scripts/load-test.sh                 # terminal 2
```

Under the load generator the backend HPA scaled from **2 to 6 replicas** (its maximum) at 436% of
target CPU. See [HPA scaling](docs/screenshots/m8-hpa-scaling.png).

## 14. Troubleshooting labs

`troubleshooting/` holds three broken manifests, each run and fixed on the cluster:

| Lab | Symptom | Investigation | Fix |
|-----|---------|---------------|-----|
| [broken-image.yaml](troubleshooting/broken-image.yaml) | new pods `ErrImagePull` / `ImagePullBackOff`, old pods keep serving | the `Failed` event names the tag that was never pushed | `kubectl rollout undo` · [capture](docs/screenshots/troubleshoot-1-broken-image.png) |
| [broken-service.yaml](troubleshooting/broken-service.yaml) | Service has a ClusterIP but no endpoints, connections refused | compare the selector with `kubectl get pods --show-labels`: one-letter typo | patch the selector · [capture](docs/screenshots/troubleshoot-2-broken-service.png) |
| [broken-readiness.yaml](troubleshooting/broken-readiness.yaml) | new pod `Running` but `0/1`, rollout stalls | events show `Readiness probe failed: … statuscode: 404` on `/readyz`; pod IP missing from endpoints | `kubectl rollout undo` · [capture](docs/screenshots/troubleshoot-3-broken-readiness.png) |

## 15. Demo: commit to deployment

The last feature was added the way the demo runs: showing the running build in the UI
(`/api/info` plus the sidebar), committed and pushed as `0c9b52a`.

1. [Before](docs/screenshots/m10-before-deploy.png): the cluster runs the previous build and the sidebar has no build line.
2. The pipeline for `0c9b52a` tested it (12 tests), built and Trivy-scanned both images, pushed them as `:0c9b52a4c7…`, and deployed them to its own kind cluster.
3. [Deploy](docs/screenshots/m10-deploy-cli.png): `helm upgrade --install` with the new SHA rolls the pods; the deployment's image changes from `e3d3fcb` to `0c9b52a` and `/api/info` reports the new version.
4. [After](docs/screenshots/m10-deployment-updated.png): the same page through the Ingress now shows `build 0c9b52a`.

> **Gotcha:** Helm 4 uses server-side apply, so after a manual `kubectl rollout undo` (as in the
> troubleshooting labs) kubectl owns the image field and the next `helm upgrade` reports a
> field-manager conflict. `helm upgrade --force-conflicts` hands ownership back to Helm.

## 16. Design decisions

| Decision | Why |
|----------|-----|
| Own domain (library) instead of the TaskBoard reference | the capstone requires an original application; the DevOps architecture follows the course |
| `/health` does not touch the DB, `/ready` does | a DB outage should stop traffic (readiness), not restart healthy pods in a loop (liveness) |
| Migrations at container start with an advisory lock | no separate job to orchestrate; safe with N replicas starting together |
| Copy-count rules as DB check constraints | the invariant holds even if a bug slips past the Python validation |
| Image tag = commit SHA, never `latest` | immutable, traceable deployments |
| Push only after the Trivy gate | a vulnerable image is never published |
| Multi-arch images | amd64 for EKS nodes, arm64 for Apple silicon and Graviton |
| Deploy job on a throw-away kind cluster | every commit proves the chart installs and the app works through the Ingress |
| PostgreSQL as a StatefulSet in the cluster | simple classroom setup; in production a managed database such as Amazon RDS gives backups, Multi-AZ and patching |
| Generated DB password kept across upgrades | no credential is ever committed |

## 17. Grading evidence

| Module | What is here | Evidence |
|---|---|---|
| M1 Application | FastAPI `/health`, `/ready`, CRUD on `/api/books`, lending, stats; PostgreSQL via Alembic; React UI | [dashboard](docs/screenshots/m1-app-dashboard.png), [add book](docs/screenshots/m1-app-add-book.png), [mobile](docs/screenshots/m1-app-mobile.png), [Swagger](docs/screenshots/m1-api-swagger.png) |
| M2 Testing | 12 pytest cases over 8 endpoints, in-memory SQLite, `pytest.ini` + `conftest.py` | [pytest -v](docs/screenshots/m2-pytest.png) |
| M3 Git | public repo, one commit per step with descriptive messages, `.gitignore` | [commit history](docs/screenshots/m3-commit-history.png) |
| M4 Docker | non-root backend image, multi-stage frontend (node build, nginx runtime), compose | [compose up](docs/screenshots/m4-docker-compose-up.png) |
| M5 CI/CD | pytest, frontend build, both images, GHCR push tagged with the SHA, Helm deploy | [green run](docs/screenshots/m5-pipeline-success.png), [GHCR tags](docs/screenshots/m5-ghcr-packages.png), [packages](docs/screenshots/m5-ghcr-package-list.png) |
| M6 DevSecOps | Trivy on both images, `--exit-code 1` on fixable HIGH/CRITICAL | [Trivy output](docs/screenshots/m6-trivy-scan.png) |
| M7 Terraform | VPC, 2 public + 2 private subnets, NAT, EKS 1.36 + node group, real AWS run, `tfvars.example` | [plan](docs/screenshots/m7-02-terraform-plan.png), [apply](docs/screenshots/m7-03-terraform-apply.png), [VPC](docs/screenshots/m7-04-aws-vpc-resource-map.png), [EKS](docs/screenshots/m7-09-aws-eks-cluster.png), [nodes](docs/screenshots/m7-12-kubectl-get-nodes.png), [destroy](docs/screenshots/m7-13-terraform-destroy.png), [all 15](#module-7-evidence) |
| M8 Kubernetes + Helm | namespace, chart, 2+ replicas each, ClusterIP services, Ingress `/` and `/api`, HPA | [helm](docs/screenshots/m8-helm-upgrade-install.png), [pods/svc](docs/screenshots/m8-pods-svc-ingress.png), [via Ingress](docs/screenshots/m8-app-via-ingress.png), [HPA](docs/screenshots/m8-hpa-scaling.png), [labs](docs/screenshots/troubleshoot-1-broken-image.png) |
| M9 Observability | `/metrics`, Prometheus scraping via ServiceMonitor, Grafana dashboard | [metrics](docs/screenshots/m9-metrics-endpoint.png), [targets UP](docs/screenshots/m9-prometheus-targets.png), [Grafana](docs/screenshots/m9-grafana-dashboard.png) |
| M10 Docs + demo | this README, the [presentation slides](docs/shelfwise-capstone-presentation.pdf) and a [narrated video walkthrough](docs/shelfwise-capstone-walkthrough.mp4); commit, pipeline, deployment update | [before](docs/screenshots/m10-before-deploy.png), [deploy](docs/screenshots/m10-deploy-cli.png), [after](docs/screenshots/m10-deployment-updated.png) |
