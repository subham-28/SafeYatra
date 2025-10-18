import osmnx as ox
import networkx as nx
from datetime import datetime
import pandas as pd # Still needed for error handling
import os
import math

# --- Helper Function to Prepare Graph ---
def _prepare_graph_for_routing(G, alpha):
    """
    Applies ONLY the dynamic NIGHT penalty and calculates blended cost.
    Assumes base_cost already includes crime risk, POI bonus, and LIGHTING penalty.
    """
    G_updated = G.copy()

    # --- Convert graph attributes ---
    print("Checking and converting graph attributes...")
    edges_to_remove = []
    for u, v, key, data in G_updated.edges(keys=True, data=True):
        try:
            # Ensure base_cost and length exist and are float
            if 'base_cost' not in data:
                print(f"Warning: 'base_cost' missing for edge ({u},{v},{key}). Using length.")
                data['base_cost'] = float(data['length'])
            else:
                data['base_cost'] = float(data['base_cost'])
            data['length'] = float(data['length'])
        except (ValueError, TypeError, KeyError) as e:
            print(f"Warning: Removing edge ({u},{v},{key}) due to invalid data. Error: {e}.")
            edges_to_remove.append((u, v, key))

    G_updated.remove_edges_from(edges_to_remove)
    print("✅ Attributes checked.")

    # --- Apply Dynamic Night-Time Penalty & Calculate Blended Cost ---
    now = datetime.now()
    is_late_night = now.hour >= 22 or now.hour <= 5

    valid_edges_data = [data for _, _, data in G_updated.edges(data=True)]
    if not valid_edges_data:
        raise ValueError("No valid edges with numeric base_cost and length found.")

    # Base_cost already includes static lighting penalty
    base_costs = [data['base_cost'] for data in valid_edges_data]
    lengths = [data['length'] for data in valid_edges_data]
    min_cost, max_cost = min(base_costs), max(base_costs)
    min_len, max_len = min(lengths), max(lengths)
    cost_range = max_cost - min_cost if max_cost > min_cost else 1
    len_range = max_len - min_len if max_len > min_len else 1

    print("Applying night-time penalty and calculating blended cost...")
    for u, v, key, data in G_updated.edges(keys=True, data=True):
        # Start with pre-calculated cost (includes lighting penalty)
        cost = data['base_cost']

        # Apply ONLY night penalty dynamically
        if is_late_night:
            cost *= 2.0

        # --- Lighting penalty logic is REMOVED ---

        # Create the blended cost
        norm_safety = (cost - min_cost) / cost_range
        norm_length = (data['length'] - min_len) / len_range
        data['combined_cost'] = (alpha * norm_safety) + ((1 - alpha) * norm_length)

    return G_updated


# --- Helper Function _get_single_best_route (No changes needed) ---
def _get_single_best_route(G_updated, start, end):
    """ Finds the single best route using Dijkstra's algorithm based on 'combined_cost'. """
    # ... (Keep the previous version of this function) ...
    try:
        start_lon = float(start[0])
        start_lat = float(start[1])
        end_lon = float(end[0])
        end_lat = float(end[1])
        if math.isnan(start_lon) or math.isnan(start_lat) or math.isnan(end_lon) or math.isnan(end_lat):
             print("❌ Error: Input coordinates contain NaN values.")
             return None
    except (ValueError, TypeError, IndexError):
        print("❌ Error: Invalid input coordinate format.")
        return None
    try:
        source_node = ox.distance.nearest_nodes(G_updated, X=start_lon, Y=start_lat)
        dest_node = ox.distance.nearest_nodes(G_updated, X=end_lon, Y=end_lat)
    except Exception as e:
        print(f"❌ Error finding nearest nodes: {e}")
        return None
    try:
        best_path_nodes = nx.shortest_path(G_updated, source=source_node, target=dest_node, weight='combined_cost')
        path_coords = [[G_updated.nodes[node]['y'], G_updated.nodes[node]['x']] for node in best_path_nodes]
        return path_coords
    except nx.NetworkXNoPath:
        print("❌ No path found between the specified points.")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during Dijkstra pathfinding: {e}")
        return None

# --- PUBLIC FUNCTIONS (Simplified) ---
# GRAPH_FILEPATH should point to your file with pre-calculated lighting penalties
GRAPH_FILEPATH = "chicago_final_graph_with_lights.graphml"

# --- Accepts graph object 'G' ---
def get_safest_route(G, start, end, alpha=0.7):
    """ Top-level function to get the single best route using Dijkstra. """
    if G is None:
        print("❌ Error: Graph object is None.")
        return None
    try:
        # No longer passes current_outages
        G_prepared = _prepare_graph_for_routing(G, alpha)
        safe_route_coords = _get_single_best_route(G_prepared, start, end)
        return safe_route_coords
    except Exception as e:
        print(f"An error occurred in get_safest_route: {e}")
        return None

# --- Accepts graph object 'G' ---
def get_alt_routes(G, start, end, alpha=0.7, k=3):
    """ Finds alternate routes using the edge penalty method. """
    if G is None:
        print("❌ Error: Graph object is None.")
        return []
    try:
        # No longer passes current_outages
        G_prepared = _prepare_graph_for_routing(G, alpha)

        all_routes_nodes = []
        alt_routes_coords = []

        start_node = ox.distance.nearest_nodes(G_prepared, X=start[0], Y=start[1])
        end_node = ox.distance.nearest_nodes(G_prepared, X=end[0], Y=end[1])

        try:
             best_path_nodes = nx.shortest_path(G_prepared, source=start_node, target=end_node, weight='combined_cost')
             if not best_path_nodes: return []
             all_routes_nodes.append(best_path_nodes)
        except nx.NetworkXNoPath:
             print("❌ No initial path found.")
             return []

        # Iteratively find alternatives
        G_temp = G_prepared.copy()
        for _ in range(k - 1):
            last_path = all_routes_nodes[-1]
            if not last_path: continue

            for i in range(len(last_path) - 1):
                u, v = last_path[i], last_path[i+1]
                if G_temp.has_edge(u, v):
                    for key in G_temp.get_edge_data(u, v):
                        if 'combined_cost' in G_temp.edges[u, v, key] and isinstance(G_temp.edges[u, v, key]['combined_cost'], (int, float)):
                            G_temp.edges[u, v, key]['combined_cost'] *= 100
                        else:
                            print(f"Warning: Skipping penalty on edge ({u},{v},{key}).")

            try:
                temp_start_node = ox.distance.nearest_nodes(G_temp, X=start[0], Y=start[1])
                temp_end_node = ox.distance.nearest_nodes(G_temp, X=end[0], Y=end[1])
                next_path_nodes = nx.shortest_path(G_temp, source=temp_start_node, target=temp_end_node, weight='combined_cost')

                is_new = all(next_path_nodes != p for p in all_routes_nodes)
                if is_new:
                    all_routes_nodes.append(next_path_nodes)
                else:
                    print("Found duplicate path, stopping search.")
                    break
            except nx.NetworkXNoPath:
                print("No further alternate paths found.")
                break

        for path_nodes in all_routes_nodes[1:]:
            path_coords = [[G_prepared.nodes[node]['y'], G_prepared.nodes[node]['x']] for node in path_nodes]
            alt_routes_coords.append(path_coords)

        return alt_routes_coords

    except Exception as e:
        print(f"An error occurred in get_alt_routes: {e}")
        return []