"""
Sequence Dynamic Programming Alignment Module.
Aligns target slides (1..M) to baseline slides (1..N), supporting 1:0, 1:1, 1:2, 1:3, etc. mappings.
"""
import re
from collections import Counter

def tokenize(text):
    """
    Extracts Korean syllables/words and alphanumeric tokens.
    """
    if not text:
        return []
    return re.findall(r"[a-zA-Z0-9가-힣]+", text.lower())

def compute_similarity(base_slide, target_slide_group):
    """
    Computes a comprehensive similarity score between a base slide and a group of target slides.
    """
    base_text = base_slide.get("text", "")
    target_text = "\n".join([s.get("text", "") for s in target_slide_group])
    
    if not base_text and not target_text:
        return 0.5
    if not base_text or not target_text:
        return 0.05
        
    # 1. Token-level Jaccard similarity
    tok_base = set(tokenize(base_text))
    tok_target = set(tokenize(target_text))
    
    jaccard = 0.0
    if tok_base and tok_target:
        intersection = len(tok_base & tok_target)
        union = len(tok_base | tok_target)
        jaccard = intersection / union if union > 0 else 0.0
        
    # 2. Title and Line Overlap (high weight)
    base_lines = [l.strip() for l in base_slide.get("lines", []) if len(l.strip()) >= 2]
    target_lines = []
    for s in target_slide_group:
        target_lines.extend([l.strip() for l in s.get("lines", []) if len(l.strip()) >= 2])
        
    line_matches = 0
    for bl in base_lines:
        for tl in target_lines:
            if bl == tl:
                line_matches += 1.0
                break
            elif len(bl) >= 4 and (bl in tl or tl in bl):
                line_matches += 0.8
                break
                
    line_ratio = line_matches / max(len(base_lines), 1)
    
    # 3. First Title Match Bonus
    title_bonus = 0.0
    base_title = base_slide.get("title", "").strip()
    target_first_title = target_slide_group[0].get("title", "").strip() if target_slide_group else ""
    if base_title and target_first_title:
        if base_title in target_first_title or target_first_title in base_title:
            title_bonus = 0.3
            
    total_score = (jaccard * 0.3) + (line_ratio * 0.5) + title_bonus
    return min(1.0, total_score)

def align_target_to_base(base_slides, target_slides, max_group_size=4):
    """
    Monotonic Dynamic Programming to map target slides into base slides.
    Returns a list of length len(base_slides), where each item is a list of target slide objects.
    """
    N = len(base_slides)
    M = len(target_slides)
    
    if M == 0:
        return [[] for _ in range(N)]
        
    # dp[i][j]: best score aligning first j target slides to first i base slides
    dp = [[-1e9] * (M + 1) for _ in range(N + 1)]
    parent = [[None] * (M + 1) for _ in range(N + 1)]
    dp[0][0] = 0.0
    
    # Base slide index: 0..N-1 (DP index 1..N)
    # Target slide index: 0..M-1 (DP index 1..M)
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
                
                # Penalty if assigning multiple slides without reasonable similarity
                count = j - k
                group_penalty = 0.05 * (count - 1)
                
                # Minimum threshold reward
                score_gain = sim - group_penalty
                cand = dp[i - 1][k] + score_gain
                
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
