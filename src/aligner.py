"""
Sequence Dynamic Programming Alignment Module.
Aligns target slides (1..M) to baseline slides (1..N) by comparing H1 (primary title),
H2 (secondary title/topic), line overlaps, and token similarity, supporting 1:0, 1:1, 1:2, 1:3 mappings.
"""
import re

GENERIC_HEADERS = {
    "unit section", "week 01", "week 02", "week 03", "week 04",
    "unit 01", "unit 02", "unit 03", "unit 04",
    "intro", "01", "02", "03", "04", "05", "unit"
}

def tokenize(text):
    """
    Extracts Korean syllables/words and alphanumeric tokens.
    """
    if not text:
        return []
    return re.findall(r"[a-zA-Z0-9가-힣]+", text.lower())

def clean_line(l):
    if not l:
        return ""
    # Strip bullet symbols, numbering like 1., (1), etc.
    l = re.sub(r"^[0-9\.\-\(\)\s\u25a0\u25a1\u2590\u25cf\u25cb\u25b6\u25b7]+", "", l)
    return l.strip().lower()

def extract_primary_titles(lines):
    """
    Extracts H1 and H2 by filtering out generic unit/layout banners.
    """
    cleaned = [clean_line(l) for l in lines if len(clean_line(l)) >= 2]
    meaningful = [c for c in cleaned if c not in GENERIC_HEADERS]
    h1 = meaningful[0] if meaningful else (cleaned[0] if cleaned else "")
    h2 = meaningful[1] if len(meaningful) > 1 else (cleaned[1] if len(cleaned) > 1 else "")
    return h1, h2, cleaned

def compute_similarity(base_slide, target_slide_group):
    """
    Computes similarity score comparing H1, H2, line overlap, and token Jaccard.
    """
    base_lines = base_slide.get("lines", [])
    b_h1, b_h2, b_cleaned = extract_primary_titles(base_lines)
    base_text = base_slide.get("text", "")
    target_text = "\n".join([s.get("text", "") for s in target_slide_group])
    
    if not base_text and not target_text:
        return 0.5
    if not base_text or not target_text:
        return 0.05

    target_h1s = []
    target_h2s = []
    target_all_meaningful = []
    for s in target_slide_group:
        th1, th2, t_cleaned = extract_primary_titles(s.get("lines", []))
        target_h1s.append(th1)
        target_h2s.append(th2)
        target_all_meaningful.extend(t_cleaned)

    # 1. H1 Cross-boundary check: multi-slide group should share the same H1 topic
    unique_th1s = set([th1 for th1 in target_h1s if th1])
    if len(unique_th1s) > 1:
        first = list(unique_th1s)[0]
        for other in list(unique_th1s)[1:]:
            if first not in other and other not in first:
                return -10.0  # Disallow grouping distinct major section slides

    # 2. H2 Cross-boundary check: if slides have distinct H2 sub-topics
    if len(target_slide_group) > 1:
        unique_th2_prefixes = set()
        for th2 in target_h2s:
            prefix = th2.split(":")[0].strip() if ":" in th2 else th2[:10]
            if len(prefix) >= 3:
                unique_th2_prefixes.add(prefix)
        if len(unique_th2_prefixes) > 1:
            return -10.0

    # 3. H1 Matching Score
    h1_score = 0.0
    for th1 in target_h1s:
        if b_h1 and th1:
            if b_h1 == th1:
                h1_score = max(h1_score, 0.7)
            elif len(b_h1) >= 4 and (b_h1 in th1 or th1 in b_h1):
                h1_score = max(h1_score, 0.55)
            for tline in target_all_meaningful:
                if b_h1 == tline or (len(b_h1) >= 4 and b_h1 in tline):
                    h1_score = max(h1_score, 0.45)
        elif b_h2 and th1:
            if b_h2 == th1 or (len(b_h2) >= 4 and (b_h2 in th1 or th1 in b_h2)):
                h1_score = max(h1_score, 0.5)

    # 4. H2 Matching Score
    h2_score = 0.0
    if b_h2:
        for th2 in target_h2s:
            if b_h2 and th2:
                b_prefix = b_h2.split(":")[0].strip()
                if b_h2 in th2 or th2 in b_h2 or (len(b_prefix) >= 4 and b_prefix in th2):
                    h2_score = max(h2_score, 0.5)
                elif b_h2 == th2:
                    h2_score = max(h2_score, 0.5)
        for tline in target_all_meaningful:
            if b_h2 == tline or (len(b_h2) >= 4 and (b_h2 in tline or tline in b_h2)):
                h2_score = max(h2_score, 0.35)

    # 5. Token Jaccard
    tok_base = set(tokenize(base_text))
    tok_target = set(tokenize(target_text))
    jaccard = 0.0
    if tok_base and tok_target:
        intersection = len(tok_base & tok_target)
        union = len(tok_base | tok_target)
        jaccard = intersection / union if union > 0 else 0.0

    # Group size bonus when matched
    group_bonus = 0.0
    if len(target_slide_group) > 1 and (h1_score >= 0.55 or h2_score >= 0.4):
        group_bonus = 0.15 * (len(target_slide_group) - 1)

    total_score = h1_score + h2_score + (jaccard * 0.3) + group_bonus
    return max(0.0, min(1.0, total_score))

