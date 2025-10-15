# Set up Miniforge
source /work/project/miniforge3/etc/profile.d/conda.sh
export PATH=/work/project/miniforge3/bin:$PATH

#!/bin/bash
eval "$(/work/project/miniforge3/bin/conda shell.bash hook)"
conda init

# Initialize Conda
eval "$(conda shell.bash hook)"

# Activate the Conda environment
conda activate project_env

# Set Gurobi license path
export GRB_LICENSE_FILE=/work/project/gurobi.lic

# setup Jupyter kernel
python -m ipykernel install --user --name project_env --display-name "Python (project_env)"

