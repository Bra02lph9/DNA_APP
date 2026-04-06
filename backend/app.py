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
    analyze_folder_files,
    analyze_sequence_by_type_adaptive,
)
from analysis.utils import load_fasta_folder

from tasks.analysis_tasks import (
    run_sequence_analysis,
    run_folder_analysis,
    run_global_coding_orfs_store,
    run_chunked_promoters_store,
    run_chunked_sd_store,
    run_chunked_terminators_store,
    assemble_and_rank_from_storage,
)
from tasks.celery_app import celery_app

from db.mongo import ensure_indexes
from db.analysis_repository import (
    create_analysis,
    get_analysis,
    fetch_module_results,
    count_module_results,
)


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

ensure_indexes()


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


def get_positive_int(value, default: int, field_name: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


def get_limit(value, default: int = 20, max_limit: int = 200) -> int:
    limit = get_positive_int(value, default, "limit")
    if limit == 0:
        return default
    return min(limit, max_limit)


def get_sort_direction(value: str | None) -> int:
    if not value:
        return 1
    value = value.lower().strip()
    if value in {"asc", "1", "up"}:
        return 1
    if value in {"desc", "-1", "down"}:
        return -1
    raise ValueError("sort_direction must be 'asc' or 'desc'")


def normalize_result_module(module: str) -> str:
    mapping = {
        "coding_orfs": "coding_orfs",
        "promoters": "promoters",
        "shine_dalgarno": "shine_dalgarno",
        "shine_dalgarno_sites": "shine_dalgarno",
        "sd": "shine_dalgarno",
        "terminators": "terminators",
        "ranked_coding_orfs": "ranked_coding_orfs",
    }
    normalized = mapping.get(module)
    if not normalized:
        raise ValueError(
            "module must be one of: coding_orfs, promoters, shine_dalgarno, terminators, ranked_coding_orfs"
        )
    return normalized


def iso_or_none(value):
    return value.isoformat() if value else None


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
        result = analyze_sequence_by_type_adaptive(
            sequence=sequence,
            analysis_type="ranked_coding_orfs",
            min_aa=min_aa,
        )
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
        result = analyze_sequence_by_type_adaptive(
            sequence=sequence,
            analysis_type="all",
            min_aa=min_aa,
        )
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


@app.route("/analyses/run", methods=["POST"])
def run_stored_analysis_route():
    data = get_json_data()

    try:
        sequence = data.get("sequence", "")
        if not sequence:
            return error_response("'sequence' is required")

        min_aa = get_min_aa(data)
        chunk_size = get_positive_int(data.get("chunk_size"), 50_000, "chunk_size")
        overlap = get_positive_int(data.get("overlap"), 1_000, "overlap")

        if chunk_size <= 0:
            return error_response("chunk_size must be > 0")

        analysis_id = create_analysis(
            sequence_length=len(sequence),
            pipeline="stored_chunked_ranking",
            parameters={
                "min_aa": min_aa,
                "chunk_size": chunk_size,
                "overlap": overlap,
            },
        )

        coding_task = run_global_coding_orfs_store.delay(
            analysis_id=analysis_id,
            sequence=sequence,
            min_aa=min_aa,
        )
        promoters_task = run_chunked_promoters_store.delay(
            analysis_id=analysis_id,
            sequence=sequence,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        sd_task = run_chunked_sd_store.delay(
            analysis_id=analysis_id,
            sequence=sequence,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        terminators_task = run_chunked_terminators_store.delay(
            analysis_id=analysis_id,
            sequence=sequence,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        return jsonify(
            {
                "analysis_id": analysis_id,
                "status": "running",
                "message": "Stored analysis started",
                "tasks": {
                    "coding_orfs": coding_task.id,
                    "promoters": promoters_task.id,
                    "shine_dalgarno": sd_task.id,
                    "terminators": terminators_task.id,
                },
            }
        ), 202

    except Exception as e:
        print("RUN STORED ANALYSIS ERROR:", e)
        return error_response(str(e), 500)


@app.route("/analyses/<analysis_id>/assemble", methods=["POST"])
def assemble_analysis_route(analysis_id):
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return error_response("analysis not found", 404)

        modules = analysis.get("modules", {})
        required = ["coding_orfs", "promoters", "shine_dalgarno", "terminators"]
        not_ready = [name for name in required if modules.get(name) != "done"]

        if not_ready:
            return error_response(
                f"Cannot assemble yet. Modules not finished: {', '.join(not_ready)}",
                409,
            )

        task = assemble_and_rank_from_storage.delay(analysis_id=analysis_id)

        return jsonify(
            {
                "analysis_id": analysis_id,
                "status": "queued",
                "task_id": task.id,
                "message": "Ranking assembly started",
            }
        ), 202

    except Exception as e:
        print("ASSEMBLE ANALYSIS ERROR:", e)
        return error_response(str(e), 500)


@app.route("/analyses/<analysis_id>", methods=["GET"])
def get_analysis_route(analysis_id):
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return error_response("analysis not found", 404)

        analysis["_id"] = str(analysis["_id"])
        if "created_at" in analysis:
            analysis["created_at"] = iso_or_none(analysis.get("created_at"))
        if "updated_at" in analysis:
            analysis["updated_at"] = iso_or_none(analysis.get("updated_at"))

        return jsonify(analysis)

    except Exception as e:
        print("GET ANALYSIS ERROR:", e)
        return error_response(str(e), 500)


@app.route("/analyses/<analysis_id>/summary", methods=["GET"])
def get_analysis_summary_route(analysis_id):
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return error_response("analysis not found", 404)

        return jsonify(
            {
                "analysis_id": analysis_id,
                "status": analysis.get("status"),
                "pipeline": analysis.get("pipeline"),
                "sequence_length": analysis.get("sequence_length"),
                "modules": analysis.get("modules", {}),
                "summary": analysis.get("summary", {}),
                "errors": analysis.get("errors", []),
                "created_at": iso_or_none(analysis.get("created_at")),
                "updated_at": iso_or_none(analysis.get("updated_at")),
            }
        )

    except Exception as e:
        print("GET ANALYSIS SUMMARY ERROR:", e)
        return error_response(str(e), 500)


@app.route("/analyses/<analysis_id>/results", methods=["GET"])
def get_analysis_results_route(analysis_id):
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return error_response("analysis not found", 404)

        module = normalize_result_module(request.args.get("module", "").strip())
        kind = request.args.get("kind", "final").strip() or "final"
        limit = get_limit(request.args.get("limit"), default=20, max_limit=200)
        skip = get_positive_int(request.args.get("skip"), 0, "skip")
        sort_field = request.args.get("sort_field")
        sort_direction = get_sort_direction(request.args.get("sort_direction"))

        results = fetch_module_results(
            analysis_id=analysis_id,
            module=module,
            kind=kind,
            sort_field=sort_field,
            sort_direction=sort_direction,
            limit=limit,
            skip=skip,
        )

        total = count_module_results(
            analysis_id=analysis_id,
            module=module,
            kind=kind,
        )

        return jsonify(
            {
                "analysis_id": analysis_id,
                "module": module,
                "kind": kind,
                "total": total,
                "skip": skip,
                "limit": limit,
                "returned": len(results),
                "results": results,
            }
        )

    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        print("GET ANALYSIS RESULTS ERROR:", e)
        return error_response(str(e), 500)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "DNA backend is running"}), 200


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
