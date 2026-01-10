"""
Edge controller for the microgrid VPS prototype.

This FastAPI application simulates a very small portion of a microgrid
controller.  It demonstrates how an edge device can:

* Register with the cloud using an enrollment token
* Obtain its site identifier and desired configuration
* Expose a simple status endpoint that reports whether it is registered
  and the current configuration
* Provide a dummy point API for monitoring

The edge is intentionally minimal – it does not implement the complex
control loops found in a real DER controller.  However, it shows the
skeleton of how you would plug in registration and configuration logic.
"""

import os
import asyncio
import httpx
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional


class EdgeState:
    """Holds the current registration and configuration state for the edge."""
    def __init__(self, edge_id: str, cloud_url: str, token: Optional[str]):
        self.edge_id = edge_id
        self.cloud_url = cloud_url.rstrip("/")
        self.token = token
        self.site_id: Optional[str] = None
        self.registered: bool = False
        self.config: Optional[Dict[str, Any]] = None

    async def register_with_cloud(self) -> None:
        """Attempt to register with the cloud using the token.

        If registration succeeds, this sets `site_id` and clears the token.
        """
        if not self.token:
            # No token provided; cannot register automatically.
            return
        url = f"{self.cloud_url}/api/edge/register"
        payload = {"edge_id": self.edge_id, "token": self.token}
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
            except httpx.HTTPError:
                # Failed to register; do nothing.  We'll retry later.
                return
            data = resp.json()
            self.site_id = data.get("site_id")
            # Registration complete – clear the token so we don't retry
            self.token = None
            self.registered = True

    async def refresh_config(self) -> None:
        """Fetch the desired configuration from the cloud, if registered."""
        if not self.registered or not self.site_id:
            return
        url = f"{self.cloud_url}/api/edges/{self.edge_id}/desired-config"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=10.0)
                resp.raise_for_status()
            except httpx.HTTPError:
                return
            self.config = resp.json()

    async def run_background_tasks(self) -> None:
        """Main background loop for registration and configuration refresh."""
        # Try to register on startup if we have a token
        if self.token:
            await self.register_with_cloud()
        # Always attempt to refresh config periodically
        while True:
            # If not registered and we have a token, retry registration
            if not self.registered and self.token:
                await self.register_with_cloud()
            # If registered, fetch the config
            await self.refresh_config()
            await asyncio.sleep(15)  # poll every 15 seconds


# Read environment variables
EDGE_ID = os.getenv("EDGE_ID", "edge-1")
CLOUD_URL = os.getenv("CLOUD_URL", "http://cloud-api:8080")
EDGE_TOKEN = os.getenv("EDGE_TOKEN")

# Initialise state
state = EdgeState(edge_id=EDGE_ID, cloud_url=CLOUD_URL, token=EDGE_TOKEN)

# Create app
app = FastAPI(title=f"Edge Controller {EDGE_ID}", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Launch the background task for registration and config refresh."""
    asyncio.create_task(state.run_background_tasks())


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> Dict[str, Any]:
    """Return registration and config status."""
    return {
        "edge_id": state.edge_id,
        "registered": state.registered,
        "site_id": state.site_id,
        "config": state.config,
    }


@app.get("/points")
def points() -> Dict[str, float]:
    """Return a set of dummy measurement points for demonstration."""
    # Generate random values to simulate changing measurements
    return {
        "pcc_active_power_kw": round(random.uniform(-5.0, 5.0), 2),
        "bess_soc_pct": round(random.uniform(20, 80), 1),
        "pv_power_kw": round(random.uniform(0, 10.0), 2),
    }
