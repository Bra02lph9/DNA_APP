from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS

from analysis.analysis_service import (
    analyze_all,
    analyze_orfs,
    analyze_promoters,
    analyze_terminators,
    analyze_shine_dalgarno,
    analyze_coding_orfs,
    analyze_ranked_coding_orfs,
    analyze_folder_files,
)
from analysis.utils import load_fasta_folder
from tasks.analysis_tasks import run_sequence_analysis, run_folder_analysis
from tasks.celery_app import celery_app


app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://dna-app-2.onrender.com",
                "http://localhost:5173",
                "https://dna-app-seven.vercel.app",
            ]
        }
    },
)


def get_json_data() -> dict:
    data = request.get_json(silent=True)
    return data or {}


def error_response(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def get_min_aa(data: dict) -> int:
    min_aa = data.get("min_aa", 30)
    try:
        min_aa = int(min_aa)
    except (TypeError, ValueError):
        raise ValueError("min_aa must be an integer")

    if min_aa <= 0:
        raise ValueError("min_aa must be > 0")

    return min_aa


def handle_single_or_folder(
    data: dict,
    single_handler,
    folder_analysis_type: str,
    single_response_transform=None,
    folder_response_transform=None,
    supports_min_aa: bool = False,
):
    mode = data.get("mode", "single")
    min_aa = get_min_aa(data) if supports_min_aa else None

    if mode == "folder":
        files = data.get("files", [])
        if not isinstance(files, list):
            return error_response("'files' must be a list")

        kwargs = {"analysis_type": folder_analysis_type}
        if supports_min_aa:
            kwargs["min_aa"] = min_aa

        results = analyze_folder_files(files, **kwargs)

        if folder_response_transform:
            results = folder_response_transform(results)

        return jsonify(results)

    sequence = data.get("sequence", "")

    if supports_min_aa:
        result = single_handler(sequence, min_aa=min_aa)
    else:
        result = single_handler(sequence)

    if single_response_transform:
        result = single_response_transform(result)

    return jsonify(result)


@app.route("/analyze/folder-path", methods=["POST"])
def analyze_folder_path_route():
    data = get_json_data()
    folder_path = data.get("folder_path", "").strip()
    min_aa = data.get("min_aa", 30)

    if not folder_path:
        return error_response("folder_path is required")

    try:
        min_aa = int(min_aa)
        folder_sequences = load_fasta_folder(folder_path)
        output = []

        for item in folder_sequences:
            result = analyze_all(item["sequence"], min_aa=min_aa)
            result["file"] = item["file"]
            result["header"] = item["header"]
            output.append(result)

        return jsonify(output)

    except Exception as e:
        print("FOLDER PATH ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/coding-orfs", methods=["POST"])
def coding_orfs_route():
    data = get_json_data()
    mode = data.get("mode", "single")

    try:
        min_aa = get_min_aa(data)

        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(
                files,
                analysis_type="coding_orfs",
                min_aa=min_aa,
            )
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_coding_orfs(sequence, min_aa=min_aa)

        return jsonify(
            {
                "coding_orfs": result["coding_orfs"],
                "best_coding_orf": result["best_coding_orf"],
            }
        )

    except Exception as e:
        print("CODING ORFS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/orfs", methods=["POST"])
def analyze_orfs_route():
    data = get_json_data()

    try:
        return handle_single_or_folder(
            data=data,
            single_handler=analyze_orfs,
            folder_analysis_type="orfs",
            single_response_transform=lambda result: result["orfs"],
        )

    except Exception as e:
        print("ORFS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/promoters", methods=["POST"])
def analyze_promoters_route():
    data = get_json_data()

    try:
        return handle_single_or_folder(
            data=data,
            single_handler=analyze_promoters,
            folder_analysis_type="promoters",
            single_response_transform=lambda result: result["promoters"],
            folder_response_transform=lambda results: [
                {
                    "file": item["file"],
                    "length": item["length"],
                    "promoters": item["promoters"],
                }
                for item in results
            ],
        )

    except Exception as e:
        print("PROMOTERS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/terminators", methods=["POST"])
def analyze_terminators_route():
    data = get_json_data()

    try:
        return handle_single_or_folder(
            data=data,
            single_handler=analyze_terminators,
            folder_analysis_type="terminators",
            single_response_transform=lambda result: {
                "terminators": result["terminators"]
            },
            folder_response_transform=lambda results: [
                {
                    "file": item["file"],
                    "length": item["length"],
                    "terminators": item["terminators"],
                }
                for item in results
            ],
        )

    except Exception as e:
        print("TERMINATORS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/shine-dalgarno", methods=["POST"])
def analyze_sd_route():
    data = get_json_data()

    try:
        return handle_single_or_folder(
            data=data,
            single_handler=analyze_shine_dalgarno,
            folder_analysis_type="shine_dalgarno",
            single_response_transform=lambda result: {
                "shine_dalgarno": result["shine_dalgarno"]
            },
            folder_response_transform=lambda results: [
                {
                    "file": item["file"],
                    "length": item["length"],
                    "shine_dalgarno": item["shine_dalgarno"],
                }
                for item in results
            ],
        )

    except Exception as e:
        print("SHINE-DALGARNO ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/ranked-coding-orfs", methods=["POST"])
def analyze_ranked_coding_orfs_route():
    data = get_json_data()
    mode = data.get("mode", "single")

    try:
        min_aa = get_min_aa(data)

        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(
                files,
                analysis_type="ranked_coding_orfs",
                min_aa=min_aa,
            )
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_ranked_coding_orfs(sequence, min_aa=min_aa)
        return jsonify(result)

    except Exception as e:
        print("RANKED CODING ORFS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/all", methods=["POST"])
def analyze_all_route():
    data = get_json_data()
    mode = data.get("mode", "single")

    try:
        min_aa = get_min_aa(data)

        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(
                files,
                analysis_type="all",
                min_aa=min_aa,
            )
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_all(sequence, min_aa=min_aa)
        return jsonify(result)

    except Exception as e:
        print("ALL ERROR:", e)
        return error_response(str(e))


@app.route("/tasks/analyze", methods=["POST"])
def create_analysis_task():
    data = get_json_data()
    mode = data.get("mode", "single")
    analysis_type = data.get("analysis_type", "all")

    try:
        min_aa = get_min_aa(data)

        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list) or not files:
                return error_response("'files' must be a non-empty list")

            task = run_folder_analysis.delay(
                files=files,
                analysis_type=analysis_type,
                min_aa=min_aa,
            )
        else:
            sequence = data.get("sequence", "")
            if not sequence:
                return error_response("'sequence' is required")

            task = run_sequence_analysis.delay(
                sequence=sequence,
                analysis_type=analysis_type,
                min_aa=min_aa,
            )

        return jsonify(
            {
                "task_id": task.id,
                "status": "queued",
                "analysis_type": analysis_type,
            }
        ), 202

    except Exception as e:
        print("TASK CREATE ERROR:", e)
        return error_response(str(e))


@app.route("/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    try:
        task_result = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task_result.status,
        }

        if task_result.status == "SUCCESS":
            response["result"] = task_result.result
        elif task_result.status == "FAILURE":
            response["error"] = str(task_result.result)

        return jsonify(response)

    except Exception as e:
        print("TASK STATUS ERROR:", e)
        return error_response(str(e))


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "DNA backend is running"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
