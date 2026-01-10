# Microgrid VPS Prototype v4

This repository contains a proof‑of‑concept implementation of a cloud‑hosted
control plane and multiple edge controllers for microgrids.  The goal of the
prototype is to demonstrate how sites can be provisioned automatically,
configured centrally and still run locally autonomous control loops.  It
borrows concepts from commercial solutions such as ComAp and Eniris but keeps
the code simple and hackable for experimentation.

## What’s new in v4

This version introduces a provisioning workflow that allows you to deploy
edge controllers without manually editing configuration files.  A cloud API
issues enrollment tokens tied to a site.  When a new edge controller comes
online it uses the token to register itself with the cloud, obtain its
`site_id` and the desired configuration.  This makes it easy to plug a
controller into a network and have it automatically appear in the portal.

Other notable changes:

* Separation of cloud and edge stacks into independent compose files (`docker‑compose.cloud.yml` and
  `docker‑compose.edge.yml`).  You can run the cloud platform on a VPS or
  container orchestration system, and run each edge stack on a Cerbo GX or
  BeagleBone.
* Ansible playbook (`deploy/edge_deploy.yml`) for automating deployment of
  the edge stack over SSH.  You supply the host, username and password
  (or key) and the playbook installs Docker, copies the edge compose file
  and spins up the services.  This is how you can turn a factory‑fresh
  device into a registered controller in a single command.
* A simple firmware update stub in the Ansible playbook.  It copies a
  firmware image to the device and runs a script to apply it.  You need to
  provide the actual firmware file and update logic – the playbook is a
  placeholder and includes safety checks to avoid accidental bricking.

## Quick start

### Running the demo locally

The default `docker‑compose.yml` spins up a cloud service and three edge
controllers on your machine.  Each edge controller runs in its own
container with isolated Redis so that it simulates separate devices.  To
bring the stack up:

```bash
docker compose up --build
```

Visit `http://localhost:8080` for the cloud UI.  Status endpoints for the
three simulated edges are exposed at:

* http://localhost:8081/status – edge 1
* http://localhost:8082/status – edge 2
* http://localhost:8083/status – edge 3

### Cloud provisioning

1. Create a site in the cloud by POSTing a desired configuration.  For
   example:

   ```bash
   curl -X POST http://localhost:8080/api/sites/site123/desired-config \
        -H 'Content-Type: application/json' \
        --data-binary @./sample_configs/demo_site.json
   ```

2. Generate an enrollment token for the site:

   ```bash
   curl -X POST http://localhost:8080/api/sites/site123/enrollment-token
   ```

3. Start an edge controller and set the `EDGE_TOKEN` environment variable
   to the token returned by the previous step.  The edge will call back
   to the cloud, register itself to the site and pull down the
   configuration.

### Deploying an edge to a Cerbo or BeagleBone

The `deploy/edge_deploy.yml` playbook installs Docker on your device,
copies the edge stack and starts it.  You need to set the variables
`edge_id`, `site_id`, `cloud_url`, and `edge_token` when invoking the
playbook.  A sample invocation using a hosts inventory might look like:

```bash
ansible-playbook -i deploy/inventory.ini deploy/edge_deploy.yml \
  -e edge_id=edge01 \
  -e site_id=site123 \
  -e cloud_url=https://api.yourdomain.com \
  -e edge_token=<token from cloud>
```

The playbook also contains a commented out section that demonstrates how
you might upload and apply a firmware image.  Because overwriting the
firmware of a Cerbo GX is risky, the default behaviour is to skip this
step.  If you decide to use it, make sure you supply a valid image and
fully understand the consequences.

## Structure

```
microgrid-vps-prototype-v4/
│   README.md                # this file
│   docker-compose.yml       # convenience file for local multi-edge demos
│   docker-compose.cloud.yml # compose file for the cloud stack
│   docker-compose.edge.yml  # compose file for a single edge controller
│
├── cloud/
│   ├── app.py               # FastAPI application implementing the cloud API
│   └── requirements.txt     # dependencies for the cloud
│
├── edge/
│   ├── app.py               # minimal control loop and registration logic
│   └── requirements.txt     # dependencies for the edge
│
├── deploy/
│   ├── edge_deploy.yml      # Ansible playbook for remote deployment
│   └── inventory.ini.example# sample hosts inventory
│
└── sample_configs/
    └── demo_site.json       # example desired configuration
```

This repository is **not** meant to be a production microgrid controller.
It is a teaching and prototyping tool.  Contributions and pull requests
are welcome.
