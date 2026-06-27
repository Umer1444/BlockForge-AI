"""
BlockForge AI – GPU Resource Manager
"""

import logging
from typing import Optional

import torch

from config import settings

logger = logging.getLogger("blockforge.gpu")


class GPUManager:
    """Manage GPU resources across the processing pipeline."""

    def __init__(self):
        self.cuda_available = torch.cuda.is_available()
        self.mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        
        if self.cuda_available:
            self.current_device = settings.GPU_DEVICE
            self.device_type = "cuda"
        elif self.mps_available:
            self.current_device = "mps"
            self.device_type = "mps"
        else:
            self.current_device = "cpu"
            self.device_type = "cpu"

    def get_info(self) -> dict:
        """Return GPU hardware information."""
        info = {
            "available": self.cuda_available or self.mps_available,
            "device": self.current_device,
            "device_type": self.device_type,
            "cuda_available": self.cuda_available,
            "mps_available": self.mps_available,
        }

        if self.cuda_available:
            info["device_count"] = torch.cuda.device_count()
            info["devices"] = []
            for i in range(info["device_count"]):
                props = torch.cuda.get_device_properties(i)
                allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
                reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                total = props.total_mem / (1024 ** 3)
                info["devices"].append({
                    "index": i,
                    "name": props.name,
                    "total_memory_gb": round(total, 2),
                    "allocated_gb": round(allocated, 2),
                    "free_gb": round(total - reserved, 2),
                })
        elif self.mps_available:
            info["device_name"] = "Apple Silicon GPU (MPS)"
            # MPS doesn't expose memory info as easily as CUDA
        
        return info

    def get_best_device(self) -> str:
        """Select the best available device."""
        if self.cuda_available:
            return "cuda:0"
        if self.mps_available:
            return "mps"
        return "cpu"

    def check_memory(self, required_gb: float = 4.0) -> bool:
        """Check if enough GPU memory is available."""
        if not self.cuda_available:
            # For MPS/CPU we don't have a reliable memory check yet
            return True

        device_idx = int(self.current_device.split(":")[-1]) if ":" in self.current_device else 0
        props = torch.cuda.get_device_properties(device_idx)
        reserved = torch.cuda.memory_reserved(device_idx) / (1024 ** 3)
        total = props.total_mem / (1024 ** 3)
        free = total - reserved

        if free < required_gb:
            logger.warning(
                f"Low GPU memory: {free:.2f} GB free, {required_gb:.2f} GB required"
            )
            return False
        return True

    def fallback_to_cpu(self):
        """Gracefully fallback to CPU when GPU is unavailable."""
        if self.current_device == "cpu":
            return

        logger.warning(f"Falling back from {self.device_type} to CPU")
        self.current_device = "cpu"
        self.device_type = "cpu"

    def try_gpu_or_fallback(self, required_gb: float = 4.0) -> str:
        """
        Attempt to use GPU if available, otherwise fallback to CPU.
        
        Returns:
            Device string to use
        """
        if self.device_type == "cpu":
            return "cpu"

        # Check memory
        if not self.check_memory(required_gb):
            logger.warning(f"Insufficient GPU memory ({required_gb}GB required), falling back to CPU")
            self.fallback_to_cpu()
            return "cpu"

        return self.current_device

    def clear_cache(self):
        """Clear GPU cache."""
        if self.cuda_available:
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        elif self.mps_available:
            # MPS doesn't have an explicit clear_cache, but we can empty the pool if possible in future torch versions
            pass
        logger.debug(f"⛏  {self.device_type.upper()} cache cleared")

    def log_status(self):
        """Log current GPU status."""
        info = self.get_info()
        if not info["available"]:
            logger.info("⛏  No GPU available, using CPU")
            return

        if info["cuda_available"]:
            for dev in info["devices"]:
                logger.info(
                    f"⛏  GPU {dev['index']}: {dev['name']} | "
                    f"{dev['free_gb']:.1f}/{dev['total_memory_gb']:.1f} GB free"
                )
        elif info["mps_available"]:
            logger.info("⛏  Using Apple Silicon GPU (MPS)")


# Singleton
gpu_manager = GPUManager()