def align_target_to_base(base_slides, target_slides, max_group_size=4):
    """
    Monotonic Dynamic Programming to map target slides into base slides.
    Returns a list of length len(base_slides), where each item is a list of target slide objects.
    """
    N = len(base_slides)
    M = len(target_slides)
    
    if M == 0:
        return [[] for _ in range(N)]
        
    dp = [[-1e9] * (M + 1) for _ in range(N + 1)]
    parent = [[None] * (M + 1) for _ in range(N + 1)]
    dp[0][0] = 0.0
    
    for i in range(1, N + 1):
        base_s = base_slides[i - 1]
        for j in range(M + 1):
            # Option 1: Base slide i gets 0 target slides (skip/empty)
            if dp[i - 1][j] > dp[i][j]:
                dp[i][j] = dp[i - 1][j]
                parent[i][j] = (i - 1, j, [])
                
            # Option 2: Base slide i takes target slides k..j-1
            for k in range(max(0, j - max_group_size), j):
                if dp[i - 1][k] <= -1e8:
                    continue
                group = target_slides[k:j]
                sim = compute_similarity(base_s, group)
                if sim <= -5.0:
                    continue
                
                cand = dp[i - 1][k] + sim
                if cand > dp[i][j]:
                    dp[i][j] = cand
                    parent[i][j] = (i - 1, k, group)
                    
    # Backtrack to reconstruct mapping
    curr_i, curr_j = N, M
    mapping = [[] for _ in range(N)]
    
    while curr_i > 0:
        p = parent[curr_i][curr_j]
        if p is None:
            break
        prev_i, prev_j, assigned_group = p
        mapping[curr_i - 1] = assigned_group
        curr_i, curr_j = prev_i, prev_j
        
    return mapping

def generate_comparison_data(file_results):
    """
    Takes all processed file results (file_results[0] is base).
    Builds the unified comparison data structure for frontend rendering.
    """
    base_file = file_results[0]
    base_slides = base_file["slides"]
    
    comparison_rows = []
    
    # Align each comparison file against base
    file_mappings = []
    for i in range(1, len(file_results)):
        target_file = file_results[i]
        mapping = align_target_to_base(base_slides, target_file["slides"])
        file_mappings.append(mapping)
        
    for r_idx, b_slide in enumerate(base_slides):
        row_targets = []
        for f_idx, mapping in enumerate(file_mappings):
            target_file = file_results[f_idx + 1]
            matched_slides = mapping[r_idx]
            row_targets.append({
                "file_name": target_file["file_name"],
                "file_index": f_idx + 2,
                "slides": matched_slides
            })
            
        comparison_rows.append({
            "row_index": r_idx + 1,
            "base_slide": b_slide,
            "targets": row_targets
        })
        
    return {
        "files": [{
            "index": i + 1,
            "name": f["file_name"],
            "slide_count": f["slide_count"],
            "is_base": (i == 0)
        } for i, f in enumerate(file_results)],
        "rows": comparison_rows
    }
