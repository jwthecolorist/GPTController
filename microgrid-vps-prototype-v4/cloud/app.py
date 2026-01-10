"""
Cloud API for the microgrid VPS prototype.

This FastAPI application exposes endpoints for:

* Storing and retrieving a site's desired configuration
* Issuing enrollment tokens tied to a site
* Registering an edge controller via a token
* Fetching an edge's desired configuration after registration

All data is stored in process memory.  In a production implementation you
would back these dictionaries with a database.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import uuid

app = FastAPI(title="Microgrid Cloud API", version="0.4.0")

# Allow all origins during development so the browser UI can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory data stores.  In a real deployment these would be persistent.
sites: Dict[str, Dict] = {}
enrollment_tokens: Dict[str, str] = {}
edges: Dict[str, Dict] = {}


class DesiredConfig(BaseModel):
    """The desired configuration posted by the user.

    We accept any JSON payload here.  Pydantic will treat it as a dict.
    """
    __root__: Dict


class RegisterRequest(BaseModel):
    edge_id: str
    token: str


@app.get("/health")
def health() -> Dict[str, str]:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/api/sites/{site_id}/desired-config")
def set_desired_config(site_id: str, config: DesiredConfig) -> Dict[str, str]:
    """Persist the desired configuration for a site.

    This will overwrite any existing configuration for the site.
    """
    sites[site_id] = config.__root__
    return {"status": "saved"}


@app.get("/api/sites/{site_id}/desired-config")
def get_desired_config(site_id: str) -> Dict:
    """Return the desired configuration for a site."""
    if site_id not in sites:
        raise HTTPException(status_code=404, detail="site not found")
    return sites[site_id]


@app.post("/api/sites/{site_id}/enrollment-token")
def generate_token(site_id: str) -> Dict[str, str]:
    """Generate an enrollment token for a site.

    Tokens are single use.  When an edge registers with this token
    it will be removed from the token store.
    """
    # Ensure the site exists before generating a token
    if site_id not in sites:
        raise HTTPException(status_code=404, detail="site not found")
    # Generate a random token and map it to the site
    token = uuid.uuid4().hex
    enrollment_tokens[token] = site_id
    return {"token": token}


@app.post("/api/edge/register")
def register_edge(req: RegisterRequest) -> Dict[str, str]:
    """Register an edge controller using an enrollment token.

    The request must include an `edge_id` (a unique identifier for the
    controller) and a valid `token` obtained from the cloud for a
    particular site.  On success this endpoint returns the site_id so
    that the edge knows which desired configuration to pull.
    """
    # Validate token
    token = req.token
    edge_id = req.edge_id
    if token not in enrollment_tokens:
        raise HTTPException(status_code=400, detail="invalid or expired token")
    site_id = enrollment_tokens.pop(token)
    # Register the edge to the site
    edges[edge_id] = {"site_id": site_id, "edge_id": edge_id}
    return {"site_id": site_id}


@app.get("/api/edges/{edge_id}/desired-config")
def get_edge_config(edge_id: str) -> Dict:
    """Return the desired configuration for an edge.

    The edge must be registered; otherwise this returns 404.
    """
    if edge_id not in edges:
        raise HTTPException(status_code=404, detail="edge not registered")
    site_id = edges[edge_id]["site_id"]
    if site_id not in sites:
        raise HTTPException(status_code=404, detail="site not found")
    return sites[site_id]


@app.get("/api/edges")
def list_edges() -> Dict[str, List[Dict[str, str]]]:
    """List all registered edges and the sites they belong to."""
    return {"edges": list(edges.values())}
