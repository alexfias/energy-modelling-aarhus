
#!/bin/bash

# Load Conda into the shell session
source /work/project/miniforge3/etc/profile.d/conda.sh
export PATH=/work/project/miniforge3/bin:$PATH

# Activate the correct Conda environment
conda activate project_env

# Set Gurobi license location (cluster-specific)
export GRB_LICENSE_FILE=/work/project/gurobi.lic

# Define the log directory & log file (job-specific)
LOG_DIR="/work/project/logs"
mkdir -p "$LOG_DIR"                         # Ensure log folder exists
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/full_run_$TIMESTAMP.log"

# Start logging
echo "===== Job started at $(date) =====" | tee -a "$LOG_FILE"
echo "Using arguments: $SCENARIO $MOD" | tee -a "$LOG_FILE"

# Redirect all Python output & errors to the log file
{
    python /work/project/scripts/test.py
} 2>&1 | tee -a "$LOG_FILE"

# Log completion time
echo "===== Job completed at $(date) =====" | tee -a "$LOG_FILE"
