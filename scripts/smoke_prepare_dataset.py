import os
import numpy as np
import polars as pl
from pathlib import Path

def generate_smoke_dataset(dim, name, count=100, test_count=10):
    project_root = Path(__file__).parent.parent.resolve()
    dataset_dir = project_root / "datasets" / "smoke" / name
    dataset_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating smoke dataset: {name} (dim={dim}) in {dataset_dir}")
    
    # Train data
    train_ids = np.arange(count, dtype=np.int32)
    train_embs = np.random.rand(count, dim).astype(np.float32)
    # Normalize for cosine similarity
    train_embs = train_embs / np.linalg.norm(train_embs, axis=1, keepdims=True)
    
    train_df = pl.DataFrame({
        "id": train_ids,
        "emb": [list(row) for row in train_embs]
    })
    train_df.write_parquet(dataset_dir / "train.parquet")
    
    # Test data
    test_ids = np.arange(test_count, dtype=np.int32)
    test_embs = np.random.rand(test_count, dim).astype(np.float32)
    test_embs = test_embs / np.linalg.norm(test_embs, axis=1, keepdims=True)
    
    test_df = pl.DataFrame({
        "id": test_ids,
        "emb": [list(row) for row in test_embs]
    })
    test_df.write_parquet(dataset_dir / "test.parquet")
    
    # Ground truth (neighbors)
    # Simple: just the first k nearest neighbors from the random set
    # For a smoke test, we don't need real accuracy, but let's make it look real.
    # Actually, we can just say neighbors are the first 10 IDs.
    neighbors = []
    for _ in range(test_count):
        neighbors.append(list(range(10))) # Fake neighbors for smoke test
        
    neighbors_df = pl.DataFrame({
        "id": test_ids,
        "neighbors_id": neighbors
    })
    neighbors_df.write_parquet(dataset_dir / "neighbors.parquet")
    
    print(f"Created {name} in {dataset_dir}")

if __name__ == "__main__":
    generate_smoke_dataset(768, "cohere_768")
    generate_smoke_dataset(1536, "openai_1536")
    generate_smoke_dataset(2048, "bge_2048")
