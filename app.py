import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from dotenv import load_dotenv
from flask import Flask, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

SERVICE_NAME = "volunteer-service"
HOSTNAME = os.getenv("HOSTNAME", os.uname().nodename)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("AWS_DYNAMODB_TABLE", "fase_5")


def generate_tid():
    return str(time.time_ns())


def log_operation(tid, operation):
    log.info(
        "%s | %s | %s | %s | %s",
        datetime.now(timezone.utc).isoformat(),
        SERVICE_NAME,
        HOSTNAME,
        tid,
        operation,
    )


if not DYNAMODB_TABLE:
    log.critical("Erro: AWS_DYNAMODB_TABLE não definida.")
    sys.exit(1)

try:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    log.info("Conectado à tabela DynamoDB: %s", DYNAMODB_TABLE)
except Exception as exc:
    log.critical("Falha ao conectar no DynamoDB: %s", exc)
    sys.exit(1)


@app.route("/health")
def health():
    tid = generate_tid()

    log_operation(
        tid,
        "GET /health started",
    )

    response = {
        "status": "ok",
        "service": SERVICE_NAME,
    }

    log_operation(
        tid,
        "health.ok",
    )

    return jsonify(response)


@app.route("/volunteers", methods=["POST"])
def register_volunteer():
    start = time.time()
    tid = generate_tid()

    log_operation(
        tid,
        f"{request.method} {request.path} started",
    )

    log_operation(
        tid,
        (
            f"request method={request.method} "
            f"path={request.path} "
            f"remote={request.remote_addr}"
        ),
    )

    data = request.get_json()

    if not data or not all(
        key in data for key in ("name", "email", "ngo_id")
    ):
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    volunteer_id = str(uuid.uuid4())

    item = {
        "volunteer_id": volunteer_id,
        "name": data["name"],
        "email": data["email"],
        "ngo_id": int(data["ngo_id"]),
        "registered_at": str(int(time.time())),
    }

    log_operation(
        tid,
        (
            f"Inserting volunteer "
            f"ngo_id={item['ngo_id']} "
            f"email={item['email']}"
        ),
    )

    try:
        table.put_item(Item=item)

        log_operation(
            tid,
            (
                f"volunteer.created "
                f"id={volunteer_id} "
                f"duration_ms={(time.time() - start) * 1000:.0f}"
            ),
        )

        return jsonify(item), 201

    except Exception as exc:
        log_operation(
            tid,
            f"Error inserting volunteer: {exc}",
        )

        log.error(
            "Erro ao salvar voluntário no DynamoDB: %s",
            exc,
        )

        return jsonify(
            {"error": "Erro interno ao processar dados"}
        ), 500


@app.route("/volunteers/<int:ngo_id>", methods=["GET"])
def get_volunteers_by_ngo(ngo_id):
    start = time.time()
    tid = generate_tid()

    log_operation(
        tid,
        f"{request.method} {request.path} started",
    )

    log_operation(
        tid,
        (
            f"request method={request.method} "
            f"path={request.path} "
            f"remote={request.remote_addr}"
        ),
    )

    try:
        response = table.scan(
            FilterExpression=Attr("ngo_id").eq(ngo_id),
        )

        items = response.get("Items", [])

        log_operation(
            tid,
            (
                f"volunteers.list "
                f"ngo_id={ngo_id} "
                f"count={len(items)} "
                f"duration_ms={(time.time() - start) * 1000:.0f}"
            ),
        )

        return jsonify(items), 200

    except Exception as exc:
        log_operation(
            tid,
            f"Error listing volunteers: {exc}",
        )

        log.error(
            "Erro ao buscar dados no DynamoDB: %s",
            exc,
        )

        return jsonify({"error": "Erro interno"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8083"))
    app.run(
        host="0.0.0.0",
        port=port,
    )
