import pypsa
import sys
import os
import logging
import gurobipy

# File paths
log_path = f"project/logs/"
network_path = f"project/networks/test.nc"
output_path = f"project/networks/test_solved.nc"

# Ensure existence of folders
os.makedirs(log_path, exist_ok=True)

# Set up logging
log_file_path = os.path.join(log_path, "test.log")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", handlers=[
    logging.FileHandler(log_file_path, mode="w"),  # 'w' to overwrite each run
    logging.StreamHandler(sys.stdout)              # Print to console as well
])
logger = logging.getLogger()

# seat gurobi license just to be sure
os.environ["GRB_LICENSE_FILE"] = "/work/project/gurobi.lic"
# Loading network file
logger.info("Loading network...")
n = pypsa.Network(network_path)
# solving network
logger.info("Optimizing network with Gurobi...")
n.optimize(solver_name='gurobi', keep_files=False)
# exporting solved network
logger.info(f"Exporting solved network to {output_path}")
n.export_to_netcdf(output_path)

logger.info("Script completed successfully.")

