def simos_from_ranking(order_list, groups_list=None):
    """
    Calculates Simos weights handling Sequence, Gaps ("gap"), and Merged Groups.
    """
    if groups_list is None:
        groups_list = []

    # --- 0. Normalize groups_list (THE FIX) ---
    # Catch flat arrays or dictionary formats sent by the frontend
    # and force them into a list of lists.
    clean_groups = []
    if groups_list and all(isinstance(x, (int, str)) for x in groups_list):
        # Frontend sent a flat list for a single group
        clean_groups.append(groups_list)
    else:
        for g in groups_list:
            if isinstance(g, list):
                clean_groups.append(g)
            elif isinstance(g, dict):
                # Frontend sent array of objects
                for v in g.values():
                    if isinstance(v, list):
                        clean_groups.append(v)
    groups_list = clean_groups

    # --- 1. Map every item to its Group Index ---
    item_to_group_idx = {}
    for g_idx, group in enumerate(groups_list):
        for item in group:
            item_to_group_idx[str(item)] = g_idx

    rank_map = {}
    current_rank = 1
    processed_group_indices = set()

    # Catch cases where the frontend nests the group directly inside the order_list
    flat_order = []
    for item in order_list:
        if isinstance(item, list):
            if item not in groups_list:
                groups_list.append(item)
                g_idx = len(groups_list) - 1
                for sub in item:
                    item_to_group_idx[str(sub)] = g_idx
            flat_order.extend(item)
        else:
            flat_order.append(item)

    # --- 2. Iterate through the Order ---
    for item in flat_order:
        if item == "gap":
            current_rank += 1
            continue

        str_item = str(item)
        g_idx = item_to_group_idx.get(str_item)

        if g_idx is not None:
            # Item is merged! Process the whole group at once.
            if g_idx not in processed_group_indices:
                group_members = groups_list[g_idx]
                for member in group_members:
                    rank_map[str(member)] = current_rank
                processed_group_indices.add(g_idx)
                current_rank += 1
        else:
            # Single card
            rank_map[str_item] = current_rank
            current_rank += 1

    # --- 3. Gather Valid IDs safely ---
    valid_ids = set()
    for item in flat_order:
        if item != "gap":
            valid_ids.add(str(item))
    for group in groups_list:
        for item in group:
            valid_ids.add(str(item))

    # --- 4. Clean and Calculate Weights ---
    clean_rank_map = {}
    for k, v in rank_map.items():
        str_k = str(k)
        if str_k in valid_ids:
            clean_rank_map[str_k] = v

    raw_weights = {k: v for k, v in clean_rank_map.items()}
    total_raw = sum(raw_weights.values())

    normalized = {}
    for k, v in raw_weights.items():
        normalized[k] = v / total_raw if total_raw > 0 else 0.0

    result = []
    sorted_ids = sorted(clean_rank_map.keys(), key=lambda x: clean_rank_map[x])

    for ind_id in sorted_ids:
        result.append({
            "id": ind_id,
            "position": clean_rank_map[ind_id],
            "raw_weight": raw_weights[ind_id],
            "normalized_weight": normalized[ind_id]
        })

    return {
        "indicators": result,
        "total_raw": total_raw
    }