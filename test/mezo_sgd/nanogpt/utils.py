import torch
import time
import argparse
from tqdm import tqdm
import psutil
import os


def get_args():
    args = argparse.ArgumentParser()
    args.add_argument("--zo_method", type=str, default="zo2")
    args.add_argument("--model_id", type=str, default="gpt2")
    args.add_argument("--verbose", action="store_true")
    args.add_argument("--max_steps", type=int, default=3)
    args.add_argument("--lr", type=float, default=1e-4)
    args.add_argument("--weight_decay", type=float, default=1e-1)
    args.add_argument("--zo_eps", type=float, default=1e-3)
    args.add_argument("--seed", type=int, default=42)
    args.add_argument("--batch_size", type=int, default=1)
    args.add_argument("--offloading_device", type=str, default="cpu")
    args.add_argument("--working_device", type=str, default="cuda:0")
    args = args.parse_args()
    return args


def model_size(model: torch.nn.Module):
    total_size = sum(p.numel() for p in model.parameters())
    trainable_size = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {"total": total_size, "trainable": trainable_size}


def prepare_data(V, B, T, device='cuda'):
    data_batch = torch.randint(0, V, (B, T+1)).to(device)
    input_ids = data_batch[:, :T]
    labels = data_batch[:, 1:T+1]
    pos = torch.arange(input_ids.shape[1], dtype=torch.long, device=device).unsqueeze(0)
    return input_ids, pos, labels


# GPU Memory Monitoring
def check_peak_memory_usage(iter, device="cuda:0", use_tqdm=False):
    # Check the peak memory usage
    peak_memory = torch.cuda.max_memory_allocated(device=device) / (1024 ** 2)
    if use_tqdm:
        tqdm.write("Peak GPU Memory after iteration {}: {:.2f} MB".format(iter+1, peak_memory))
    else:
        print(f"Peak GPU Memory after iteration {iter+1}: {peak_memory:.2f} MB")
    torch.cuda.reset_peak_memory_stats(device=device)

# CPU Memory Monitoring
peak_memory_cpu = 0
def check_and_update_peak_cpu_memory_usage(iter, use_tqdm=False):
    global peak_memory_cpu
    process = psutil.Process(os.getpid())
    current_memory = process.memory_info().rss / (1024 ** 2)  # Convert to MB
    if current_memory > peak_memory_cpu:
        peak_memory_cpu = current_memory
    if use_tqdm:
        tqdm.write(f"Peak CPU Memory after iteration {iter+1}: {peak_memory_cpu:.2f} MB")
    else:
        print(f"Peak CPU Memory after iteration {iter+1}: {peak_memory_cpu:.2f} MB")

def reset_peak_cpu_memory_usage():
    global peak_memory_cpu
    peak_memory_cpu = 0
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

def check_throughput(iter, total_token_batch_size_per_iter, fn, *args, use_tqdm=False, **kwargs):
    t1 = time.time()
    out = fn(*args, **kwargs)
    t2 = time.time()
    time_cost = t2-t1
    throughtput = total_token_batch_size_per_iter / time_cost
    if use_tqdm:
        tqdm.write("Time cost after iteration {}: {:.2f} ms, {:.2f} tok/s".format(iter+1, time_cost*1e3, throughtput))
    else:
        print("Time cost after iteration {}: {:.2f} ms, {:.2f} tok/s".format(iter+1, time_cost*1e3, throughtput))
