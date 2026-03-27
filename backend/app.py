from flask import Flask, request, jsonify
from flask_cors import CORS

from analysis.orf_finder import find_all_orfs
from analysis.promoters import find_promoters
from analysis.terminators import find_rho_independent_terminators
from analysis.shine_dalgarno import find_shine_dalgarno_sites
from analysis.coding_orfs import (find_coding_orfs, choose_best_coding_orf,
                                  coding_orfs_to_dicts, coding_orf_to_dict)
from analysis.coding_orf_ranker import (
    rank_coding_orfs,
    choose_best_ranked_coding_orf,
)
from analysis.utils import validate_dna, load_fasta_folder


app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://dna-app-2.onrender.com",
        "http://localhost:5173"
    ]}}
)


def clean_sequence(sequence: str) -> str:
    return sequence.upper().replace("\n", "").replace(" ", "").replace("\r", "")


def orf_to_dict(orf):
    return {
        "strand": orf.strand,
        "frame": orf.frame,
        "start": orf.start,
        "end": orf.end,
        "length_nt": orf.length_nt,
        "sequence": orf.sequence
    }


def promoter_to_dict(p):
    return {
        "strand": p.strand,
        "box35_start": p.box35_start,
        "box35_end": p.box35_end,
        "box35_seq": p.box35_seq,
        "box35_mismatches": p.box35_mismatches,

        "box10_start": p.box10_start,
        "box10_end": p.box10_end,
        "box10_seq": p.box10_seq,
        "box10_mismatches": p.box10_mismatches,
        "spacing": p.spacing,
        "spacer_seq": p.spacer_seq,
        "spacer_at_fraction": p.spacer_at_fraction,
        "score": p.score,
    }


def terminator_to_dict(t):
    return {
        "strand": t.strand,
        "stem_left_start": t.stem_left_start,
        "stem_left_end": t.stem_left_end,
        "stem_left_seq": t.stem_left_seq,
        "loop_seq": t.loop_seq,
        "stem_right_start": t.stem_right_start,
        "stem_right_end": t.stem_right_end,
        "stem_right_seq": t.stem_right_seq,
        "poly_t_start": t.poly_t_start,
        "poly_t_end": t.poly_t_end,
        "poly_t_seq": t.poly_t_seq,
        "stem_length": t.stem_length,
        "loop_length": t.loop_length,
        "mismatches": t.mismatches,
        "gc_fraction": getattr(t, "gc_fraction", None),
        "poly_t_length": getattr(t, "poly_t_length", None),
        "score": getattr(t, "score", None)
    }


def sd_to_dict(s):
    return {
        "strand": s.strand,
        "start": s.start,
        "end": s.end,
        "sequence": s.sequence,
        "mismatches": s.mismatches,
        "linked_start_codon": s.linked_start_codon,
        "linked_start_position": s.linked_start_position,
        "distance_to_start": s.distance_to_start,
        "score": s.score,
    }


def analyze_one_sequence(seq: str) -> dict:
    seq = clean_sequence(seq)
    validate_dna(seq)

    orfs = [orf_to_dict(o) for o in find_all_orfs(seq)]
    promoters = [promoter_to_dict(p) for p in find_promoters(seq)]
    terminators = [terminator_to_dict(t) for t in find_rho_independent_terminators(seq)]

    sd_sites = find_shine_dalgarno_sites(seq)
    shine_dalgarno = [sd_to_dict(s) for s in sd_sites]

    return {
        "length": len(seq),
        "orfs": orfs,
        "promoters": promoters,
        "terminators": terminators,
        "shine_dalgarno": shine_dalgarno,
    }


def analyze_folder_files(files: list[dict]) -> list[dict]:
    output = []

    for item in files:
        seq = clean_sequence(item.get("sequence", ""))
        name = item.get("name", "unknown")

        validate_dna(seq)

        result = analyze_one_sequence(seq)
        result["file"] = name
        output.append(result)

    return output


@app.route("/analyze/folder-path", methods=["POST"])
def analyze_folder_path():
    data = request.get_json()
    folder_path = data.get("folder_path", "").strip()

    if not folder_path:
        return jsonify({"error": "folder_path is required"}), 400

    try:
        folder_sequences = load_fasta_folder(folder_path)
        output = []

        for item in folder_sequences:
            seq = item["sequence"]
            result = analyze_one_sequence(seq)
            result["file"] = item["file"]
            result["header"] = item["header"]
            output.append(result)

        return jsonify(output)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/analyze/coding-orfs", methods=["POST"])
def coding_orfs_route():
    data = request.get_json()
    sequence = data.get("sequence", "").strip().upper()

    if not sequence:
        return jsonify({"error": "No DNA sequence provided"}), 400

    orfs = find_coding_orfs(sequence, min_aa=30)
    best_orf = choose_best_coding_orf(sequence, min_aa=30)

    return jsonify({
        "coding_orfs": coding_orfs_to_dicts(orfs),
        "best_coding_orf": coding_orf_to_dict(best_orf) if best_orf else None
    })


