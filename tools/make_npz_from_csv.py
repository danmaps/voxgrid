import argparse
import numpy as np
import pandas as pd
from pathlib import Path

parser = argparse.ArgumentParser(description="Convert CSV (x,y,z) to NPZ with 'xyz' array")
parser.add_argument("csv", type=str, help="Input CSV path with columns x,y,z")
parser.add_argument("npz", type=str, nargs="?", help="Output NPZ path (default: same name with .npz)")
args = parser.parse_args()

csv_path = Path(args.csv)
if args.npz:
    out_path = Path(args.npz)
else:
    out_path = csv_path.with_suffix(".npz")

df = pd.read_csv(csv_path)
if not set(["x","y","z"]).issubset(df.columns):
    raise SystemExit("CSV must contain columns: x,y,z")

xyz = df[["x","y","z"]].to_numpy(dtype=np.float32)
np.savez(out_path, xyz=xyz)
print(f"Wrote {out_path} with array 'xyz' of shape {xyz.shape}")
