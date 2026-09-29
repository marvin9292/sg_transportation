DOMAIN = "sg_transportation"

SCAN_INTERVAL_SECONDS = 15

CONF_ACCOUNT_KEY = "account_key"

SUBENTRY_TYPE_BUS_SERVICE = "bus_service"
SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS = "train_service_alerts"

SUBENTRY_CONF_BUS_STOP_CODE = "bus_stop_code"
SUBENTRY_CONF_DESCRIPTION = "description"
SUBENTRY_CONF_SERVICE_NO = "service_no"

BUS_TYPE_MAP = {
    "SD": "Single",
    "DD": "Double",
    "BD": "Bendy",
}

BUS_LOAD_MAP = {
    "SEA": "Seats Available",
    "SDA": "Standing Available",
    "LSD": "Limited Standing",
}

TRAIN_ALERTS_API_URL = "https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts"

TRAIN_LINE_NAME_MAP = {
    "BPL": "Bukit Panjang LRT",
    "CGL": "Changi Extension",
    "CCL": "Circle Line",
    "CEL": "Circle Line Extension",
    "DTL": "Downtown Line",
    "EWL": "East West Line",
    "NEL": "North East Line",
    "NSL": "North South Line",
    "PWL": "Punggol LRT West Loop",
    "PEL": "Punggol LRT East Loop",
    "SEL": "Sengkang LRT East Loop",
    "SWL": "Sengkang LRT West Loop",
}

TRAIN_LINE_CODES = list(TRAIN_LINE_NAME_MAP.keys())