@app.route("/analyze/orfs", methods=["POST"])
def analyze_orfs():
    data = request.get_json()
    mode = data.get("mode", "single")

    try:
        if mode == "folder":
            files = data.get("files", [])
            output = []

            for item in files:
                seq = clean_sequence(item.get("sequence", ""))
                name = item.get("name", "unknown")
                validate_dna(seq)

                output.append({
                    "file": name,
                    "length": len(seq),
                    "orfs": [orf_to_dict(o) for o in find_all_orfs(seq)],
                })

            return jsonify(output)

        sequence = clean_sequence(data.get("sequence", ""))
        validate_dna(sequence)
        orfs = find_all_orfs(sequence)
        return jsonify([orf_to_dict(o) for o in orfs])

    except Exception as e:
        print("ORFS ERROR:", e)
        return jsonify({"error": str(e)}), 400


@app.route("/analyze/promoters", methods=["POST"])
def analyze_promoters():
    data = request.get_json() or {}
    mode = data.get("mode", "single")

    try:
        if mode == "folder":
            files = data.get("files", [])
            output = []

            for item in files:
                seq = clean_sequence(item.get("sequence", ""))
                name = item.get("name", "unknown")
                validate_dna(seq)

                promoters = find_promoters(seq)

                output.append({
                    "file": name,
                    "length": len(seq),
                    "promoters": [promoter_to_dict(p) for p in promoters],
                })

            return jsonify(output)

        sequence = clean_sequence(data.get("sequence", ""))
        validate_dna(sequence)

        promoters = find_promoters(sequence)
        return jsonify([promoter_to_dict(p) for p in promoters])

    except Exception as e:
        print("PROMOTERS ERROR:", e)
        return jsonify({"error": str(e)}), 400


@app.route("/analyze/terminators", methods=["POST"])
def analyze_terminators():
    data = request.get_json()
    mode = data.get("mode", "single")

    try:

        if mode == "folder":
            files = data.get("files", [])
            output = []

            for item in files:
                seq = clean_sequence(item.get("sequence", ""))
                name = item.get("name", "unknown")

                validate_dna(seq)

                terminators = find_rho_independent_terminators(seq)

                output.append({
                    "file": name,
                    "length": len(seq),
                    "terminators": [
                        terminator_to_dict(t) for t in terminators
                    ]
                })

            return jsonify(output)

        sequence = clean_sequence(data.get("sequence", ""))
        validate_dna(sequence)

        terminators = find_rho_independent_terminators(sequence)

        return jsonify({
            "terminators": [
                terminator_to_dict(t) for t in terminators
            ]
        })

    except Exception as e:
        print("TERMINATORS ERROR:", e)
        return jsonify({"error": str(e)}), 400


@app.route("/analyze/shine-dalgarno", methods=["POST"])
def analyze_sd():
    data = request.get_json()
    mode = data.get("mode", "single")

    try:
        if mode == "folder":
            files = data.get("files", [])
            output = []

            for item in files:
                seq = clean_sequence(item.get("sequence", ""))
                name = item.get("name", "unknown")
                validate_dna(seq)

                sites = find_shine_dalgarno_sites(seq)

                output.append({
                    "file": name,
                    "length": len(seq),
                    "shine_dalgarno": [sd_to_dict(s) for s in sites],
                })

            return jsonify(output)

        sequence = clean_sequence(data.get("sequence", ""))
        validate_dna(sequence)

        sites = find_shine_dalgarno_sites(sequence)

        return jsonify({
            "shine_dalgarno": [sd_to_dict(s) for s in sites]
        })

    except Exception as e:
        print("SHINE-DALGARNO ERROR:", e)
        return jsonify({"error": str(e)}), 400


@app.route("/analyze/ranked-coding-orfs", methods=["POST"])
def analyze_ranked_coding_orfs():
    data = request.get_json() or {}
    mode = data.get("mode", "single")

    if mode == "single":
        seq = clean_sequence(data.get("sequence", ""))
        validate_dna(seq)

        ranked = rank_coding_orfs(seq)
        best = choose_best_ranked_coding_orf(seq)

        return jsonify({
            "length": len(seq),
            "ranked_coding_orfs": ranked,
            "best_ranked_coding_orf": best,
        })

    elif mode == "folder":
        files = data.get("files", [])
        output = []

        for f in files:
            seq = clean_sequence(f.get("sequence", ""))
            validate_dna(seq)

            ranked = rank_coding_orfs(seq)
            best = choose_best_ranked_coding_orf(seq)

            output.append({
                "file": f.get("name"),
                "length": len(seq),
                "ranked_coding_orfs": ranked,
                "best_ranked_coding_orf": best,
            })

        return jsonify(output)

    return jsonify({"error": "Invalid mode"}), 400


@app.route("/analyze/all", methods=["POST"])
def analyze_all():
    data = request.get_json()
    mode = data.get("mode", "single")

    try:
        if mode == "folder":
            files = data.get("files", [])
            output = analyze_folder_files(files)
            return jsonify(output)

        sequence = clean_sequence(data.get("sequence", ""))
        result = analyze_one_sequence(sequence)
        return jsonify(result)

    except Exception as e:
        print("ALL ERROR:", e)
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
