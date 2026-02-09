import os
import json
from collections import defaultdict

# Configuration
MP_DIR = "data/mp"
PL_DIR = "data/pl"
COMMON_DATA_FILE = "docs/data/common-data.json"
OUTPUT_FILE = "data/anomaly_report.json"
SINGLE_DIGIT_RANGE = [str(i) for i in range(1, 10)] 
EXCLUDED_PARTIES = ["6", "9"] 

def load_province_map():
    if not os.path.exists(COMMON_DATA_FILE):
        return {}
    try:
        with open(COMMON_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Map "PROVINCE-10" -> "กรุงเทพฯ"
            # Return map of "10" -> "กรุงเทพฯ" for easier lookup with area code prefix
            return {p["code"].replace("PROVINCE-", ""): p["name"] for p in data.get("provinces", [])}
    except Exception as e:
        print(f"Warning: Could not load common data: {e}")
        return {}

def get_province_info(area_code, province_map):
    prefix = area_code[:2]
    return prefix, province_map.get(prefix, f"Unknown ({prefix})")

def get_candidate_number_str(candidate_code, area_code):
    """
    Extracts candidate number string from code, e.g., 'CANDIDATE-MP-100105' -> '5'
    """
    prefix = f"CANDIDATE-MP-{area_code}"
    if candidate_code and candidate_code.startswith(prefix):
        raw_num = candidate_code[len(prefix):]
        try:
            return str(int(raw_num))
        except ValueError:
            return None
    return None

    """
    Extracts candidate number string from code, e.g., 'CANDIDATE-MP-100105' -> '5'
    """
    prefix = f"CANDIDATE-MP-{area_code}"
    if candidate_code and candidate_code.startswith(prefix):
        raw_num = candidate_code[len(prefix):]
        try:
            return str(int(raw_num))
        except ValueError:
            return None
    return None

def main():
    print(f"Scanning data from {MP_DIR} and {PL_DIR}...")
    
    province_map = load_province_map()
    
    if not os.path.exists(MP_DIR):
        print(f"Error: Directory {MP_DIR} not found.")
        return

    mp_files = sorted([f for f in os.listdir(MP_DIR) if f.endswith(".json")])
    anomalies = []
    
    for filename in mp_files:
        area_code = filename.replace(".json", "")
        mp_path = os.path.join(MP_DIR, filename)
        pl_path = os.path.join(PL_DIR, filename)

        if not os.path.exists(pl_path):
            continue

        try:
            with open(mp_path, "r", encoding="utf-8") as f:
                mp_data = json.load(f)
            with open(pl_path, "r", encoding="utf-8") as f:
                pl_data = json.load(f)
        except Exception as e:
            print(f"Error reading {area_code}: {e}")
            continue

        mp_entries = mp_data.get("entries", [])
        pl_entries = pl_data.get("entries", [])
        
        if not mp_entries:
            continue

        # 1. Identify Winner
        winner = mp_entries[0]
        winner_num_str = get_candidate_number_str(winner.get("candidateCode"), area_code)
        
        if not winner_num_str:
            continue
            
        # 2. Extract Winner Stats
        winner_party_code = winner.get("partyCode", "")
        winner_votes = winner.get("voteTotal", 0)
        
        # 3. Check "Twin Party" in Party List
        # Construct the target party ID: e.g. winner #5 -> "PARTY-0005"
        try:
            target_party_id = f"PARTY-{int(winner_num_str):04d}"
        except ValueError:
            continue
            
        # Find this party in the PL results
        pl_twin_entry = next((e for e in pl_entries if e.get("partyCode") == target_party_id), None)
        
        # New: Find MP Candidate for this Twin Party in the same area
        mp_twin_entry = next((e for e in mp_entries if e.get("partyCode") == target_party_id), None)
        mp_twin_votes = mp_twin_entry.get("voteTotal", 0) if mp_twin_entry else 0
        
        if pl_twin_entry:
            pl_votes = pl_twin_entry.get("voteTotal", 0)
            pl_rank = pl_twin_entry.get("rank")
            
            # 4. Calculate Ratio (Twin PL Votes / Winner MP Votes)
            # Note: This is a localized ratio (Area specific), different from the global ratio in verify_hypothesis.py
            # But the 'Anomaly' is defined by the Twin Effect mainly.
            
            # Avoid division by zero
            base_votes = winner_votes if winner_votes > 0 else 1
            ratio = pl_votes / base_votes
            
            # 5. Filter for Reporting
            # Condition A: Winner number is 1-9 (excluding 6, 9)
            # Condition B: The Twin Party ranks high (Top 7) OR The Twin Party gets significant votes
            
            is_single_digit = winner_num_str in SINGLE_DIGIT_RANGE
            is_excluded = winner_num_str in EXCLUDED_PARTIES
            
            if is_single_digit and not is_excluded:
                # Calculate simple anomaly score:
                # How much did the "Twin Party" overperform expectations?
                # Expectation: Twin Party (often small) shouldn't be in Top 7 ifMP Winner is from a different party.
                
                # Check if MP Winner Party is DIFFERENT from Twin Party
                # (Almost always true, as Party-0005 is likely not the party of Candidate #5)
                is_different_party = winner_party_code != target_party_id
                
                if is_different_party and pl_rank <= 7:
                    anomalies.append({
                        "area_code": area_code,
                        "mp_winner_number": winner_num_str,
                        "mp_winner_party": winner_party_code,
                        "mp_votes": winner_votes,
                        "pl_twin_party": target_party_id,
                        "pl_twin_rank": pl_rank,
                        "pl_twin_votes": pl_votes,
                        "mp_twin_candidate_votes": mp_twin_votes,
                        "ratio_pl_to_mp": round(ratio, 4), # Ratio of Twin PL votes to Winner MP votes
                        "anomaly_score": pl_votes, # Simple score: raw votes obtained by the twin party
                        "province_id": area_code[:2],
                        "province_name": province_map.get(area_code[:2], "Unknown")
                    })

    # Sort by 'anomaly_score' (votes obtained by the questionable party) descending
    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
    
    # --- Aggregations ---
    
    # 1. By Province
    province_stats = defaultdict(lambda: {"count": 0, "total_ghost_votes": 0, "areas": []})
    for a in anomalies:
        p_id = a["province_id"]
        p_name = a["province_name"]
        entry = province_stats[p_id]
        entry["id"] = p_id
        entry["name"] = p_name
        entry["count"] += 1
        entry["total_ghost_votes"] += a["pl_twin_votes"]
        entry["areas"].append(a["area_code"])
        
    sorted_provinces = sorted(province_stats.values(), key=lambda x: x["total_ghost_votes"], reverse=True)

    # 2. By Winning MP Party
    mp_party_stats = defaultdict(lambda: {"count": 0, "total_ghost_votes": 0, "provinces": defaultdict(int)})
    for a in anomalies:
        party = a["mp_winner_party"]
        p_name = a["province_name"]
        entry = mp_party_stats[party]
        entry["party_code"] = party
        entry["count"] += 1
        entry["total_ghost_votes"] += a["pl_twin_votes"]
        entry["provinces"][p_name] += 1
        
    sorted_mp_parties = sorted(mp_party_stats.values(), key=lambda x: x["count"], reverse=True)
    
    # Save to JSON
    output_data = {
        "metadata": {
            "description": "Anomaly detection report based on Twin Number Hypothesis (Buy 1 Get 2)",
            "criteria": "Winner MP Number (1-9, excl 6,9) matches Top 7 Party List Number (Different Party)",
            "total_areas_flagged": len(anomalies)
        },
        "anomalies": anomalies,
        "province_stats": sorted_provinces,
        "mp_party_stats": sorted_mp_parties
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nAnalysis complete. Found {len(anomalies)} anomalies.")
    print(f"Report saved to: {(OUTPUT_FILE)}")
    
    # Print Summaries
    print("\n=== Top 5 Provinces by Anomalies ===")
    for p in sorted_provinces[:5]:
         print(f"{p['name']}: {p['count']} areas, {p['total_ghost_votes']} ghost votes")

    print("\n=== Top 5 MP Parties involved ===")
    for p in sorted_mp_parties[:5]:
         print(f"{p['party_code']}: {p['count']} areas, {p['total_ghost_votes']} ghost votes")

    # Print Top 10 Summary
    print("\n=== Top 10 Anomalies (Sorted by Twin Party Votes) ===")
    print(f"{'Area':<6} | {'MP Num':<6} | {'Twin Party':<12} | {'Twin Rank':<10} | {'Twin PL Votes':<14} | {'Twin MP Votes':<14}")
    print("-" * 80)
    for a in anomalies[:10]:
        print(f"{a['area_code']:<6} | {a['mp_winner_number']:<6} | {a['pl_twin_party']:<12} | {a['pl_twin_rank']:<10} | {a['pl_twin_votes']:<14} | {a['mp_twin_candidate_votes']:<14}")

if __name__ == "__main__":
    main()
