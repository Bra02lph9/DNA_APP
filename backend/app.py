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


def handle_single_or_folder(
    data: dict,
    single_handler,
    folder_analysis_type: str,
    single_response_transform=None,
    folder_response_transform=None,
):
    mode = data.get("mode", "single")

    if mode == "folder":
        files = data.get("files", [])
        if not isinstance(files, list):
            return error_response("'files' must be a list")

        results = analyze_folder_files(files, analysis_type=folder_analysis_type)

        if folder_response_transform:
            results = folder_response_transform(results)

        return jsonify(results)

    sequence = data.get("sequence", "")
    result = single_handler(sequence)

    if single_response_transform:
        result = single_response_transform(result)

    return jsonify(result)


@app.route("/analyze/folder-path", methods=["POST"])
def analyze_folder_path_route():
    data = get_json_data()
    folder_path = data.get("folder_path", "").strip()

    if not folder_path:
        return error_response("folder_path is required")

    try:
        folder_sequences = load_fasta_folder(folder_path)
        output = []

        for item in folder_sequences:
            result = analyze_all(item["sequence"])
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
        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(files, analysis_type="coding_orfs")
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_coding_orfs(sequence, min_aa=30)
        return jsonify({
            "coding_orfs": result["coding_orfs"],
            "best_coding_orf": result["best_coding_orf"],
        })

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
        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(files, analysis_type="ranked_coding_orfs")
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_ranked_coding_orfs(sequence)
        return jsonify(result)

    except Exception as e:
        print("RANKED CODING ORFS ERROR:", e)
        return error_response(str(e))


@app.route("/analyze/all", methods=["POST"])
def analyze_all_route():
    data = get_json_data()
    mode = data.get("mode", "single")

    try:
        if mode == "folder":
            files = data.get("files", [])
            if not isinstance(files, list):
                return error_response("'files' must be a list")

            output = analyze_folder_files(files, analysis_type="all")
            return jsonify(output)

        sequence = data.get("sequence", "")
        result = analyze_all(sequence)
        return jsonify(result)

    except Exception as e:
        print("ALL ERROR:", e)
        return error_response(str(e))


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "DNA backend is running"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
