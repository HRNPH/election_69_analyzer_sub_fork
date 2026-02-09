import os
import json
from collections import defaultdict

# Configuration
MP_DIR = "data/mp"
PL_DIR = "data/pl"
SUSPICIOUS_RATIO = 20.0 

# Canonicalize keys to "1", "2", ... "9"
SINGLE_DIGIT_RANGE = [str(i) for i in range(1, 10)] 
EXCLUDED_PARTIES = ["6", "9"] 

def get_party_suffix(party_code):
    # PARTY-0046 -> "46"
    # PARTY-0005 -> "5"
    if not party_code: return None
    try:
        return str(int(party_code.split("-")[-1]))
    except:
        return None

def get_candidate_number(candidate_code, area_code):
    # CANDIDATE-MP-100105 -> "05" -> "5"
    prefix = f"CANDIDATE-MP-{area_code}"
    if candidate_code.startswith(prefix):
        raw_num = candidate_code[len(prefix):]
        try:
            return str(int(raw_num))
        except:
            return None
    return None

def analyze():
    print(f"Loading data from {MP_DIR} and {PL_DIR}...")
    
    mp_files = sorted([f for f in os.listdir(MP_DIR) if f.endswith(".json")])
    if not mp_files:
        print("No MP data found.")
        return

    party_mp_votes = defaultdict(int)
    party_pl_votes = defaultdict(int)
    type1_anomalies = [] 

    processed_count = 0
    
    for filename in mp_files:
        area_code = filename.replace(".json", "")
        mp_path = os.path.join(MP_DIR, filename)
        pl_path = os.path.join(PL_DIR, filename)

        if not os.path.exists(pl_path):
            continue

        try:
            with open(mp_path, "r") as f: mp_data = json.load(f)
            with open(pl_path, "r") as f: pl_data = json.load(f)
        except Exception:
            continue

        # 1. Process MP Votes
        mp_entries = mp_data.get("entries", [])
        winner_number = None

        if mp_entries:
            # Winner Logic
            top_mp = mp_entries[0]
            winner_number = get_candidate_number(top_mp.get("candidateCode"), area_code)

            # Vote Aggregation
            for entry in mp_entries:
                p_code = entry.get("partyCode")
                vote = entry.get("voteTotal", 0)
                suffix = get_party_suffix(p_code)
                if suffix:
                    party_mp_votes[suffix] += vote

        # 2. Process PL Votes
        pl_entries = pl_data.get("entries", [])
        for entry in pl_entries:
            p_code = entry.get("partyCode")
            vote = entry.get("voteTotal", 0)
            suffix = get_party_suffix(p_code)
            if suffix:
                party_pl_votes[suffix] += vote

        # Type 1 Check
        if winner_number:
            # If Winner is #5, we check if Party #5 (PARTY-0005) is doing well here
            target_party_code = f"PARTY-{int(winner_number):04d}"
            
            found = next((e for e in pl_entries if e.get("partyCode") == target_party_code), None)
            if found:
                rank = found.get("rank")
                if winner_number not in EXCLUDED_PARTIES and rank <= 7:
                     type1_anomalies.append({
                        "area": area_code,
                        "mp_num": winner_number,
                        "pl_party": target_party_code,
                        "pl_rank": rank,
                        "pl_votes": found.get("voteTotal")
                    })

        processed_count += 1

    print(f"\nProcessed {processed_count} areas.")
    
    # --- REPORTING ---

    print(f"\n=== 1. ความผิดปกติรูปแบบที่ 1: ปรากฏการณ์เลขเดียวกัน (ติดอันดับ 1-7) ===")
    print(f"สมมติฐาน: ผู้ลงคะแนนกาบัญชีรายชื่อ 'เบอร์ X' ตามเบอร์ของ 'ผู้ชนะ ส.ส. เขต' (กาเลขเบิ้ล)")
    print(f"ตรรกะ: ถ้า ส.ส. เขตชนะด้วยเบอร์ X แล้วพรรคเบอร์ X (คนละพรรค) ติด Top 7 อย่างผิดปกติหรือไม่?")
    print(f"หมายเหตุ: ไม่นับรวมพรรคหลักเบอร์ 06 และ 09")
    print("-" * 60)
    print(f"{'เขต':<6} | {'เบอร์':<4} | {'อันดับ PL':<10} | {'คะแนน PL':<10}")
    print("-" * 60)
    for a in type1_anomalies[:20]: 
        print(f"{a['area']:<6} | {a['mp_num']:<4} | {a['pl_rank']:<10} | {a['pl_votes']:<10}")
    print(f"... พบความผิดปกติทั้งหมด: {len(type1_anomalies)} เขต (จาก {processed_count} เขต)")

    print(f"\n=== 2. ความผิดปกติรูปแบบที่ 2: คะแนนนิยมปริศนา (สถิติภาพรวม) ===")
    print(f"สมมติฐาน: ผลกระทบตัวคูณคะแนน - คะแนนบัญชีรายชื่อ เทียบกับ คะแนน ส.ส. เขต")
    print(f"ตรรกะ: คำนวณอัตราส่วน = (คะแนนบัญชีรายชื่อ / คะแนน ส.ส. เขต) สำหรับพรรคเลขตัวเดียว")
    print(f"เป้าหมาย: ตรวจจับความต่างมหาศาล (>20เท่า) ที่ชี้ว่าอาจเป็น 'คะแนนผี' ที่ไม่สัมพันธ์กับความนิยมในพื้นที่")
    print("-" * 75)
    print(f"{'พรรค':<6} | {'คะแนนเขต':<12} | {'คะแนน PL':<12} | {'อัตราส่วน':<10} | {'ผลลัพธ์'}")
    print("-" * 75)
    
    for suffix in SINGLE_DIGIT_RANGE:
        mp_v = party_mp_votes.get(suffix, 0)
        pl_v = party_pl_votes.get(suffix, 0)
        
        if mp_v == 0: mp_v = 1 # Avoid div by zero
        
        ratio = pl_v / mp_v
        
        verdict = "ปกติ"
        if ratio > 100: verdict = "ผิดปกติรุนแรง"
        elif ratio > 20: verdict = "น่าสงสัย"
        
        print(f"{suffix:<6} | {mp_v:<12} | {pl_v:<12} | {ratio:.1f}x      | {verdict}")

if __name__ == "__main__":
    analyze()
