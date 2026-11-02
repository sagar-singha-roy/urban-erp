from urban_common.app import create_service_app

from app.api.v1.properties import router as properties_router

app = create_service_app(
    "PTX",
    "Property Tax & Revenue Management",
    routers=[properties_router],
    publishes_events=True,
)
