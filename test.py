import numpy as np
import pandas as pd
import osmnx as ox # Import osmnx to load the graph
from safe_route import get_safest_route, get_alt_routes

# --- 1. Load the Graph ---
GRAPH_FILEPATH_TEST = "chicago_final_graph_with_lights.graphml" # Make sure this path is correct
print("Loading the graph for testing...")

try:
    graph_for_test = ox.load_graphml(filepath=GRAPH_FILEPATH_TEST)
    print("✅ Graph loaded.")
except FileNotFoundError:
    print(f"❌ ERROR: Graph file not found at {GRAPH_FILEPATH_TEST}. Cannot run tests.")
    exit() # Stop the script if graph can't load
except Exception as e:
    print(f"❌ ERROR: Failed to load graph. {e}")
    exit()

# --- 2. Define Test Coordinates ---
start_test = (-87.6090, 41.8917) # lon, lat
end_test = (-87.6403, 41.8785)

# --- 3. Test get_safest_route ---
print("\n--- Testing get_safest_route ---")
# Pass the loaded graph object 'graph_for_test' as the first argument
safest_path = get_safest_route(graph_for_test, start_test, end_test, alpha=0.7)

if safest_path:
    print(f"✅ get_safest_route returned a path with {len(safest_path)} points.")
    print(safest_path)
else:
    print("❌ get_safest_route failed or found no path.")

# --- 4. Test get_alt_routes ---
print("\n--- Testing get_alt_routes ---")
# Pass the loaded graph object 'graph_for_test' as the first argument
alternate_paths = get_alt_routes(graph_for_test, start_test, end_test, alpha=0.7)

if isinstance(alternate_paths, list):
    print(f"✅ get_alt_routes returned {len(alternate_paths)} alternate paths.")
    if alternate_paths:
        for i in range(len(alternate_paths)):
             print(f"{i+1}th alternate path's first 3 points:", alternate_paths[i][:3])
else:
    print("❌ get_alt_routes failed.")

print("\n--- Test Complete ---")